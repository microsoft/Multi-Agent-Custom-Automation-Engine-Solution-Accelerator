"""Las capacidades propias del orquestador, junto a ``compose``.

Lo que el orquestador puede resolver él mismo lo resuelve en la MISMA llamada:
una imagen, una búsqueda viva, un cálculo, los toolboxes del proyecto. Componer
un especialista para eso significa publicar una versión de agente en Foundry y
armar un workflow para terminar llamando la misma tool. ``compose`` queda para
el trabajo que sí necesita especialistas.

La imagen es el caso que no tiene dónde vivir: la tool contesta con los bytes EN
LÍNEA (base64) y nada más — ni archivo de Foundry ni contenedor. Se guardan en el
MISMO ``GeneratedFileStore`` que usa cualquier otro archivo generado y se anuncian
como contenido ``hosted_file``, que es el tipo del framework: de ahí en adelante
manda la rama que ya existe en el manejador SSE (evento ``generated_file``, la
imagen dentro del mensaje, descriptor persistido). Sin carril nuevo y sin shims.
"""

import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from agent_framework import AgentResponseUpdate, Content, WorkflowEvent

from common.services.event_store import EventStore, MemoryContainer, set_event_store
from v4.api import router


@pytest.fixture(autouse=True)
def _ledger_store():
    """El turno escribe su ledger (objetivo, hechos, veredictos) en el store
    de eventos; acá vive en memoria, con el mismo contrato de identidad."""
    store = EventStore(MemoryContainer())
    set_event_store(store)
    yield store
    set_event_store(None)


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _Stream:
    def __init__(self, events):
        self._events = list(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        return self._events.pop(0)


def _fake_openai(*replies):
    """Un turno hace varias llamadas (ejecución, síntesis, veredicto). Las
    respuestas se consumen en orden y la última se repite si el turno pide
    más. ``calls`` guarda todas; ``create_kwargs`` la PRIMERA (la oferta)."""
    queue = list(replies)

    class _Fake:
        instances: list = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.closed = False
            self.create_kwargs = None
            self.calls: list = []
            _Fake.instances.append(self)

            async def create(**kw):
                self.calls.append(kw)
                if self.create_kwargs is None:
                    self.create_kwargs = kw
                return queue.pop(0) if len(queue) > 1 else queue[0]

            self.responses = SimpleNamespace(create=create)

        async def close(self):
            self.closed = True

    return _Fake


def _client(toolboxes=None, image_deployment="gpt-image-2"):
    c = router._RouterChatClient.__new__(router._RouterChatClient)
    c.agent_name = "Composer"
    c._openai_base_url = "https://account.invalid/openai"
    c._api_version = "2025-03-01-preview"
    c._model = "gpt-5.4-mini"
    c._reasoning = {"effort": "medium"}
    c._reasoning_eval = {"effort": "low"}
    c._image_deployment = image_deployment
    c._toolboxes = list(toolboxes or [])
    c._memory_store = None
    c.composition = None
    c._user_id = "u1"
    c._user_access_token = None
    c._workspace_id = None
    # Tools del workspace: sin workspace montado no se conectan (None).
    c._ws_tool = None
    c._ws_tool_lock = asyncio.Lock()
    c._ws_specs = None
    c._ws_names = set()
    c._ws_identity = {}
    c._user_cred = None
    c._bearer = AsyncMock(return_value="tok")
    c._turn_id = "t1"
    c._session_id = "s1"
    c._ledger_unavailable = False
    return c


def _image_item(result, output_format=None):
    return SimpleNamespace(
        type="image_generation_call", result=result, output_format=output_format
    )


def _text(chunk):
    return SimpleNamespace(type="response.output_text.delta", delta=chunk)


def _done(item):
    return SimpleNamespace(type="response.output_item.done", item=item)


async def _collect(client, prompt="hola"):
    return [u async for u in client.invoke(prompt, history=[])]


# ── lo que el orquestador ofrece en su propia llamada ────────────────────────


@pytest.mark.asyncio
async def test_the_orchestrator_offers_compose_and_its_own_capabilities():
    fake = _fake_openai(_Stream([]))
    with patch("openai.AsyncOpenAI", fake):
        await _collect(_client())

    tools = fake.instances[-1].create_kwargs["tools"]
    # La decisión de componer es del dueño: ``compose`` con las cinco
    # semánticas del framework va en la misma oferta que sus capacidades
    # propias.
    assert tools[0]["name"] == "compose"
    assert tools[0]["parameters"]["properties"]["pattern"]["enum"] == list(
        router._PATTERNS
    )
    assert [t["type"] for t in tools[1:]] == [
        "image_generation",
        "web_search",
        "code_interpreter",
    ]
    assert tools[3]["container"] == {"type": "auto"}


@pytest.mark.asyncio
async def test_invalid_composition_then_direct_preserves_tool_call_history():
    invalid = SimpleNamespace(
        type="function_call",
        name="compose",
        call_id="invalid-compose",
        arguments=json.dumps(
            {"pattern": "sequential", "task": "retry this", "participants": []}
        ),
    )
    direct = SimpleNamespace(
        type="function_call",
        name="compose",
        call_id="direct-compose",
        arguments=json.dumps(
            {"pattern": "direct", "task": "Run this directly", "participants": []}
        ),
    )
    fake = _fake_openai(
        _Stream([_done(invalid)]),
        _Stream([_done(direct)]),
        _Stream([_text("Completed.")]),
    )

    with patch("openai.AsyncOpenAI", fake):
        await _collect(_client(), prompt="Original request")

    retry_input = fake.instances[-1].calls[1]["input"]
    assert retry_input == [
        {"role": "user", "content": "Run this directly"},
        {
            "type": "function_call",
            "call_id": "invalid-compose",
            "name": "compose",
            "arguments": invalid.arguments,
        },
        {
            "type": "function_call_output",
            "call_id": "invalid-compose",
            "output": (
                "ERROR: pattern 'sequential' requires at least one participant. "
                "Vuelve a componer eligiendo al menos un participante para este "
                "patrón (o usa 'direct')."
            ),
        },
    ]


@pytest.mark.asyncio
async def test_a_composed_run_leaves_facts_without_a_verdict(
    _ledger_store, monkeypatch
):
    # La orquestación elegida corre dentro del turno y bajo la misma ley: lo
    # que cada participante observó son hechos del turno que quedan en el
    # ledger, sin veredicto que los juzgue. Lo que dijeron ya salió por sus
    # eventos: no se repite.
    call = SimpleNamespace(
        type="function_call",
        name="compose",
        arguments=json.dumps(
            {
                "pattern": "sequential",
                "task": "pyproject bajo src/",
                "participants": [
                    {"name": "SrcAgent", "description": "d", "system_message": "s"}
                ],
            }
        ),
    )
    fake = _fake_openai(_Stream([_done(call)]), _verdict(True))
    client = _client()
    result = json.dumps(
        {"status": "success", "details": {"matches": ["src/backend/pyproject.toml"]}}
    )

    async def _run_pattern(pattern, task, participants, history, *, resume=None):
        assert resume is None
        yield WorkflowEvent(
            "output",
            data=AgentResponseUpdate(
                contents=[
                    Content.from_function_call(
                        "c1",
                        "workspace_search_files",
                        arguments='{"query": "pyproject"}',
                    )
                ],
                role="assistant",
            ),
            executor_id="SrcAgent",
        )
        yield WorkflowEvent(
            "output",
            data=AgentResponseUpdate(
                contents=[Content.from_function_result("c1", result=result)],
                role="assistant",
            ),
            executor_id="SrcAgent",
        )
        yield WorkflowEvent(
            "output",
            data=AgentResponseUpdate(
                contents=[Content.from_text("Encontré src/backend/pyproject.toml")],
                role="assistant",
            ),
            executor_id="SrcAgent",
        )
        # Un especialista publicado en Foundry: sus tools corren alojadas y
        # llegan como mcp_server_tool_call/result; el nombre va en la llamada.
        yield WorkflowEvent(
            "output",
            data=AgentResponseUpdate(
                contents=[
                    Content.from_mcp_server_tool_call(
                        "m1",
                        "workspace_list_entries",
                        server_name="MacaeMcpServer",
                        arguments='{"path": "/"}',
                    ),
                    # Resultado alojado como lista de Content (así llega del
                    # framework): el hecho guarda el TEXTO, no el repr.
                    Content.from_mcp_server_tool_result(
                        "m1",
                        output=[
                            Content.from_text(
                                '{"status": "success", "details": {"entries": ["src"]}}'
                            )
                        ],
                    ),
                ],
                role="assistant",
            ),
            executor_id="RuffAgent",
        )

    monkeypatch.setattr(client, "_run_pattern", _run_pattern)
    with patch("openai.AsyncOpenAI", fake):
        updates = await _collect(client, prompt="un especialista que busque pyproject")

    assert [type(u).__name__ for u in updates] == ["WorkflowEvent"] * 4
    # Carril interactivo sin juez: una sola llamada al modelo (la que compuso).
    assert len(fake.instances[-1].calls) == 1
    events = await _ledger_store.history("t1")
    facts = [e["identity"] for e in events if e["kind"] == "fact"]
    assert any(i.startswith("t1:SrcAgent:workspace_search_files:") for i in facts)
    assert any(i.startswith("t1:RuffAgent:workspace_list_entries:") for i in facts)
    hosted = next(
        e
        for e in events
        if e["identity"].startswith("t1:RuffAgent:workspace_list_entries:")
    )
    assert '"entries": ["src"]' in hosted["payload"]["output"]
    assert "Content object" not in hosted["payload"]["output"]
    assert any(":workspace_search_files:" not in i for i in facts)
    assert [e for e in events if e["kind"] == "verdict"] == []
    closed = next(e for e in events if e["identity"] == "t1:closed")
    assert closed["payload"]["status"] == "completed"


@pytest.mark.asyncio
async def test_a_direct_answer_closes_the_turn_without_a_verdict(_ledger_store):
    # Carril interactivo: el dueño compone ``direct`` y contesta en la misma
    # pasada. Lo que entrega es la respuesta; el próximo evaluador es el
    # usuario, no un juez interno. El modelo se llama UNA vez: si volviera el
    # evaluador directo habría una segunda llamada (el veredicto) y este
    # conteo lo delataría —las colas de los tests de abajo le regalan un
    # ``_verdict`` que lo dejaría pasar inadvertido.
    call = SimpleNamespace(
        type="function_call",
        name="compose",
        arguments=json.dumps({"pattern": "direct", "task": "hola", "participants": []}),
    )
    fake = _fake_openai(_Stream([_done(call), _text("La respuesta directa.")]))
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        updates = await _collect(client, prompt="una pregunta directa")

    assert "".join(c.text for u in updates for c in u.contents) == (
        "La respuesta directa."
    )
    assert len(fake.instances[-1].calls) == 1
    events = await _ledger_store.history("t1")
    assert not any(e["kind"] == "verdict" for e in events)
    closed = next(e for e in events if e["identity"] == "t1:closed")
    assert closed["payload"]["status"] == "done"


@pytest.mark.asyncio
async def test_the_owner_can_ask_the_human_and_the_turn_waits(_ledger_store):
    # La compuerta humana del chat: request_human_approval termina el turno en
    # waiting_for con la solicitud como hecho; el manejador SSE la publica.
    call = SimpleNamespace(
        type="function_call",
        name="request_human_approval",
        arguments=json.dumps(
            {
                "action": "git push --receive-pack=... origin HEAD:refs/heads/main",
                "action_class": "write-shared",
                "reason": "la sonda de INC-2026-013 reproduce",
            }
        ),
    )
    fake = _fake_openai(_Stream([_text("Necesito autorización."), _done(call)]))
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        updates = await _collect(client, prompt="trabajá INC-2026-013")

    # La solicitud no puede compartir respuesta con una tool con efectos.
    assert fake.instances[-1].create_kwargs["parallel_tool_calls"] is False
    assert len(fake.instances[-1].calls) == 1  # sin veredicto: el turno espera
    req = client.approval_request
    assert req and req["action_class"] == "write-shared" and req["request_id"]
    assert (
        "".join(c.text for u in updates for c in u.contents) == "Necesito autorización."
    )
    events = await _ledger_store.history("t1")
    waiting = next(
        e for e in events if e["identity"] == f"t1:approval:{req['request_id']}"
    )
    assert waiting["payload"]["status"] == "waiting_for"
    closed = next(e for e in events if e["identity"] == "t1:closed")
    assert closed["payload"]["status"] == "waiting_for"
    indexed = await _ledger_store.find("fact", f"approval-request:{req['request_id']}")
    assert indexed["payload"]["session_id"] == "s1"
    assert indexed["payload"]["user_id"] == "u1"
    assert indexed["payload"]["status"] == "waiting_for"
    # La sesión la recupera de su hecho durable (recarga / corte del SSE).
    restored = await router._pending_chat_approval("s1", "u1")
    assert restored == {
        "request_id": req["request_id"],
        "turn_id": "t1",
        "action": req["action"],
        "action_class": "write-shared",
        "reason": req["reason"],
        "session_id": "s1",
    }
    assert await router._pending_chat_approval("s1", "other") is None
    assert await router._pending_chat_approval("s2", "u1") is None


@pytest.mark.asyncio
async def test_a_decided_request_is_no_longer_pending_for_the_session(
    _ledger_store,
):
    await _ledger_store.append(
        "fact",
        "approval-session:s1:r1",
        {"request_id": "r1", "session_id": "s1", "user_id": "u1", "action": "a"},
    )
    assert (await router._pending_chat_approval("s1", "u1"))["request_id"] == "r1"
    await _ledger_store.append(
        "fact", "approval-request:r1:decision", {"decision": "approved"}
    )
    assert await router._pending_chat_approval("s1", "u1") is None


async def _pending_approval(store, request_id="r1", session_id="s1", user_id="u1"):
    await store.append(
        "fact",
        f"approval-request:{request_id}",
        {
            "status": "waiting_for",
            "request_id": request_id,
            "turn_id": "t0",
            "session_id": session_id,
            "user_id": user_id,
            "action": "git push origin HEAD:main",
            "action_class": "write-shared",
            "reason": "r",
        },
    )


@pytest.mark.asyncio
async def test_the_human_decision_is_a_fact_and_a_system_note_not_a_user_voice(
    _ledger_store,
):
    await _pending_approval(_ledger_store)
    fake = _fake_openai(
        _Stream([_text("Ejecuto la acción autorizada.")]), _verdict(True)
    )
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        await _collect_with(
            client,
            prompt="Aprobado: push",
            approval={"request_id": "r1", "decision": "approved"},
        )
    first_input = fake.instances[-1].calls[0]["input"]
    note = [
        i for i in first_input if isinstance(i, dict) and i.get("role") == "developer"
    ]
    assert note and "r1: approved" in note[0]["content"]
    assert first_input[-1]["role"] == "user"
    events = await _ledger_store.history("t1")
    assert any(
        e["identity"] == "t1:approval:r1:approved"
        for e in events
        if e["kind"] == "fact"
    )


@pytest.mark.parametrize(
    "seed",
    [
        None,  # solicitud desconocida
        {"session_id": "other"},  # de otra sesión
        {"user_id": "other"},  # de otro usuario
    ],
)
@pytest.mark.asyncio
async def test_a_decision_without_its_own_pending_request_does_not_authorize(
    _ledger_store, seed
):
    if seed is not None:
        await _pending_approval(_ledger_store, **seed)
    fake = _fake_openai(_Stream([_text("No ejecuto.")]), _verdict(True))
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        await _collect_with(
            client,
            prompt="Aprobado: push",
            approval={"request_id": "r1", "decision": "approved"},
        )
    note = [
        i
        for i in fake.instances[-1].calls[0]["input"]
        if isinstance(i, dict) and i.get("role") == "developer"
    ]
    assert note and "no es válida" in note[0]["content"]
    assert "r1: approved" not in note[0]["content"]
    events = await _ledger_store.history("t1")
    assert not any(e["identity"].startswith("t1:approval:r1") for e in events)
    assert await _ledger_store.find("fact", "approval-request:r1:decision") is None


@pytest.mark.asyncio
async def test_a_replayed_decision_does_not_authorize_twice(_ledger_store):
    await _pending_approval(_ledger_store)
    notes = []
    for turn in ("t1", "t2"):
        fake = _fake_openai(_Stream([_text("ok")]), _verdict(True))
        client = _client()
        client._turn_id = turn
        with patch("openai.AsyncOpenAI", fake):
            await _collect_with(
                client,
                prompt="Aprobado: push",
                approval={"request_id": "r1", "decision": "approved"},
            )
        notes.append(
            next(
                i["content"]
                for i in fake.instances[-1].calls[0]["input"]
                if isinstance(i, dict) and i.get("role") == "developer"
            )
        )
    assert "r1: approved" in notes[0]
    assert "no es válida" in notes[1]


@pytest.mark.asyncio
async def test_an_approved_turn_answers_a_repeated_request_instead_of_parking(
    _ledger_store,
):
    """Medido en prod 2026-10-12 (rev 175): autorización → "Aprobado" → el
    dueño volvía a pedir autorización por la misma acción, cuatro turnos
    seguidos, con la nota de aprobación a la vista. El turno que trae la
    decisión es el turno de ejecutarla: una nueva solicitud se contesta por el
    protocolo con la autorización vigente y el turno sigue; no se aparca."""
    await _pending_approval(_ledger_store)
    again = SimpleNamespace(
        type="function_call",
        call_id="c1",
        name="request_human_approval",
        arguments=json.dumps(
            {
                "action": "git push origin HEAD:main",
                "action_class": "write-shared",
                "reason": "r",
            }
        ),
    )
    fake = _fake_openai(
        _Stream([_done(again)]),
        _Stream([_text("Ejecutado.")]),
        _verdict(True),
    )
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        updates = await _collect_with(
            client,
            prompt="Aprobado: push",
            approval={"request_id": "r1", "decision": "approved"},
        )

    assert client.approval_request is None
    second_input = fake.instances[-1].calls[1]["input"]
    answered = next(
        i
        for i in second_input
        if isinstance(i, dict) and i.get("type") == "function_call_output"
    )
    assert answered["call_id"] == "c1"
    assert json.loads(answered["output"]) == {
        "status": "already_authorized",
        "request_id": "r1",
        "action": "git push origin HEAD:main",
        "instruction": (
            "The human already authorized this action in this turn. Execute "
            "exactly the authorized action now and report its evidence; do not "
            "request authorization again."
        ),
    }
    assert "".join(c.text for u in updates for c in u.contents) == "Ejecutado."
    events = await _ledger_store.history("t1")
    assert not any(
        e["identity"].startswith("t1:approval:")
        and e["payload"].get("status") == "waiting_for"
        for e in events
    )
    closed = next(e for e in events if e["identity"] == "t1:closed")
    assert closed["payload"]["status"] == "done"


async def _collect_with(client, prompt, **kw):
    return [u async for u in client.invoke(prompt, history=[], **kw)]


# ── el libro de evidencia es del TURNO ───────────────────────────────────────


def _verdict(goal_met, reason="", corrected=""):
    return SimpleNamespace(
        output_text=json.dumps(
            {
                "goal_met": goal_met,
                "blocked": False,
                "reason": reason,
                "corrected_objective": corrected,
            }
        )
    )


def _exec_output(command, stdout, exit_code=0):
    return json.dumps(
        {
            "status": "success",
            "action": "workspace_exec",
            "summary": f"exit={exit_code} for `{command}`",
            "details": {
                "command": command,
                "cwd": "/",
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": "",
                "truncated": False,
            },
        }
    )


def test_a_fact_is_what_the_tool_observed_not_how_it_was_called():
    """Dos scripts distintos que imprimen lo mismo son el mismo hecho; otra
    salida es otro hecho; una salida que no es el envelope se compara entera."""
    same_a = router._fact_key(_exec_output("ls", "a\nb"))
    same_b = router._fact_key(_exec_output("ls -1 | cat", "a\nb"))
    other = router._fact_key(_exec_output("ls", "a\nc"))
    assert same_a == same_b != other
    assert router._fact_key("texto plano") == router._fact_key("texto plano")
    assert router._fact_key("texto plano") != router._fact_key("otro texto")


@pytest.mark.asyncio
async def test_the_ledger_of_a_turn_is_read_by_its_owner_only(
    _ledger_store, monkeypatch
):
    await _ledger_store.append("objective", "t9", {"objective": "x", "user_id": "u1"})
    await _ledger_store.append(
        "fact", "t9:workspace_exec:abc", {"tool": "workspace_exec"}
    )
    await _ledger_store.append("objective", "t9:closed", {"status": "done"})
    await _ledger_store.append(
        "objective", "t8", {"objective": "otro", "user_id": "u1"}
    )

    monkeypatch.setattr(router, "_extract_auth", lambda request: ("u1", ""))
    body = await router.chat_turn_ledger("t9", request=None)
    assert [e["identity"] for e in body["events"]] == [
        "t9",
        "t9:workspace_exec:abc",
        "t9:closed",
    ]

    monkeypatch.setattr(router, "_extract_auth", lambda request: ("intruso", ""))
    with pytest.raises(router.HTTPException) as err:
        await router.chat_turn_ledger("t9", request=None)
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_a_plan_id_resolves_to_the_ledger_of_its_magentic_plan(
    _ledger_store, monkeypatch
):
    """La UI conoce el ``plan_id``; el dueño del ledger es el id propio del
    MPlan. Se resuelve por el documento del plan (``m_plan``), no adivinando."""
    await _ledger_store.append(
        "objective", "plan:m1", {"objective": "auditar", "user_id": "u1"}
    )
    await _ledger_store.append("verdict", "plan:m1:1", {"kind": "done"})
    plan = SimpleNamespace(m_plan={"id": "m1"})
    store = SimpleNamespace(get_plan=AsyncMock(return_value=plan))
    monkeypatch.setattr(
        router.DatabaseFactory, "get_database", AsyncMock(return_value=store)
    )
    monkeypatch.setattr(router, "_extract_auth", lambda request: ("u1", ""))

    body = await router.chat_turn_ledger("p-ui", request=None)

    assert body["owner"] == "plan:m1"
    assert [e["identity"] for e in body["events"]] == ["plan:m1", "plan:m1:1"]
    store.get_plan.assert_awaited_once_with("p-ui")


@pytest.mark.asyncio
async def test_workspace_tool_discovery_strips_identity_and_caches_metadata():
    class _Fn:
        name = "workspace_read_file"
        description = "read a file"

        def parameters(self):
            return {
                "properties": {
                    "user_id": {"type": "string"},
                    "workspace_id": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["user_id", "workspace_id", "path"],
            }

    class _Tool:
        enters = 0

        def __init__(self, **_kwargs):
            self.functions = [_Fn()]

        async def __aenter__(self):
            type(self).enters += 1
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    c = _client()
    c._workspace_id = "my-repo"
    cfg = SimpleNamespace(name="ws", description="workspace", url="https://mcp.invalid")
    with (
        patch("v4.api.router.ReconnectingMCPTool", _Tool),
        patch(
            "v4.magentic_agents.models.agent_models.MCPConfig.from_env",
            return_value=cfg,
        ),
    ):
        first = await c._workspace_tools()
        second = await c._workspace_tools()

    assert _Tool.enters == 1
    assert first == second
    assert first == [
        {
            "type": "function",
            "name": "workspace_read_file",
            "description": "read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        }
    ]
    assert c._ws_identity == {"workspace_read_file": ("user_id", "workspace_id")}
    assert c._ws_names == {"workspace_read_file"}


@pytest.mark.asyncio
async def test_workspace_tool_results_are_serialized_when_not_text_chunks():
    class _Tool:
        async def call_tool(self, name, **kwargs):
            assert name == "workspace_read_file"
            assert kwargs == {
                "path": "README.md",
                "user_id": "u1",
                "workspace_id": "repo",
            }
            return {"status": "ok", "path": "README.md"}

    c = _client()
    c._workspace_id = "repo"
    c._ws_tool = _Tool()
    c._ws_identity = {"workspace_read_file": ("user_id", "workspace_id")}

    out = await c._call_workspace_tool("workspace_read_file", '{"path":"README.md"}')

    assert json.loads(out) == {"status": "ok", "path": "README.md"}


@pytest.mark.asyncio
async def test_a_generated_artifact_ends_the_turn_without_a_text_verdict(_ledger_store):
    class _Store:
        async def save(self, file_id, filename, data):
            return True

    fake = _fake_openai(
        _Stream(
            [
                _done(
                    SimpleNamespace(
                        type="function_call",
                        name="compose",
                        arguments=json.dumps(
                            {"pattern": "direct", "task": "hola", "participants": []}
                        ),
                    )
                )
            ]
        ),
        _Stream([_done(_image_item(base64.b64encode(PNG).decode()))]),
    )
    with (
        patch("openai.AsyncOpenAI", fake),
        patch(
            "v4.common.services.generated_file_store.GeneratedFileStore.get_instance",
            return_value=_Store(),
        ),
    ):
        updates = await _collect(_client())

    (content,) = [x for u in updates for x in u.contents]
    assert content.type == "hosted_file"
    assert len(fake.instances[-1].calls) == 2
    events = await _ledger_store.history("t1")
    assert not any(e["kind"] == "verdict" for e in events)
    closed = next(e for e in events if e["identity"] == "t1:closed")
    assert closed["payload"]["status"] == "done"


@pytest.mark.asyncio
async def test_every_declared_toolbox_is_attached_with_the_preview_gate():
    fake = _fake_openai(_Stream([]))
    boxes = [("Toolbox", "https://p.invalid/toolboxes/Toolbox/mcp?api-version=v1")]
    with patch("openai.AsyncOpenAI", fake):
        await _collect(_client(toolboxes=boxes))

    (mcp,) = [
        t for t in fake.instances[-1].create_kwargs["tools"] if t["type"] == "mcp"
    ]
    assert mcp["server_label"] == "Toolbox"
    assert mcp["server_url"] == boxes[0][1]
    assert mcp["require_approval"] == "never"
    # El endpoint está detrás de una compuerta de preview: sin la cabecera
    # contesta 401 por válido que sea el token.
    assert mcp["headers"]["Foundry-Features"] == "Toolboxes=V1Preview"
    assert mcp["headers"]["Authorization"] == "Bearer tok"


@pytest.mark.asyncio
async def test_without_declared_toolboxes_none_is_attached():
    fake = _fake_openai(_Stream([]))
    with patch("openai.AsyncOpenAI", fake):
        await _collect(_client(toolboxes=[]))
    assert not [
        t for t in fake.instances[-1].create_kwargs["tools"] if t["type"] == "mcp"
    ]


@pytest.mark.asyncio
async def test_azure_reads_the_image_deployment_from_a_request_header():
    # Sin esta cabecera la llamada ENTERA contesta 400, incluso en turnos que
    # nunca iban a generar una imagen.
    fake = _fake_openai(_Stream([]))
    with patch("openai.AsyncOpenAI", fake):
        await _collect(_client(image_deployment="gpt-image-2"))
    headers = fake.instances[-1].kwargs["default_headers"]
    assert headers["x-ms-oai-image-generation-deployment"] == "gpt-image-2"


# ── la imagen entra por el canal que ya existe ───────────────────────────────


@pytest.mark.asyncio
async def test_a_generated_image_is_stored_and_announced_as_a_hosted_file():
    saved: list = []

    class _Store:
        async def save(self, file_id, filename, data):
            saved.append((file_id, filename, data))
            return True

    fake = _fake_openai(_Stream([_done(_image_item(base64.b64encode(PNG).decode()))]))
    with (
        patch("openai.AsyncOpenAI", fake),
        patch(
            "v4.common.services.generated_file_store.GeneratedFileStore.get_instance",
            return_value=_Store(),
        ),
    ):
        updates = await _collect(_client())

    # Los bytes quedaron guardados ANTES de anunciarse el enlace: no hay carrera
    # que pueda dejar la descarga en 404.
    assert len(saved) == 1
    file_id, filename, data = saved[0]
    assert data == PNG
    assert filename == f"{file_id}.png"

    (content,) = [c for u in updates for c in u.contents]
    assert content.type == "hosted_file"
    assert content.file_id == file_id
    # La rama del manejador SSE lee el nombre de additional_properties.
    assert content.additional_properties["filename"] == filename
    assert content.media_type == "image/png"


@pytest.mark.asyncio
async def test_a_code_interpreter_file_is_announced_as_a_hosted_file():
    # El archivo del code interpreter viaja como anotación del mensaje; por el
    # mismo canal que la imagen llega al chip ``generated_file`` del SSE.
    ann = SimpleNamespace(
        type="container_file_citation",
        file_id="cfile_abc",
        container_id="cntr_1",
        filename="landing.html",
    )
    cite = SimpleNamespace(type="url_citation", url="https://x.invalid")
    # El mismo archivo citado dos veces en el texto, y una segunda parte con
    # otro archivo: un chip por archivo, en orden.
    other = SimpleNamespace(
        type="container_file_citation",
        file_id="cfile_def",
        container_id="cntr_1",
        filename="chart.png",
    )
    message = SimpleNamespace(
        type="message",
        content=[
            SimpleNamespace(
                type="output_text", text="Listo.", annotations=[cite, ann, ann]
            ),
            SimpleNamespace(type="output_text", text="Y esto.", annotations=[other]),
        ],
    )
    fake = _fake_openai(_Stream([_done(message)]))
    with patch("openai.AsyncOpenAI", fake):
        updates = await _collect(_client())

    files = [c for u in updates for c in u.contents if c.type == "hosted_file"]
    assert [c.file_id for c in files] == ["cfile_abc", "cfile_def"]
    # El ámbito viaja con el archivo: el contenedor sólo existe en el endpoint
    # que lo creó, y el manejador SSE lo persiste desde ahí.
    assert files[0].additional_properties == {
        "container_id": "cntr_1",
        "filename": "landing.html",
        "openai_base_url": "https://account.invalid/openai",
        "openai_api_version": "2025-03-01-preview",
    }


@pytest.mark.asyncio
async def test_the_format_the_tool_reports_is_the_one_stored():
    saved: list = []

    class _Store:
        async def save(self, file_id, filename, data):
            saved.append(filename)
            return True

    item = _image_item(base64.b64encode(PNG).decode(), output_format="jpeg")
    fake = _fake_openai(_Stream([_done(item)]))
    with (
        patch("openai.AsyncOpenAI", fake),
        patch(
            "v4.common.services.generated_file_store.GeneratedFileStore.get_instance",
            return_value=_Store(),
        ),
    ):
        updates = await _collect(_client())

    assert saved[0].endswith(".jpeg")
    (content,) = [c for u in updates for c in u.contents]
    assert content.media_type == "image/jpeg"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["", None, "!!!no-es-base64!!!"])
async def test_an_image_call_without_usable_bytes_stores_nothing_and_does_not_raise(
    payload,
):
    class _Store:
        async def save(self, *a, **kw):  # pragma: no cover - no debe llamarse
            raise AssertionError("no hay bytes que guardar")

    fake = _fake_openai(_Stream([_done(_image_item(payload))]))
    with (
        patch("openai.AsyncOpenAI", fake),
        patch(
            "v4.common.services.generated_file_store.GeneratedFileStore.get_instance",
            return_value=_Store(),
        ),
    ):
        assert await _collect(_client()) == []


@pytest.mark.asyncio
async def test_composing_still_works_with_the_capabilities_attached():
    # Agregar capacidades no desplaza a ``compose``: sigue siendo la vía del
    # trabajo que necesita especialistas.
    call = SimpleNamespace(
        type="function_call",
        name="compose",
        arguments=json.dumps(
            {
                "pattern": "magentic",
                "task": "Auditar el repo",
                "participants": [
                    {"name": "RepoAgent", "description": "d", "system_message": "s"}
                ],
            }
        ),
    )
    fake = _fake_openai(_Stream([_done(call)]))
    client = _client()
    with patch("openai.AsyncOpenAI", fake):
        await _collect(client)
    assert client.composition is not None
    pattern, task, participants = client.composition
    assert (pattern, task) == ("magentic", "Auditar el repo")
    assert [p["name"] for p in participants] == ["RepoAgent"]


# ── el modelo del turno ──────────────────────────────────────────────────────


def _build(monkeypatch, *, model=None, toolboxes="", configured="gpt-5.4-mini"):
    from common.config.app_config import config

    monkeypatch.setattr(
        config, "AZURE_AI_PROJECT_ENDPOINT", "https://acc.invalid/api/projects/p", False
    )
    monkeypatch.setattr(config, "CHAT_ORCHESTRATOR_MODEL", configured, False)
    monkeypatch.setattr(config, "CHAT_TOOLBOXES", toolboxes, False)
    monkeypatch.setattr(config, "_get_optional", lambda name, default=None: default)
    return router._RouterChatClient("Composer", model=model)


def test_the_caller_names_the_engine_for_this_turn(monkeypatch):
    # Las fortalezas medidas difieren por tipo de trabajo; el runtime puede
    # nombrar el motor del turno en vez de dejarlo clavado en configuración.
    assert _build(monkeypatch, model="gpt-5.1-codex-mini")._model == (
        "gpt-5.1-codex-mini"
    )


def test_without_a_named_engine_the_configured_one_is_used(monkeypatch):
    assert _build(monkeypatch, configured="gpt-5.4-mini")._model == "gpt-5.4-mini"


def test_a_declared_toolbox_version_pins_the_url(monkeypatch):
    client = _build(monkeypatch, toolboxes="Toolbox:3, Otra , ,")
    assert client._toolboxes == [
        (
            "Toolbox",
            "https://acc.invalid/api/projects/p/toolboxes/Toolbox/versions/3/mcp?api-version=v1",
        ),
        (
            "Otra",
            "https://acc.invalid/api/projects/p/toolboxes/Otra/mcp?api-version=v1",
        ),
    ]


def test_no_declared_toolboxes_means_no_attachments(monkeypatch):
    assert _build(monkeypatch, toolboxes="")._toolboxes == []
