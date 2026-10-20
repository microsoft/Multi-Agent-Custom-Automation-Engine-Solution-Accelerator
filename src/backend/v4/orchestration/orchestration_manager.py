"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import inspect
import logging
import re
import time as _time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

from agent_framework import (
    Agent,
    AgentExecutor,
    AgentResponseUpdate,
    Content,
    Message,
)

# agent_framework imports
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_azure_ai import AzureAIClient, AzureAIProjectAgentOptions
from agent_framework_orchestrations import (
    AgentBasedGroupChatOrchestrator,
    ConcurrentBuilder,
    GroupChatBuilder,
    HandoffBuilder,
    MagenticBuilder,
    SequentialBuilder,
)
from agent_framework_orchestrations._base_group_chat_orchestrator import (
    GroupChatRequestSentEvent,
    GroupChatResponseReceivedEvent,
    ParticipantRegistry,
)
from agent_framework_orchestrations._magentic import (
    MagenticPlanReviewRequest,
    MagenticProgressLedger,
)

from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_af import PlanStatus, TeamConfiguration
from common.services.checkpoint_storage import get_checkpoint_storage
from v4.callbacks.response_handlers import (
    streaming_agent_response_callback,
)
from v4.common.services.team_service import TeamService
from v4.config.settings import connection_config, orchestration_config
from v4.magentic_agents.magentic_agent_factory import MagenticAgentFactory
from v4.models.messages import WebsocketMessageType
from v4.orchestration.human_approval_manager import HumanApprovalMagenticManager


async def _team_capabilities(memory_store: Any, team_id: str | None) -> dict:
    """Capacidades reales del equipo, leídas de su configuración.

    Sin agentes con MCP no hay tools de workspace en toda la corrida: el equipo
    no puede leer el repo ni ejecutar nada en él, por mucho que el plan lo
    prometa. Dicho aquí, el humano lo ve ANTES de aprobar.
    """
    if not team_id:
        return {}
    try:
        team = await memory_store.get_team_by_id(team_id=team_id)
    except Exception:  # la ausencia de este dato nunca debe tumbar el aparcado
        return {}
    agents = list(getattr(team, "agents", None) or []) if team else []
    con_mcp = [a.name for a in agents if getattr(a, "use_mcp", False)]
    return {
        "team_name": getattr(team, "name", "") if team else "",
        "agents": [a.name for a in agents],
        "workspace_agents": con_mcp,
        "can_see_workspace": bool(con_mcp),
        "coding_agents": [a.name for a in agents if getattr(a, "coding_tools", False)],
    }


async def _materialize_hosted_file_to_workspace(
    user_id: str,
    workspace_id: str,
    file_id: str,
    container_id: str | None,
    filename: str,
) -> None:
    """Download a hosted file from a Foundry container and write it to the workspace.

    Uses the process-shared credential (app MI in prod, az-login in dev).
    Errors are logged as warnings and never propagate — file materialisation
    is best-effort and must never break the orchestration run.
    """
    _log = logging.getLogger(__name__)
    if not container_id:
        _log.debug(
            "_materialize_hosted_file_to_workspace: skipping file_id=%s (no container_id)",
            file_id,
        )
        return
    try:
        import os
        from typing import Any

        from openai import AsyncOpenAI

        from v4.common.services.workspace_service import (
            _git,
            _resolve,
            workspace_for,
        )

        # El contenedor lo creó un agente Foundry (AzureAIClient) en el
        # Responses API del PROYECTO; desde el endpoint de la cuenta responde
        # 404 "Container not found" (medido 2026-10-19).
        project = (config.AZURE_AI_PROJECT_ENDPOINT or "").rstrip("/")
        cred = config.get_shared_async_credential()
        token = await cred.get_token("https://ai.azure.com/.default")
        client = AsyncOpenAI(
            api_key=token.token,
            base_url=f"{project}/openai/v1",
            timeout=120,
        )
        try:
            name = filename
            if not name or name == file_id:
                info: Any = await client.containers.files.retrieve(
                    file_id=file_id, container_id=container_id
                )
                path = getattr(info, "path", None) or file_id
                name = os.path.basename(path) or filename
            file_content = await client.containers.files.content.retrieve(
                file_id=file_id, container_id=container_id
            )
            data = await file_content.aread()
        finally:
            await client.close()

        ws = workspace_for(user_id, workspace_id)
        dest = _resolve(ws, name or file_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        rel = str(dest.relative_to(ws))

        add_res = _git(ws, "add", rel)
        if add_res.returncode != 0:
            _log.warning(
                "Workspace git add failed for %s: %s",
                rel,
                add_res.stderr.decode("utf-8", errors="replace")[-300:],
            )
            return

        staged = _git(ws, "diff", "--cached", "--quiet", "--", rel)
        if staged.returncode == 0:
            # No changes staged (e.g. same content as HEAD) → nothing to commit.
            return
        if staged.returncode != 1:
            _log.warning(
                "Workspace git diff --cached failed for %s: %s",
                rel,
                staged.stderr.decode("utf-8", errors="replace")[-300:],
            )
            return

        commit_res = _git(ws, "commit", "-q", "-m", f"agent: add {name or file_id}")
        if commit_res.returncode != 0:
            _log.warning(
                "Workspace git commit failed for %s: %s",
                rel,
                commit_res.stderr.decode("utf-8", errors="replace")[-300:],
            )
            return

        _log.info(
            "Magentic workspace write: user=%s ws=%s file=%s",
            user_id,
            workspace_id,
            name,
        )
    except Exception as exc:
        _log.warning(
            "_materialize_hosted_file_to_workspace failed file_id=%s: %s",
            file_id,
            exc,
        )


def _user_response(data: Any, answer: str, decision: str = "") -> Any:
    """La respuesta del usuario en el tipo que la solicitud espera (doc): una
    aprobación de tool, ``to_function_approval_response(approved=...)``; un
    handoff, ``HandoffAgentUserRequest.create_response``; el resto, la
    conversación con el mensaje del usuario."""
    from agent_framework_orchestrations import HandoffAgentUserRequest

    if isinstance(data, Content) and data.type == "function_approval_request":
        return data.to_function_approval_response(approved=decision == "approved")
    if isinstance(data, HandoffAgentUserRequest):
        return HandoffAgentUserRequest.create_response(answer)
    return [Message(role="user", text=answer)]


def _record_tool_contents(
    log: list[dict],
    pending: dict[str, tuple[int, str, str, Any]],
    contents: Any,
    agent: str,
) -> None:
    """Acumula las herramientas de un participante del plan como deeds
    (misma forma que el carril chat: ``_make_deed``), para que la ejecución
    del plan viaje en el ``metadata.turn_log`` de su resultado."""
    from v4.api.router import _make_deed

    for c in contents or []:
        ct = getattr(c, "type", "") or ""
        if ct in ("function_call", "mcp_server_tool_call"):
            call_id = str(getattr(c, "call_id", ""))
            fragment = getattr(c, "arguments", None)
            hit = pending.get(call_id)
            if hit is not None:
                # En streaming la llamada llega por trozos con el mismo call_id:
                # los argumentos se arman concatenando, no son llamadas nuevas.
                idx, server, tool, args = hit
                if isinstance(args, str) and isinstance(fragment, str):
                    args = args + fragment
                elif fragment:
                    args = fragment
                pending[call_id] = (idx, server, tool, args)
                log[idx] = _make_deed(server, tool, args, "called", None, agent)
                continue
            tool = (
                getattr(c, "name", None) or getattr(c, "tool_name", None) or "unknown"
            )
            server = getattr(c, "server_name", None) or (
                "mcp" if ct.startswith("mcp") else "function"
            )
            log.append(_make_deed(server, tool, fragment, "called", None, agent))
            pending[call_id] = (len(log) - 1, server, tool, fragment)
        elif ct in ("function_result", "mcp_server_tool_result"):
            exc = getattr(c, "exception", None)
            result = (
                str(exc)
                if exc
                else (
                    getattr(c, "result", None)
                    or getattr(c, "output", None)
                    or getattr(c, "text", None)
                )
            )
            status = "error" if exc else "success"
            hit = pending.pop(str(getattr(c, "call_id", "")), None)
            if hit is None:
                log.append(
                    _make_deed("function", "unknown", None, status, result, agent)
                )
            else:
                idx, server, tool, args = hit
                log[idx] = _make_deed(server, tool, args, status, result, agent)


def _participant_name(agent: Any) -> str:
    """El nombre con el que el framework identifica al participante (el
    ``author_name`` de sus mensajes)."""
    inner = getattr(agent, "_agent", None)
    return str(
        getattr(agent, "agent_name", None)
        or getattr(inner, "name", None)
        or getattr(agent, "name", None)
        or ""
    )


def _stage_context(predecessor: str, step: str):
    """Filtro de contexto de una etapa ``sequential``: la salida del predecesor
    y, como último mensaje, el paso propio de este participante.

    El framework pasa la conversación completa; aquí se queda lo que el
    predecesor dijo (por ``author_name``; si no firmó, la última respuesta del
    asistente) y se agrega el paso compuesto por el dueño. Sin paso, equivale a
    ``context_mode="last_agent"``.

    A la etapa siguiente pasa el TEXTO del predecesor. Un archivo que generó
    (``hosted_file``) ya llegó al usuario por el SSE y su enlace va en el
    texto; como contenido de un mensaje ``assistant`` el cliente del framework
    lo serializa como ``input_file`` y el Responses API lo rechaza (400
    "Invalid value: 'input_file'. Supported values are: 'output_text' and
    'refusal'", medido 2026-10-19: el workflow moría en la segunda etapa).
    """

    def _role(m: Any) -> str:
        role = getattr(m, "role", "")
        return str(getattr(role, "value", role)).lower()

    def _filter(full_conversation: list[Message]) -> list[Message]:
        prior = [
            m
            for m in full_conversation
            if predecessor and getattr(m, "author_name", None) == predecessor
        ]
        if not prior:
            tail: list[Message] = []
            for m in reversed(full_conversation):
                if _role(m) != "assistant":
                    break
                tail.append(m)
            prior = list(reversed(tail))
        spoken = [
            Message(
                role="assistant",
                text=m.text,
                author_name=getattr(m, "author_name", None),
            )
            for m in prior
        ]
        if step:
            return [*spoken, Message(role="user", text=step)]
        return spoken

    return _filter


class _SteeredGroupChatOrchestrator(AgentBasedGroupChatOrchestrator):
    """El orquestador por agente del framework, entregando al elegido el paso
    que el dueño compuso para él.

    Lo único que hace: ``compose`` escribe por participante su parte propia en
    ESTA petición (``instruction``). En group_chat el framework ya envía con
    cada petición un mensaje de steering (``additional_instruction``, el mismo
    que usa su Magentic) y su orquestador lo manda vacío; acá va
    ``steps[target]`` cada vez que le toca hablar. Un participante sin paso
    recibe exactamente lo nativo: no se inventa instrucción alguna y no se
    tocan la difusión, la caché del executor, la selección ni la terminación.

    Medido 2026-10-06 (prod 19:45) sin el paso: con la tarea "que las tres
    miradas discutan hasta converger", cada participante simuló el debate
    entero solo (tres agentes, cada uno imitando a los otros dos).
    """

    def __init__(
        self, *args: Any, steps: Mapping[str, str] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._steps = {name: step for name, step in (steps or {}).items() if step}

    async def _send_request_to_participant(
        self,
        target: str,
        ctx: Any,
        *,
        additional_instruction: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await super()._send_request_to_participant(
            target,
            ctx,
            additional_instruction=additional_instruction or self._steps.get(target),
            metadata=metadata,
        )


class OrchestrationManager:
    """Manager for handling orchestration logic using agent_framework Magentic workflow."""

    logger = logging.getLogger(f"{__name__}.OrchestrationManager")

    # Per-user-id lock to prevent concurrent orchestration initialization
    # Ensures idempotency: only one initialization runs per user at a time
    _initialization_locks: dict[str, asyncio.Lock] = {}

    def __init__(self):
        self.user_id: str | None = None
        self.logger = self.__class__.logger

    @classmethod
    def _get_user_lock(cls, user_id: str) -> asyncio.Lock:
        """Get or create an asyncio.Lock for the given user_id."""
        if user_id not in cls._initialization_locks:
            cls._initialization_locks[user_id] = asyncio.Lock()
        return cls._initialization_locks[user_id]

    def _extract_response_text(self, data) -> str:
        """
        Extract text content from various agent_framework response types.

        Handles:
        - Message: Extract .text
        - AgentResponse: Extract .text
        - AgentExecutorResponse: Extract from agent_response.text or full_conversation[-1].text
        - List of any of the above
        """
        if data is None:
            return ""

        # Direct Message
        if isinstance(data, Message):
            return data.text or ""

        # Has .text attribute directly (AgentResponse, etc.)
        if hasattr(data, "text") and data.text:
            return data.text

        # AgentExecutorResponse - has agent_response and full_conversation
        if hasattr(data, "agent_response"):
            # Try to get text from agent_response first
            agent_resp = data.agent_response
            if agent_resp and hasattr(agent_resp, "text") and agent_resp.text:
                return agent_resp.text
            # Fallback to last message in full_conversation
            if hasattr(data, "full_conversation") and data.full_conversation:
                last_msg = data.full_conversation[-1]
                if isinstance(last_msg, Message) and last_msg.text:
                    return last_msg.text

        # List of items - could be AgentExecutorResponse, ChatMessage, etc.
        if isinstance(data, list) and len(data) > 0:
            texts = []
            for item in data:
                # Recursively extract from each item
                item_text = self._extract_response_text(item)
                if item_text:
                    texts.append(item_text)
            if texts:
                # Return the last non-empty response (most recent)
                return texts[-1]

        return ""

    # ---------------------------
    # Orchestration construction
    # ---------------------------
    @classmethod
    async def init_orchestration(
        cls,
        agents: list,
        team_config: TeamConfiguration,
        memory_store: DatabaseBase,
        user_id: str | None = None,
    ):
        """
        Initialize a Magentic workflow with:
          - Provided agents (participants)
          - HumanApprovalMagenticManager as orchestrator manager
          - AzureAIClient as the underlying chat client
          - Event-based callbacks for streaming and final responses
        - Uses same deployment, endpoint, and credentials
        - Applies same execution settings (temperature, max_tokens)
        - Maintains same human approval workflow
        """
        if not user_id:
            raise ValueError("user_id is required to initialize orchestration")

        # Get credential from config (same as old version)
        credential = config.get_azure_credential(client_id=config.AZURE_CLIENT_ID)

        raw_name = team_config.name if team_config.name else "OrchestratorAgent"
        # Replace spaces and invalid chars with hyphens, strip leading/trailing hyphens
        sanitized_name = re.sub(r"[^a-zA-Z0-9-]", "-", raw_name)
        sanitized_name = re.sub(r"-+", "-", sanitized_name)  # Collapse multiple hyphens
        sanitized_name = sanitized_name.strip("-")[:63]  # Trim and limit length
        agent_name = sanitized_name if sanitized_name else "OrchestratorAgent"

        try:
            # Create the chat client (AzureAIClient)
            # Un solo cerebro: el manager del plan piensa con el contrato de
            # inferencia del orquestador del chat (modelo y reasoning), no con
            # el modelo del equipo, que es el de los participantes.
            chat_client = AzureAIClient(
                project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                model_deployment_name=config.CHAT_ORCHESTRATOR_MODEL,
                agent_name=agent_name,
                credential=credential,
            )

            # New API: Create an Agent to wrap the chat client for the manager
            manager_agent = Agent(
                client=chat_client,
                name="MagenticManager",
                default_options=AzureAIProjectAgentOptions(
                    reasoning=cast(
                        Any, {"effort": config.CHAT_ORCHESTRATOR_REASONING_EFFORT}
                    )
                ),
            )

            cls.logger.info(
                "Created AzureAIClient and manager Agent for orchestration with model '%s' at endpoint '%s'",
                config.CHAT_ORCHESTRATOR_MODEL,
                config.AZURE_AI_PROJECT_ENDPOINT,
            )
        except Exception as e:
            cls.logger.error("Failed to create AzureAIClient: %s", e)
            raise

        # Create HumanApprovalMagenticManager with the manager agent
        # New API: StandardMagenticManager takes agent as first positional argument
        try:
            manager = HumanApprovalMagenticManager(
                user_id=user_id,
                agent=manager_agent,  # New API: pass agent instead of chat_client
                max_round_count=orchestration_config.max_rounds,
                max_stall_count=3,
                max_reset_count=2,
            )
            cls.logger.info(
                "Created HumanApprovalMagenticManager for user '%s' with max_rounds=%d",
                user_id,
                orchestration_config.max_rounds,
            )
            # The builder swallows the reference; run_orchestration needs it to
            # seed prior-session context into MagenticContext.chat_history.
            orchestration_config.managers[user_id] = manager
        except Exception as e:
            cls.logger.error("Failed to create manager: %s", e)
            raise

        # Build participant map: use each agent's name as key
        participants: dict[str, Any] = {}
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participants) + 1}"

            # Extract the inner Agent for wrapper templates
            # FoundryAgentTemplate wrap an Agent in self._agent
            # ProxyAgent directly extends BaseAgent and can be used as-is
            if hasattr(ag, "_agent") and ag._agent is not None:
                # This is a wrapper (FoundryAgentTemplate)
                # Use the inner Agent which implements AgentProtocol
                participants[name] = ag._agent
                cls.logger.debug("Added participant '%s' (extracted inner agent)", name)
            else:
                # This is already an agent (like ProxyAgent extending BaseAgent)
                participants[name] = ag
                cls.logger.debug("Added participant '%s'", name)

        # Assemble workflow with callback
        storage = get_checkpoint_storage()

        # New SDK: participants() accepts a Sequence (list) of agents
        # The orchestrator uses agent.name to identify them
        participant_list = list(participants.values())
        cls.logger.info("Participants for workflow: %s", list(participants.keys()))

        # Note: When using a custom manager, the framework ignores max_round_count,
        # max_stall_count, and intermediate_outputs parameters.
        # These are already configured in the HumanApprovalMagenticManager.
        builder = MagenticBuilder(
            participants=participant_list,
            manager=manager,
            checkpoint_storage=storage,
            # Required: yield agent streaming output events, not just orchestrator output
            intermediate_outputs=True,
            # Native HITL gate: after manager.plan() the orchestrator emits a
            # request_info(MagenticPlanReviewRequest) and idles on a checkpoint.
            enable_plan_review=True,
        )

        # Build workflow
        workflow = builder.build()
        cls.logger.info(
            "Built Magentic workflow with %d participants and event callbacks",
            len(participants),
        )

        return workflow

    @classmethod
    def build_pattern_workflow(
        cls,
        pattern: str,
        agents: list,
        *,
        durable: bool = False,
        steps: dict[str, str] | None = None,
        orchestrator: Any | None = None,
        autonomous: set[str] | None = None,
    ) -> tuple[Any, list[Any]]:
        """Build the framework workflow of a composed chat-turn orchestration.

        ``magentic`` is not built here: it is the formal Plan
        (``init_orchestration``: HumanApprovalMagenticManager, plan review,
        checkpoints, WebSocket). The other patterns take the same participants
        the factory builds (the inner ``Agent`` of each ``FoundryAgentTemplate``)
        and the framework's builder wires them:

        * ``sequential`` / ``concurrent``: intermediate outputs on, so every
          participant's updates stream to the turn.
        * ``group_chat``: an orchestrator agent on the reasoning model
          (``CHAT_ORCHESTRATOR_MODEL``) selects the speaker from the
          conversation; ``max_rounds`` is the same ceiling as the plan lane
          (without it the framework runs indefinitely).
        * ``handoff``: the documented topology — the first participant is the
          triage that routes to every specialist and every specialist hands
          back to the triage; autonomous mode on, so an agent that answers
          without handing off keeps working instead of returning control to
          a user who is not at a prompt (a chat turn or a plan step).

        ``durable=True`` wires the SAME Cosmos checkpoint storage as magentic
        (the four builders accept ``checkpoint_storage``, verified against
        1.0.0b260311) so a ``request_info`` closes its superstep on a durable
        checkpoint that ``_park_on_request_info`` can reference. Without a
        durable identity (a real plan) those checkpoints would be orphans by
        construction — no ``waiting_for`` references them and
        ``_purge_checkpoint_lineage`` walks ``plan.workflow_names`` — so an
        ephemeral chat turn builds with NO storage: durability follows the
        identity that can come back for it, never precedes it.

        Returns:
            A tuple of (workflow, closables) where closables is a list of
            resources that must be closed when the workflow ends (e.g. the
            orchestrator agent for group_chat which owns an aiohttp session).
        """
        participants = [
            ag._agent if getattr(ag, "_agent", None) is not None else ag
            for ag in agents
        ]
        if not participants:
            raise ValueError("a composed orchestration needs at least one participant")
        storage = get_checkpoint_storage() if durable else None
        if pattern == "sequential":
            # Pipeline, no eco: el builder envuelve cada agente en un
            # AgentExecutor con context_mode="full" (recibe la pregunta del
            # usuario + todo lo anterior y la vuelve a responder). Envueltos
            # aquí con "last_agent", el agente N trabaja SÓLO sobre la respuesta
            # del N-1 — la etapa la define la posición en la cadena, no la
            # instruction. El builder respeta Executors ya construidos
            # (_resolve_participants). El primero recibe el input por
            # AgentExecutorRequest, así que su modo no interviene.
            # Con "last_agent" solo, el agente N recibe la respuesta del N-1 y
            # nada más: ni la tarea ni SU paso, así que reformula lo anterior
            # (medido 2026-10-03: dos especialistas, el mismo análisis dos
            # veces). La etapa es posición MÁS instrucción propia: "custom"
            # entrega la salida del predecesor y, como último mensaje, el paso
            # que el dueño compuso para ese participante (``steps``). Sin paso,
            # equivale a "last_agent".
            names = [_participant_name(ag) for ag in agents]
            executors: list[Any] = []
            for i, p in enumerate(participants):
                if i == 0:
                    executors.append(AgentExecutor(p, context_mode="last_agent"))
                    continue
                executors.append(
                    AgentExecutor(
                        p,
                        context_mode="custom",
                        context_filter=_stage_context(
                            names[i - 1], (steps or {}).get(names[i], "")
                        ),
                    )
                )
            return SequentialBuilder(
                participants=executors,
                intermediate_outputs=True,
                checkpoint_storage=storage,
            ).build(), []
        if pattern == "concurrent":
            return ConcurrentBuilder(
                participants=participants,
                intermediate_outputs=True,
                checkpoint_storage=storage,
            ).build(), []
        if pattern == "group_chat":
            # ``orchestrator`` inyectado: el que elige quién habla puede venir
            # de afuera (una prueba determinista de la semántica, sin red); si
            # no, el del contrato del orquestador. Sólo el creado acá se cierra.
            created = orchestrator is None
            if orchestrator is None:
                orchestrator = Agent(
                    client=AzureOpenAIResponsesClient(
                        project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                        deployment_name=config.CHAT_ORCHESTRATOR_MODEL,
                        credential=config.get_shared_async_credential(),
                    ),
                    name="GroupChatOrchestrator",
                )
            # Los participantes se envuelven acá (el builder respeta Executors
            # ya construidos) para que el registro del orquestador sea el mismo
            # que armaría el builder; el orquestador es el del framework más el
            # paso propio de cada participante (``steps``, por nombre). Con un
            # orquestador ya construido el builder ignora ``max_rounds``: va en
            # el constructor del orquestador.
            members = [AgentExecutor(p) for p in participants]
            manager = _SteeredGroupChatOrchestrator(
                agent=orchestrator,
                participant_registry=ParticipantRegistry(members),
                max_rounds=orchestration_config.max_rounds,
                steps=steps,
            )
            workflow = GroupChatBuilder(
                participants=members,
                orchestrator=manager,
                intermediate_outputs=True,
                checkpoint_storage=storage,
            ).build()
            # The orchestrator's client owns an aiohttp session; return it for
            # the caller to close when the workflow ends.
            return workflow, ([orchestrator] if created else [])
        if pattern == "handoff":
            # Sin autoridad central (doc: "no existe una autoridad central que
            # gestione el flujo"): el primero recibe el pedido y, sin
            # add_handoff, el framework arma la malla — cada agente traspasa a
            # cualquier otro según la conversación compartida. Restringir los
            # especialistas a devolver al triage era un hub central (agente como
            # herramienta), no handoff. Modo por defecto (human-in-loop): cuando
            # un agente responde sin traspasar, el flujo pide al usuario
            # (``request_info``) y el chat aparca el workflow hasta el siguiente
            # mensaje (``run_pattern(on_park=, resume=)``).
            builder = HandoffBuilder(
                participants=participants, checkpoint_storage=storage
            ).with_start_agent(participants[0])
            # Subconjunto autónomo (doc: ``with_autonomous_mode(agents=[...])``):
            # lo decide el dueño por participante. Los demás devuelven la
            # conversación al usuario cuando no traspasan.
            names = [_participant_name(ag) for ag in agents]
            chosen = [
                p
                for p, name in zip(participants, names, strict=False)
                if name in (autonomous or set())
            ]
            if chosen:
                builder = builder.with_autonomous_mode(agents=chosen)
            return builder.build(), []
        raise ValueError(f"unknown orchestration pattern '{pattern}'")

    async def run_pattern(
        self,
        pattern: str,
        agents: list,
        messages: Any,
        *,
        user_id: str,
        session_id: str,
        plan_id: str | None = None,
        workspace_id: str | None = None,
        steps: dict[str, str] | None = None,
        autonomous: set[str] | None = None,
        on_park: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        resume: dict[str, Any] | None = None,
    ):
        """Run a composed (non-magentic) pattern owning its full lifecycle.

        ``on_park`` / ``resume`` give a chat turn the durable identity the
        framework documents for handoff and any participant that asks the user
        (Learn, "checkpoints for durable workflows"): on ``request_info`` the
        workflow's checkpoint and pending request are handed to ``on_park``;
        the next message resumes with ``resume={"checkpoint_id", "answer"}``:
        step 1 restores the checkpoint (reloading the pending requests), step 2
        sends the user's answer as the responses.

        This is the single authority for what happens to a composed run —
        the front door decides *what* (pattern, participants, task) and this
        method decides *how it lives and dies*:

        * events are yielded as the framework emits them (the caller renders);
        * on ``request_info`` the durability contract applies: with a
          ``plan_id`` the run parks exactly like magentic
          (``_park_on_request_info``: checkpoint verified, ``waiting_for``
          persisted, UI notified) and resumes via ``resume_orchestration``;
          without one there is no durable identity to hang the resume on, so
          the turn ends there — stated, not implied;
        * closables (e.g. the group_chat orchestrator's aiohttp session) and
          the turn's agents are closed here, deterministically, in a finally.

        Durability follows the identity: with a ``plan_id`` the workflow
        builds WITH checkpoint storage parkable and purgeable via
        ``plan.workflow_names``. A composed chat turn (``on_park``/``resume``,
        no ``plan_id``) also builds WITH storage so a participant can park on
        the session, but nothing lists it in ``plan.workflow_names``; this
        method is therefore its only purge path — it keeps a lineage that
        parked a request the user can resume and drops every other (the turn
        that finished or was abandoned, and the checkpoint it resumed from).
        A truly ephemeral turn (no ``on_park`` and no ``resume``) builds with
        none — it must not shed durable checkpoints no identity references.
        """
        resumable = on_park is not None or resume is not None
        # Un turno compuesto de chat (sin ``plan_id``) construye con storage
        # durable para poder aparcarse, pero su ``workflow_name`` nunca entra en
        # ``plan.workflow_names`` — el único recorrido de purga. Sin limpieza
        # terminal aquí sus checkpoints quedan huérfanos en Cosmos para siempre;
        # la durabilidad sigue a la identidad aparcada, no al turno.
        durable_chat = resumable and not plan_id
        workflow, closables = self.build_pattern_workflow(
            pattern,
            agents,
            durable=bool(plan_id) or resumable,
            steps=steps,
            autonomous=autonomous,
        )
        parked = False
        try:
            if resume is not None:
                # Paso 1 (doc): restaurar el checkpoint recarga las solicitudes
                # pendientes. Paso 2: responderlas con lo que dijo el usuario.
                restored = []
                async for event in workflow.run(
                    checkpoint_id=resume["checkpoint_id"], stream=True
                ):
                    if getattr(event, "type", None) == "request_info":
                        restored.append(event)
                if not restored:
                    raise RuntimeError(
                        f"checkpoint {resume['checkpoint_id']} sin solicitud pendiente"
                    )
                responses = {
                    req.request_id: _user_response(
                        req.data,
                        str(resume.get("answer") or ""),
                        str(resume.get("decision") or ""),
                    )
                    for req in restored
                }
                event_stream = workflow.run(responses=responses, stream=True)
            else:
                event_stream = workflow.run(messages, stream=True)
            pending_for_user: Any = None
            async for event in event_stream:
                if getattr(event, "type", None) == "request_info":
                    if on_park is not None and not plan_id:
                        # El checkpoint que conserva la solicitud se escribe al
                        # CERRAR el superstep: se aparca cuando el stream
                        # termina, como el carril de plan.
                        pending_for_user = event
                        continue
                    if plan_id:
                        await self._park_on_request_info(
                            workflow=workflow,
                            event=event,
                            user_id=user_id,
                            session_id=session_id,
                            plan_id=plan_id,
                            workspace_id=workspace_id,
                        )
                    else:
                        self.logger.info(
                            "Composed %s asked the user without a plan identity; "
                            "the turn ends here",
                            pattern,
                        )
                    return
                yield event
            if pending_for_user is not None and on_park is not None:
                storage = get_checkpoint_storage()
                latest = await storage.get_latest(workflow_name=workflow.name)
                if (
                    latest is None
                    or pending_for_user.request_id
                    not in latest.pending_request_info_events
                ):
                    raise RuntimeError(
                        f"request_info {pending_for_user.request_id} sin checkpoint "
                        f"que lo conserve (workflow {workflow.name})"
                    )
                data = pending_for_user.data
                approval: dict[str, Any] | None = None
                if (
                    isinstance(data, Content)
                    and data.type == "function_approval_request"
                ):
                    call = data.function_call
                    approval = {
                        "tool": str(getattr(call, "name", "") or ""),
                        "arguments": str(getattr(call, "arguments", "") or "")[:2000],
                    }
                await on_park(
                    {
                        "request_id": pending_for_user.request_id,
                        "checkpoint_id": latest.checkpoint_id,
                        "workflow_name": workflow.name,
                        "kind": "function_approval_request"
                        if approval
                        else type(data).__name__,
                        "approval": approval,
                        "executor_id": str(
                            getattr(pending_for_user, "source_executor_id", "") or ""
                        ),
                    }
                )
                parked = True
        finally:
            if durable_chat:
                await self._purge_composed_turn(workflow, resume, parked)
            for resource in closables:
                try:
                    close_method = getattr(resource, "close", None)
                    if callable(close_method):
                        result = close_method()
                        if inspect.isawaitable(result):
                            await result
                except Exception as e:
                    self.logger.warning(
                        "Closing workflow resource %s failed: %s",
                        getattr(resource, "name", resource),
                        e,
                    )
            for ag in agents:
                try:
                    await ag.close()
                except Exception as e:  # teardown of the turn's agents
                    self.logger.warning(
                        "Closing composed agent %s failed: %s",
                        getattr(ag, "agent_name", ag),
                        e,
                    )

    # ---------------------------
    # Orchestration retrieval
    # ---------------------------
    @classmethod
    async def get_current_or_new_orchestration(
        cls,
        user_id: str,
        team_config: TeamConfiguration,
        team_switched: bool,
        team_service: TeamService | None = None,
        force_rebuild: bool = False,
        user_access_token: str | None = None,
        workspace_id: str | None = None,
    ):
        """
        Return an existing workflow for the user or create a new one if:
          - None exists
          - Team switched flag is True
          - force_rebuild is True (for new tasks after workflow completion)

        Thread-safe: uses per-user-id lock to prevent concurrent initialization.
        If multiple requests arrive simultaneously, only the first one initializes;
        the others wait and return the same orchestration instance.
        """
        # Acquire per-user lock to ensure only one initialization runs at a time
        user_lock = cls._get_user_lock(user_id)
        async with user_lock:
            # Double-check pattern: re-check after acquiring lock
            current = orchestration_config.get_current_orchestration(user_id)
            needs_rebuild = current is None or team_switched or force_rebuild

            if needs_rebuild:
                if team_service is None or team_service.memory_context is None:
                    raise ValueError(
                        "team_service with initialized memory_context is required"
                    )

                if current is not None and (team_switched or force_rebuild):
                    reason = (
                        "team switched"
                        if team_switched
                        else "force rebuild for new task"
                    )
                    cls.logger.info(
                        "Rebuilding orchestration for user '%s' (reason: %s)",
                        user_id,
                        reason,
                    )

                    prior_wrappers = orchestration_config.agent_wrappers.pop(
                        user_id, []
                    )

                    async def _close_wrapper(agent) -> None:
                        agent_name = getattr(
                            agent, "agent_name", getattr(agent, "name", "")
                        )
                        close_method = getattr(agent, "close", None)
                        if callable(close_method) and inspect.iscoroutinefunction(
                            close_method
                        ):
                            try:
                                await close_method()
                                cls.logger.debug(
                                    "Closed agent wrapper '%s'", agent_name
                                )
                            except Exception as e:
                                cls.logger.warning(
                                    "Non-fatal error closing agent wrapper '%s': %s",
                                    agent_name,
                                    e,
                                )

                    if prior_wrappers:
                        close_tasks = [
                            asyncio.ensure_future(_close_wrapper(a))
                            for a in prior_wrappers
                        ]
                        await asyncio.gather(*close_tasks, return_exceptions=True)

                factory = MagenticAgentFactory(team_service=team_service)
                try:
                    agents = await factory.get_agents(
                        user_id=user_id,
                        team_config_input=team_config,
                        memory_store=team_service.memory_context,
                        # OBO: agents authenticate as the user (build_user_credential
                        # → OnBehalfOfCredential). With offline_access the credential
                        # self-renews downstream, so it survives long/approval-gated
                        # runs without recreating agents. Falls back to app MI if None.
                        user_access_token=user_access_token,
                        # Sin esto el agente no sabe sobre qué workspace trabaja
                        # y llama a las tools con un nombre inventado.
                        workspace_id=workspace_id,
                    )
                    cls.logger.info(
                        "Created %d agents for user '%s'", len(agents), user_id
                    )
                except Exception as e:
                    cls.logger.error(
                        "Failed to create agents for user '%s': %s", user_id, e
                    )
                    raise
                try:
                    cls.logger.info(
                        "Initializing new orchestration for user '%s'", user_id
                    )
                    workflow = await cls.init_orchestration(
                        agents, team_config, team_service.memory_context, user_id
                    )
                    orchestration_config.orchestrations[user_id] = workflow
                    # Store wrappers for proper cleanup on next rebuild
                    orchestration_config.agent_wrappers[user_id] = agents
                except Exception as e:
                    cls.logger.error(
                        "Failed to initialize orchestration for user '%s': %s",
                        user_id,
                        e,
                    )
                    raise
            return orchestration_config.get_current_orchestration(user_id)

    # ---------------------------
    # Execution
    # ---------------------------
    async def _persist_agent_message(
        self,
        *,
        plan_id: str | None,
        user_id: str,
        agent_name: str,
        content: str,
        is_final: bool,
    ) -> None:
        """Persist an agent message to the plan store from the backend.

        Reuses the SAME proven path the ``/agent_message`` endpoint used
        (``PlanService.handle_agent_messages``) — just triggered in-process
        instead of by the frontend echo. On ``is_final`` it also flips the plan
        to completed. Never raises: persistence must not abort the run.
        """
        if not plan_id:
            return
        try:
            from v4.common.services.plan_service import PlanService
            from v4.models.messages import AgentMessageResponse, AgentMessageType

            resp = AgentMessageResponse(
                plan_id=plan_id,
                agent=agent_name,
                content=content,
                agent_type=AgentMessageType.AI_AGENT,
                is_final=is_final,
                streaming_message=content if is_final else None,
            )
            await PlanService.handle_agent_messages(resp, user_id)
        except Exception as _pe:
            self.logger.warning(
                "Backend persist of agent message (plan=%s, final=%s) failed: %s",
                plan_id,
                is_final,
                _pe,
            )

    async def resume_orchestration(
        self,
        user_id: str,
        session_id: str,
        plan_id: str,
        request_id: str,
        response: Any,
        workspace_id: str | None = None,
        *,
        answer: str = "",
        decision: str = "",
    ) -> None:
        """Deliver the human response to the pending ``request_info`` and continue.

        With ``response=None`` the answer is typed against the restored request
        itself (``answer``/``decision`` → ``_user_response``): the case of a tool
        approval, whose response needs the pending ``function_call``.

        The plan's ``waiting_for`` (persisted by ``_park_on_request_info`` when the
        workflow went idle) carries the checkpoint to restore. ``response`` is
        the framework object the request expects: ``Content.from_text`` for a
        clarification, ``MagenticPlanReviewResponse.approve()/revise()`` for a
        plan review.
        """
        from common.database.database_factory import DatabaseFactory

        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
        waiting_for = (plan.waiting_for if plan else None) or {}
        if plan is None or waiting_for.get("request_id") != request_id:
            raise ValueError(
                f"Plan {plan_id} is not waiting for request {request_id} "
                f"(waiting_for={waiting_for.get('request_id')})"
            )
        plan.waiting_for = None  # consumed: the answer is on its way into the workflow
        await memory_store.update_plan(plan)
        await self.run_orchestration(
            user_id,
            session_id,
            input_task=None,
            plan_id=plan_id,
            workspace_id=workspace_id
            if workspace_id is not None
            else waiting_for.get("workspace_id"),
            _resume=(
                {
                    "checkpoint_id": waiting_for["checkpoint_id"],
                    "responses": {request_id: response},
                }
                if response is not None
                else {
                    "checkpoint_id": waiting_for["checkpoint_id"],
                    "answer": answer,
                    "decision": decision,
                }
            ),
        )

    async def cancel_parked(self, user_id: str, plan_id: str, request_id: str) -> None:
        """The human rejected a parked request.

        Nothing to resume: ``waiting_for`` is cleared, the plan is kept as
        ``canceled`` (auditable decision) and the UI gets the FINAL_RESULT
        ``cancelled`` it always got.
        """
        from common.database.database_factory import DatabaseFactory

        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
        waiting_for = (plan.waiting_for if plan else None) or {}
        if plan is None or waiting_for.get("request_id") != request_id:
            raise ValueError(
                f"Plan {plan_id} is not waiting for request {request_id} "
                f"(waiting_for={waiting_for.get('request_id')})"
            )
        plan.waiting_for = None
        plan.overall_status = PlanStatus.canceled
        await memory_store.update_plan(plan)
        await self._purge_checkpoint_lineage(plan)
        await connection_config.send_status_update_async(
            {
                "content": "Plan execution cancelled by user.",
                "status": "cancelled",
                "timestamp": asyncio.get_event_loop().time(),
            },
            user_id,
            message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
            process_id=plan.plan_id,
        )
        self.logger.info(
            "Parked %s %s cancelled by user (plan %s)",
            waiting_for.get("kind"),
            request_id,
            plan_id,
        )

    async def _purge_checkpoint_lineage(self, plan: Any) -> None:
        """Pliegue terminal: borra todos los checkpoints de cada segmento del
        linaje (``plan.workflow_names``). La cadena ``previous_checkpoint_id`` no
        cruza una reanudación, por eso la unidad es el ``workflow_name``."""
        names = list(getattr(plan, "workflow_names", None) or [])
        if not names:
            return
        storage = get_checkpoint_storage()
        for name in names:
            for checkpoint_id in await storage.list_checkpoint_ids(workflow_name=name):
                await storage.delete(checkpoint_id)
        self.logger.info(
            "Checkpoints purged for plan %s (%d segments)", plan.plan_id, len(names)
        )

    async def _purge_composed_turn(
        self, workflow: Any, resume: dict[str, Any] | None, parked: bool
    ) -> None:
        """Limpieza terminal del linaje durable de un turno compuesto de chat.

        Un turno compuesto no se referencia desde ``plan.workflow_names``, así
        que ``_purge_checkpoint_lineage`` nunca lo recoge. La durabilidad sigue a
        la identidad aparcada: se conserva SÓLO el linaje que dejó una solicitud
        que el usuario puede reanudar (``parked``); cualquier otro —el turno que
        terminó o se abandonó, y el checkpoint del que se reanudó, ya consumido—
        es un huérfano que se borra aquí. La unidad es el ``workflow_name``: la
        cadena ``previous_checkpoint_id`` no cruza una reanudación."""
        storage = get_checkpoint_storage()
        names: set[str] = set()
        if resume is not None:
            # El checkpoint reanudado ya se consumió para restaurar este turno;
            # su ``workflow_name`` difiere del de esta corrida, así que su linaje
            # queda huérfano salvo que se purgue explícitamente.
            try:
                spent = await storage.load(resume["checkpoint_id"])
                names.add(spent.workflow_name)
            except Exception as e:
                self.logger.warning(
                    "No se pudo resolver el linaje reanudado para purgar: %s", e
                )
        if parked:
            # El nuevo checkpoint aparcado se conserva; nunca se purga.
            names.discard(workflow.name)
        else:
            names.add(workflow.name)
        for name in names:
            try:
                for checkpoint_id in await storage.list_checkpoint_ids(
                    workflow_name=name
                ):
                    await storage.delete(checkpoint_id)
            except Exception as e:
                self.logger.warning(
                    "Purga de checkpoints del turno compuesto %s falló: %s", name, e
                )

    async def _purge_checkpoint_lineage_by_id(self, user_id: str, plan_id: str) -> None:
        from common.database.database_factory import DatabaseFactory

        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
        if plan is not None:
            await self._purge_checkpoint_lineage(plan)

    async def _park_on_request_info(
        self,
        *,
        workflow: Any,
        event: Any,
        user_id: str,
        session_id: str,
        plan_id: str | None,
        workspace_id: str | None,
    ) -> None:
        """The workflow went idle on a ``request_info``: the pending request lives
        in the checkpoint that closed the superstep. Nothing waits in-process:
        ``waiting_for`` is persisted on the plan, the UI is notified, and this
        run ends. The answer resumes from the checkpoint (``resume_orchestration``).
        """
        storage = get_checkpoint_storage()
        latest = await storage.get_latest(workflow_name=workflow.name)
        if latest is None or event.request_id not in latest.pending_request_info_events:
            raise RuntimeError(
                f"request_info {event.request_id} sin checkpoint que lo conserve "
                f"(workflow {workflow.name})"
            )
        data = event.data
        # Una tool que pide autorización humana también viaja como
        # ``user_input_request``: es una aprobación (tool + argumentos), no una
        # pregunta; la UI muestra Aprobar/Rechazar y la decisión vuelve como
        # ``to_function_approval_response`` (``_user_response``).
        is_approval = (
            isinstance(data, Content) and data.type == "function_approval_request"
        )
        is_clarification = (
            isinstance(data, Content)
            and bool(data.user_input_request)
            and not is_approval
        )
        is_plan_review = isinstance(data, MagenticPlanReviewRequest)
        question = (data.text or "") if is_clarification else ""
        approval: dict[str, Any] | None = None
        if is_approval:
            call = data.function_call
            approval = {
                "tool": str(getattr(call, "name", "") or ""),
                "arguments": str(getattr(call, "arguments", "") or "")[:2000],
            }
        kind = (
            "function_approval_request"
            if is_approval
            else "clarification"
            if is_clarification
            else "plan_review"
            if is_plan_review
            else type(data).__name__
        )
        waiting_for: dict[str, Any] = {
            "kind": kind,
            "request_id": event.request_id,
            "checkpoint_id": latest.checkpoint_id,
            "workflow_name": workflow.name,
            "question": question,
            "approval": approval,
            "content_id": getattr(data, "id", None),
            "workspace_id": workspace_id,
        }
        mplan = None
        if is_plan_review:
            manager = orchestration_config.managers.get(user_id)
            mplan = getattr(manager, "magentic_plan", None)
            if mplan is None:
                raise RuntimeError(
                    f"plan review {event.request_id} without an MPlan on the manager"
                )
            if plan_id:
                mplan.plan_id = plan_id
            waiting_for["m_plan_id"] = mplan.id
            waiting_for["is_stalled"] = bool(getattr(data, "is_stalled", False))
        if plan_id:
            from common.database.database_factory import DatabaseFactory

            memory_store = await DatabaseFactory.get_database(user_id=user_id)
            plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
            if plan is None:
                if is_plan_review:
                    raise RuntimeError(
                        f"Plan {plan_id} not found while parking request_info"
                    )
            else:
                waiting_for["team_id"] = plan.team_id
                # Qué puede hacer REALMENTE este equipo. Es un hecho de su
                # configuración, no una suposición sobre la tarea: si ningún
                # agente tiene MCP, el workspace es invisible para toda la
                # corrida y el usuario aprueba un plan que no puede cumplirse.
                waiting_for["team_capabilities"] = await _team_capabilities(
                    memory_store, plan.team_id
                )
                if mplan is not None:
                    mplan.team_id = plan.team_id or ""
                    # Re-sent on WS reconnect from the store (router).
                    waiting_for["m_plan"] = mplan.model_dump()
                plan.waiting_for = waiting_for
                if workflow.name not in plan.workflow_names:
                    plan.workflow_names.append(workflow.name)
                await memory_store.update_plan(plan)
        if mplan is not None:
            from v4.models.messages import PlanApprovalRequest
            from v4.models.messages import PlanStatus as V4PlanStatus

            await connection_config.send_status_update_async(
                message=PlanApprovalRequest(
                    plan=mplan,
                    status=V4PlanStatus.PENDING_APPROVAL,
                    context={
                        "request_id": event.request_id,
                        "is_stalled": bool(getattr(data, "is_stalled", False)),
                    },
                ),
                user_id=user_id,
                message_type=WebsocketMessageType.PLAN_APPROVAL_REQUEST,
                process_id=plan_id,
            )
        if is_clarification or is_approval:
            await connection_config.send_status_update_async(
                {
                    "question": question,
                    "request_id": event.request_id,
                    "approval": approval,
                },
                user_id=user_id,
                message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                process_id=plan_id,
            )
            if session_id and question:
                try:
                    from common.services.chat_cosmos_service import (
                        get_chat_cosmos_service,
                    )

                    chat_svc = await get_chat_cosmos_service()
                    await chat_svc.add_message(
                        session_id=session_id,
                        user_id=user_id,
                        content=question,
                        role="assistant",
                        metadata={
                            "intent": "task",
                            "clarification_id": event.request_id,
                            "message_type": "clarification_question",
                        },
                    )
                except Exception as chat_error:
                    self.logger.warning(
                        "Could not persist clarification question to chat_cosmos: %s",
                        chat_error,
                    )
        self.logger.info(
            "Orchestration parked on %s %s (checkpoint %s)",
            waiting_for["kind"],
            event.request_id,
            latest.checkpoint_id,
        )

    async def run_orchestration(
        self,
        user_id,
        session_id: str,
        input_task,
        plan_id: str | None = None,
        history: list | None = None,
        workspace_id: str | None = None,
        _resume: dict[str, Any] | None = None,
    ) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.

        ``plan_id`` makes the BACKEND the single source of truth for plan state:
        agent messages are persisted to the plan store and the plan is marked
        completed here, in-process — no longer dependent on the frontend echoing
        to ``/agent_message`` (which was fragile and duplicated the final).

        ``_resume`` (internal, set by ``resume_orchestration``) restores the
        checkpoint the workflow went idle on and feeds the pending
        ``request_info`` responses; the event loop below is shared.
        """
        job_id = str(uuid.uuid4())
        self.logger.info(
            "Starting orchestration job '%s' for user '%s'%s",
            job_id,
            user_id,
            " (resume)" if _resume else "",
        )

        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            raise ValueError("Orchestration not initialized for user.")
        # Fresh thread per participant to avoid cross-run state bleed
        executors = getattr(workflow, "executors", {})
        self.logger.debug("Executor keys at run start: %s", list(executors.keys()))

        for exec_key, executor in executors.items():
            if _resume is not None:
                break  # state comes from the checkpoint; do not wipe it
            try:
                if exec_key == "magentic_orchestrator":
                    # Orchestrator path
                    if hasattr(executor, "_conversation"):
                        conv = executor._conversation
                        # Support list-like or custom container with clear()
                        if hasattr(conv, "clear") and callable(conv.clear):
                            conv.clear()
                            self.logger.debug(
                                "Cleared orchestrator conversation (%s)", exec_key
                            )
                        elif isinstance(conv, list):
                            conv[:] = []
                            self.logger.debug(
                                "Emptied orchestrator conversation list (%s)", exec_key
                            )
                        else:
                            self.logger.debug(
                                "Orchestrator conversation not clearable type (%s): %s",
                                exec_key,
                                type(conv),
                            )
                    else:
                        self.logger.debug(
                            "Orchestrator has no _conversation attribute (%s)", exec_key
                        )
                else:
                    # Agent path
                    if hasattr(executor, "_chat_history"):
                        hist = executor._chat_history
                        if hasattr(hist, "clear") and callable(hist.clear):
                            hist.clear()
                            self.logger.debug(
                                "Cleared agent chat history (%s)", exec_key
                            )
                        elif isinstance(hist, list):
                            hist[:] = []
                            self.logger.debug(
                                "Emptied agent chat history list (%s)", exec_key
                            )
                        else:
                            self.logger.debug(
                                "Agent chat history not clearable type (%s): %s",
                                exec_key,
                                type(hist),
                            )
                    else:
                        self.logger.debug(
                            "Agent executor has no _chat_history attribute (%s)",
                            exec_key,
                        )
            except Exception as e:
                self.logger.warning(
                    "Failed clearing state for executor %s: %s", exec_key, e
                )
        # --- END NEW BLOCK ---

        # The task is the bare objective. Prior conversation enters the manager
        # as MagenticContext.chat_history (real Messages) at plan() time — the
        # framework models objective and conversation separately; welding the
        # history into the task string polluted the plan (steps like "review
        # prior context", agents chosen for past topics).
        task_text = (
            getattr(input_task, "description", str(input_task))
            if input_task is not None
            else ""
        )
        self.logger.debug("Task: %s", task_text)

        manager = orchestration_config.managers.get(user_id)
        if manager is not None and _resume is None:
            # Unconditional: an empty list clears any stale pending seed left
            # by a run that never reached plan().
            manager.seed_chat_history(history or [])

        # ── Stamp session_id on ProxyAgent instances so they can write to chat_cosmos ──
        from v4.magentic_agents.proxy_agent import ProxyAgent as _ProxyAgent

        for _agent in orchestration_config.agent_wrappers.get(user_id, []):
            if isinstance(_agent, _ProxyAgent):
                _agent.session_id = session_id

        # Track how many times each agent is called (for debugging duplicate calls)
        agent_call_counts: dict = {}
        # Buffer streamed text per-agent so we can emit a complete AGENT_MESSAGE
        agent_stream_buffers: dict[str, str] = {}

        agents_actively_responding: set[str] = set()
        # La ejecución del plan como evidencia de UN turno de la sesión: cada
        # ronda (participante + sus herramientas) es un deed del turn_log que
        # viaja en el metadata del resultado del plan, no como mensajes sueltos.
        agent_tool_logs: dict[str, list[dict]] = {}
        agent_tool_pending: dict[str, dict[str, tuple[int, str, str, Any]]] = {}
        agent_rounds: dict[str, int] = {}
        plan_turn_log: list[dict] = []
        # Deeds beyond _LEDGER_MAX_DEEDS are dropped (bounded like the
        # direct-chat ledger) and only their count is persisted, keeping the
        # chat session item under the 2 MB Cosmos limit.
        plan_turn_log_dropped: int = 0

        try:
            # Execute workflow using run() with stream=True
            # The execution settings are configured in the manager/client
            final_output: str | None = None
            # request_info the workflow went idle on (clarification / plan review)
            pending_request: Any = None

            self.logger.info("Starting workflow execution...")

            if _resume is None:
                event_stream = workflow.run(task_text, stream=True)
            elif "responses" in _resume:
                event_stream = workflow.run(
                    checkpoint_id=_resume["checkpoint_id"],
                    checkpoint_storage=get_checkpoint_storage(),
                    responses=_resume["responses"],
                    stream=True,
                )
            else:
                # Dos pasos (doc, igual que ``run_pattern``): restaurar el
                # checkpoint recarga la solicitud pendiente con su dato, y la
                # respuesta se construye en el tipo que esa solicitud espera
                # (``_user_response``: aprobación de tool, handoff o texto).
                restored: list[Any] = []
                async for ev in workflow.run(
                    checkpoint_id=_resume["checkpoint_id"],
                    checkpoint_storage=get_checkpoint_storage(),
                    stream=True,
                ):
                    if getattr(ev, "type", None) == "request_info":
                        restored.append(ev)
                if not restored:
                    raise RuntimeError(
                        f"checkpoint {_resume['checkpoint_id']} sin solicitud pendiente"
                    )
                event_stream = workflow.run(
                    responses={
                        req.request_id: _user_response(
                            req.data,
                            str(_resume.get("answer") or ""),
                            str(_resume.get("decision") or ""),
                        )
                        for req in restored
                    },
                    stream=True,
                )

            async for event in event_stream:
                try:
                    # WorkflowEvent has a .type field (string) instead of specific event classes
                    event_type = (
                        event.type if hasattr(event, "type") else type(event).__name__
                    )
                    if event_type not in ("status", "output"):
                        self.logger.info("[EVENT] type=%s", event_type)

                    # The workflow is about to go idle waiting for a human. The
                    # pending request lives in the checkpoint; nothing blocks here.
                    if event_type == "request_info":
                        pending_request = event
                        self.logger.info(
                            "[REQUEST INFO] request_id=%s data=%s",
                            getattr(event, "request_id", None),
                            type(event.data).__name__,
                        )

                    # Handle orchestrator events (plan, progress ledger)
                    elif event_type == "magentic_orchestrator":
                        self.logger.info("[Magentic Orchestrator Event]")
                        if isinstance(event.data, Message):
                            self.logger.info(
                                "Plan message: %s",
                                event.data.text[:200] if event.data.text else "",
                            )
                        elif isinstance(event.data, MagenticProgressLedger):
                            self.logger.info("Progress ledger received")

                    # Handle group chat request sent
                    elif event_type == "group_chat":
                        # Check if this is a request or response via the data type
                        if isinstance(event.data, GroupChatRequestSentEvent):
                            agent_name = event.data.participant_name
                            agent_call_counts[agent_name] = (
                                agent_call_counts.get(agent_name, 0) + 1
                            )
                            call_num = agent_call_counts[agent_name]

                            self.logger.info(
                                "[REQUEST SENT (round %d)] to agent: %s (call #%d)",
                                event.data.round_index,
                                agent_name,
                                call_num,
                            )

                            if call_num > 1:
                                self.logger.warning(
                                    "Agent '%s' called %d times", agent_name, call_num
                                )

                            # Open the response window: clear any residual buffer from a
                            # previous round and mark this agent as the active speaker.
                            # Only chunks received while an agent is in this set will be
                            # forwarded to the UI; broadcast-sync chunks (should_respond=False)
                            # arrive outside this window and are silently discarded.
                            agent_stream_buffers.pop(agent_name, None)
                            agent_tool_logs.pop(agent_name, None)
                            agent_tool_pending.pop(agent_name, None)
                            agent_rounds[agent_name] = int(event.data.round_index)
                            agents_actively_responding.add(agent_name)

                        elif isinstance(event.data, GroupChatResponseReceivedEvent):
                            agent_name = event.data.participant_name
                            self.logger.info(
                                "[RESPONSE RECEIVED (round %d)] from agent: %s",
                                event.data.round_index,
                                agent_name,
                            )
                            # Close the response window: no more chunks for this agent
                            # should reach the UI until the next RequestSentEvent.
                            agents_actively_responding.discard(agent_name)
                            # Flush accumulated streaming content as a complete AGENT_MESSAGE
                            buffered = agent_stream_buffers.pop(agent_name, "")
                            if buffered:
                                from v4.callbacks.response_handlers import (
                                    clean_citations,
                                )
                                from v4.models.messages import AgentMessage

                                cleaned = clean_citations(buffered)
                                if cleaned.strip():
                                    agent_msg = AgentMessage(
                                        agent_name=agent_name,
                                        timestamp=str(_time.time()),
                                        content=cleaned,
                                    )
                                    await connection_config.send_status_update_async(
                                        agent_msg,
                                        user_id,
                                        message_type=WebsocketMessageType.AGENT_MESSAGE,
                                        process_id=plan_id,
                                    )
                                    self.logger.info(
                                        "Sent AGENT_MESSAGE for '%s' (%d chars)",
                                        agent_name,
                                        len(cleaned),
                                    )
                                    # Persist this intermediate agent message to the
                                    # plan store from the BACKEND (single source of
                                    # truth) instead of relying on the frontend echo.
                                    # is_final=False → background detail; the chat
                                    # thread only ever gets the ONE final (writeback).
                                    await self._persist_agent_message(
                                        plan_id=plan_id,
                                        user_id=user_id,
                                        agent_name=agent_name,
                                        content=cleaned,
                                        is_final=False,
                                    )
                                    # Ronda al turn_log: primero sus herramientas,
                                    # después la respuesta del participante.
                                    from v4.api.router import (
                                        _LEDGER_MAX_DEEDS,
                                        _make_deed,
                                    )

                                    _round_deeds = agent_tool_logs.pop(agent_name, [])
                                    _round_deeds.append(
                                        _make_deed(
                                            "magentic",
                                            agent_name,
                                            {"round": agent_rounds.get(agent_name)},
                                            "success",
                                            cleaned,
                                            agent_name,
                                        )
                                    )
                                    for _deed in _round_deeds:
                                        if len(plan_turn_log) < _LEDGER_MAX_DEEDS:
                                            plan_turn_log.append(_deed)
                                        else:
                                            plan_turn_log_dropped += 1

                    # Handle executor completed - just log, don't send to UI
                    elif event_type == "executor_completed":
                        self.logger.debug(
                            "[EXECUTOR COMPLETED] agent: %s",
                            getattr(event, "executor_id", "unknown"),
                        )
                        # Don't send to UI here - group_chat events already handle agent messages

                    # Handle workflow output event (streaming chunks AND final result)
                    elif event_type == "output":
                        executor_id = getattr(event, "executor_id", None)
                        output_data = event.data
                        # Streaming AgentResponseUpdate chunks emit per-token —
                        # log at DEBUG to avoid flooding INFO logs (hundreds per response).
                        # Other output types (final results, etc.) keep INFO.
                        _data_type_name = type(output_data).__name__
                        if _data_type_name == "AgentResponseUpdate":
                            self.logger.debug(
                                "[OUTPUT] executor=%s data_type=%s",
                                executor_id,
                                _data_type_name,
                            )
                        else:
                            self.logger.info(
                                "[OUTPUT] executor=%s data_type=%s",
                                executor_id,
                                _data_type_name,
                            )

                        # Streaming chunk from an agent executor.
                        # Only process chunks for agents that are within a formal
                        # RequestSent → ResponseReceived window.  Chunks emitted by
                        # the SDK's internal broadcast (should_respond=False) arrive
                        # outside that window and are discarded here, preventing the
                        # duplicate-message problem without altering SDK behaviour.
                        if isinstance(output_data, AgentResponseUpdate) and executor_id:
                            self.logger.debug(
                                "[OUTPUT] executor_id='%s' actively_responding=%s",
                                executor_id,
                                agents_actively_responding,
                            )
                            if executor_id not in agents_actively_responding:
                                self.logger.debug(
                                    "[OUTPUT] Discarding broadcast chunk from '%s' "
                                    "(outside active-response window)",
                                    executor_id,
                                )
                            else:
                                chunk_text = output_data.text or ""
                                if chunk_text:
                                    agent_stream_buffers[executor_id] = (
                                        agent_stream_buffers.get(executor_id, "")
                                        + chunk_text
                                    )
                                _record_tool_contents(
                                    agent_tool_logs.setdefault(executor_id, []),
                                    agent_tool_pending.setdefault(executor_id, {}),
                                    getattr(output_data, "contents", None),
                                    executor_id,
                                )
                                try:
                                    await streaming_agent_response_callback(
                                        executor_id,
                                        output_data,
                                        False,
                                        user_id,
                                        process_id=plan_id,
                                    )
                                except Exception as e:
                                    self.logger.error(
                                        "Error in streaming callback for agent %s: %s",
                                        executor_id,
                                        e,
                                    )
                                # Materialise any file outputs to the workspace.
                                if workspace_id:
                                    for _c in output_data.contents or []:
                                        if getattr(_c, "type", None) == "hosted_file":
                                            _fid = getattr(_c, "file_id", None)
                                            _ap = (
                                                getattr(
                                                    _c, "additional_properties", None
                                                )
                                                or {}
                                            )
                                            _cid = (
                                                _ap.get("container_id")
                                                if isinstance(_ap, dict)
                                                else None
                                            )
                                            _fname = (
                                                (
                                                    _ap.get("filename")
                                                    if isinstance(_ap, dict)
                                                    else None
                                                )
                                                or getattr(_c, "name", None)
                                                or _fid
                                                or "agent_file"
                                            )
                                            if _fid:
                                                asyncio.ensure_future(
                                                    _materialize_hosted_file_to_workspace(
                                                        user_id=user_id,
                                                        workspace_id=workspace_id,
                                                        file_id=_fid,
                                                        container_id=_cid,
                                                        filename=_fname,
                                                    )
                                                )
                        # Final workflow output (list[Message] or Message)
                        elif isinstance(output_data, Message):
                            final_output = output_data.text or ""
                        elif isinstance(output_data, list):
                            # Handle list of Message objects
                            texts = []
                            for item in output_data:
                                if isinstance(item, Message):
                                    if item.text:
                                        texts.append(item.text)
                                else:
                                    texts.append(str(item))
                            final_output = "\n".join(texts)
                        elif hasattr(output_data, "text"):
                            final_output = output_data.text or ""
                        else:
                            final_output = str(output_data) if output_data else ""
                        self.logger.debug("Received workflow output event")

                except Exception as e:
                    self.logger.error(
                        f"Error processing event {type(event).__name__}: {e}",
                        exc_info=True,
                    )

            if pending_request is not None:
                await self._park_on_request_info(
                    workflow=workflow,
                    event=pending_request,
                    user_id=user_id,
                    session_id=session_id,
                    plan_id=plan_id,
                    workspace_id=workspace_id,
                )
                return

            # Extract final result
            final_text = final_output if final_output else ""

            # Log agent call summary
            self.logger.info("Agent call counts: %s", agent_call_counts)

            # Log results
            self.logger.info("\nAgent responses:")
            self.logger.info(
                "Orchestration completed. Final result length: %d chars",
                len(final_text),
            )
            self.logger.info("\nFinal result:\n%s", final_text)
            self.logger.info("=" * 50)

            # ── Persist BEFORE signalling ─────────────────────────────────────
            # The FINAL_RESULT_MESSAGE makes the UI drop planId and reload the
            # session from Cosmos. Measured on revision 132: WS final at
            # 13.859 → client GET /chat/sessions at 14.444 → write-back at
            # 14.868. The reload ran 424 ms before the result existed, so the
            # page showed the previous state until a manual refresh. Durable
            # writes (plan store + chat session) therefore precede the signal.
            #
            # is_final=True routes through PlanService.handle_agent_messages, which
            # persists the final agent message to the plan store AND flips the plan
            # to overall_status=completed — the state that USED to happen only when
            # the frontend echoed the final. Now it is guaranteed, headless.
            if final_text:
                await self._persist_agent_message(
                    plan_id=plan_id,
                    user_id=user_id,
                    agent_name="Group_Chat_Manager",
                    content=final_text,
                    is_final=True,
                )

            # ── Write Plan result back to chat session ────────────────────────
            # This closes the visibility gap: after Plan execution the chat
            # agent will have the Plan outcome in its Cosmos history so the
            # user can continue the conversation with full context.
            if final_text and session_id:
                try:
                    from common.services.chat_cosmos_service import (
                        get_chat_cosmos_service,
                    )

                    _wb_metadata: dict[str, Any] = {
                        "intent": "task",
                        "type": "plan_result",
                        "plan_id": plan_id,
                        "turn_log": plan_turn_log,
                    }
                    if plan_turn_log_dropped:
                        _wb_metadata["turn_log_dropped"] = plan_turn_log_dropped
                    _chat_svc_wb = await get_chat_cosmos_service()
                    await _chat_svc_wb.add_message(
                        session_id=session_id,
                        user_id=user_id,
                        content=final_text,
                        role="assistant",
                        metadata=_wb_metadata,
                    )
                    self.logger.info(
                        "Plan result written back to chat session %s (%d chars)",
                        session_id[:12],
                        len(final_text),
                    )
                except Exception as _wb_err:
                    self.logger.warning(
                        "Could not write Plan result to chat session %s: %s",
                        session_id,
                        _wb_err,
                    )

            # ── Signal the UI: everything it will reload is already durable ──
            # send_status_update_async already wraps this in {type, data}.
            # Pre-wrapping here produced {type, data:{type, data:{...}}} on the
            # wire — the frontend only survived it via defensive fallbacks.
            await connection_config.send_status_update_async(
                {
                    "content": final_text,
                    "status": "completed",
                    "timestamp": asyncio.get_event_loop().time(),
                },
                user_id,
                message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
                process_id=plan_id,
            )
            self.logger.info("Final result sent via WebSocket to user '%s'", user_id)

            # Checkpoint lineage is not read by the UI; it can go last.
            if plan_id:
                try:
                    await self._purge_checkpoint_lineage_by_id(user_id, plan_id)
                except Exception as cleanup_error:
                    self.logger.warning(
                        "Checkpoint cleanup failed for plan %s: %s",
                        plan_id,
                        cleanup_error,
                    )

        except Exception as e:
            # Error handling
            self.logger.error("Unexpected orchestration error: %s", e, exc_info=True)
            self.logger.error("Error type: %s", type(e).__name__)
            if hasattr(e, "__dict__"):
                self.logger.error("Error attributes: %s", e.__dict__)
            self.logger.info("=" * 50)

            # Mirror of upstream dev-v4: mark the plan FAILED in the store so it
            # cannot resurrect as an in_progress zombie (a page refresh re-triggers
            # orphaned orchestrations; stale approvals re-send). A DB error here
            # must never mask the original orchestration error.
            try:
                if plan_id:
                    # Lazy import: the test harness stubs common.database as a
                    # bare Mock, which breaks this import at module load.
                    from common.database.database_factory import DatabaseFactory

                    memory_store = await DatabaseFactory.get_database(user_id=user_id)
                    plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
                    if plan:
                        plan.overall_status = PlanStatus.failed
                        await memory_store.update_plan(plan)
                        self.logger.info("Plan '%s' status updated to FAILED", plan_id)
                        await self._purge_checkpoint_lineage(plan)
            except Exception as db_error:
                self.logger.error(
                    "Failed to update plan status to FAILED: %s", db_error
                )

            # Send error status to user
            try:
                await connection_config.send_status_update_async(
                    {
                        "content": f"Error during orchestration: {str(e)}",
                        "status": "error",
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                    user_id,
                    message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
                    process_id=plan_id,
                )
            except Exception as send_error:
                self.logger.error("Failed to send error status: %s", send_error)
            raise
