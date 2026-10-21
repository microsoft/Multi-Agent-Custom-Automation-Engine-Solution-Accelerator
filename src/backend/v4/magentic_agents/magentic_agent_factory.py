# Copyright (c) Microsoft. All rights reserved.
"""Factory for creating and managing magentic agents from JSON configurations."""

import json
import logging
from types import SimpleNamespace
from typing import Any

from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_af import TeamConfiguration
from v4.common.services.team_service import TeamService
from v4.magentic_agents.foundry_agent import FoundryAgentTemplate
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig

# from v4.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
#                                                     SearchConfig)
from v4.magentic_agents.proxy_agent import ProxyAgent


class UnsupportedModelError(Exception):
    """Raised when an unsupported model is specified."""


class InvalidConfigurationError(Exception):
    """Raised when agent configuration is invalid."""


def _with_workspace(
    instructions: str,
    user_id: str,
    workspace_id: str | None,
    has_mcp: bool,
    chat_toolboxes: str | None = None,
) -> str:
    """Inyectar contexto de workspace y/o Toolbox en las instrucciones.

    - workspace_id presente: añadir el contexto del workspace.
    - chat_toolboxes presente: añadir el contexto del Toolbox mediante el
      inspector de MacaeMcpServer, independientemente de workspace_id.

    El carril de chat ya lo hace; el de plan no lo hacía, y un agente con las
    tools de MacaeMcpServer pero sin el identificador llamaba ``workspace_exec``
    con un nombre inventado (``macae-local``) y respondía que no tenía acceso.
    """
    result = instructions
    # Contexto del workspace (si aplica)
    if has_mcp and workspace_id:
        result += (
            f"\n\nWORKSPACE: trabajas sobre el workspace persistente '{workspace_id}' "
            f"del usuario '{user_id}'. Es el ÚNICO que puedes ver y ya está montado; "
            "no existe ningún otro y no debes inventar su nombre. Para mirarlo usa "
            "las tools de MacaeMcpServer pasando exactamente esos dos valores: "
            f"workspace_list_entries {{user_id='{user_id}', workspace_id='{workspace_id}', "
            "path=''}}, workspace_read_file, workspace_search_content y workspace_exec "
            "para comandos (git status, git log, pruebas). Nunca afirmes que no tienes "
            "acceso sin haber llamado antes a una de esas tools."
        )
    # Contexto del Toolbox (independiente del workspace, pero SÍ depende de MCP)
    # El Toolbox del proyecto y los servidores MCP externos se alcanzan por las
    # MISMAS tools de inspector de MacaeMcpServer — no se adjuntan al agente
    # como en el carril directo. Sin decírselo, el modelo responde "no tengo
    # acceso a web/GitHub/…" aunque la capacidad esté a una tool de distancia.
    # Sin MCP no hay vía, así que la consciencia sería falsa: se omite.
    if has_mcp and chat_toolboxes:
        result += (
            f"\n\nTOOL BOX Y SERVIDORES EXTERNOS: a través de MacaeMcpServer "
            f"tienes acceso al Tool Box '{chat_toolboxes}' del proyecto y a "
            "servidores MCP externos registrados. Ahí viven capacidades que NO "
            "se te adjuntan explícitamente, como búsqueda web en vivo, GitHub y "
            "otros sistemas. Para usarlas: list_connected_servers (qué "
            "servidores hay), discover_mcp_capabilities(server_name) o "
            "tool_search(query) (qué tools expone cada uno) y call_external_tool"
            "(server_name, target_tool, arguments) para invocarlas. Nunca "
            "afirmes que no tienes búsqueda web ni acceso a un sistema externo "
            "sin haber llamado antes a list_connected_servers o tool_search. "
            "Si un servidor publica un recurso de skills (skill://index.json), "
            "léelo con read_external_resource: trae recetas versionadas de cómo "
            "usar sus herramientas para tareas concretas."
        )
    return result


class MagenticAgentFactory:
    """Factory for creating and managing magentic agents from JSON configurations."""

    def __init__(self, team_service: TeamService | None = None):
        self.logger = logging.getLogger(__name__)
        self._agent_list: list = []
        self.team_service = team_service

    # Ensure only an explicit boolean True in the source sets this flag.
    def extract_use_reasoning(self, agent_obj):
        # Support both dict and attribute-style objects
        if isinstance(agent_obj, dict):
            val = agent_obj.get("use_reasoning", False)
        else:
            val = getattr(agent_obj, "use_reasoning", False)

        # Accept only the literal boolean True
        return True if val is True else False

    async def create_agent_from_config(
        self,
        user_id: str,
        agent_obj: SimpleNamespace | Any,
        team_config: TeamConfiguration,
        memory_store: DatabaseBase,
        user_access_token: str | None = None,
        workspace_id: str | None = None,
        chat_toolboxes: str | None = None,
    ) -> FoundryAgentTemplate | ProxyAgent:
        """
        Create an agent from configuration object.

        Args:
            user_id: User ID
            agent_obj: Agent object from parsed JSON (SimpleNamespace)
            team_model: Model name to determine which template to use

        Returns:
            Configured agent instance

        Raises:
            UnsupportedModelError: If model is not supported
            InvalidConfigurationError: If configuration is invalid
        """
        # Get model from agent config, team model, or environment
        deployment_name = getattr(agent_obj, "deployment_name", None)

        if agent_obj.name.lower() == "proxyagent":
            self.logger.info("Creating ProxyAgent")
            return ProxyAgent(user_id=user_id)

        if not deployment_name:
            raise InvalidConfigurationError(
                f"Agent '{agent_obj.name}' missing requiered 'deployment_name' field"
            )

        # Determine which template to use
        # Usage
        use_reasoning = self.extract_use_reasoning(agent_obj)

        # Regla, no reparación: el orquestador decide por tarea si un agente
        # razona, y el deployment se deriva de esa decisión. Un agente
        # ``use_reasoning`` corre en el modelo de razonamiento configurado y
        # recibe ``reasoning.effort``; en otro modelo ese parámetro es un 400
        # (medido 2026-10-01: gpt-4.1-mini → "unsupported_parameter:
        # reasoning.effort"). Nada depende de un equipo registrado: la misma
        # regla rige donde se compone (roster) y donde se construye (aquí).
        if use_reasoning and deployment_name != config.REASONING_MODEL_NAME:
            self.logger.info(
                "Agent '%s' use_reasoning: deployment '%s' → '%s' (modelo de razonamiento)",
                agent_obj.name,
                deployment_name,
                config.REASONING_MODEL_NAME,
            )
            deployment_name = config.REASONING_MODEL_NAME

        # Validate supported models
        supported_models = json.loads(config.SUPPORTED_MODELS)

        if deployment_name not in supported_models:
            raise UnsupportedModelError(
                f"Model '{deployment_name}' not supported. Supported: {supported_models}"
            )

        # Validate reasoning constraints
        if use_reasoning:
            if getattr(agent_obj, "use_bing", False) or getattr(
                agent_obj, "coding_tools", False
            ):
                raise InvalidConfigurationError(
                    f"Agent cannot use Bing search or coding tools. "
                    f"Agent '{agent_obj.name}' has use_bing={getattr(agent_obj, 'use_bing', False)}, "
                    f"coding_tools={getattr(agent_obj, 'coding_tools', False)}"
                )

        # Only create configs for explicitly requested capabilities
        index_name = getattr(agent_obj, "index_name", None)
        use_rag_value = getattr(agent_obj, "use_rag", False)
        use_mcp_value = getattr(agent_obj, "use_mcp", False)

        self.logger.info(
            "🔍 DEBUG: Agent '%s' config: use_rag=%s, use_mcp=%s, index_name='%s'",
            agent_obj.name,
            use_rag_value,
            use_mcp_value,
            index_name,
        )

        search_config = (
            SearchConfig.from_env(index_name) if use_rag_value and index_name else None
        )

        self.logger.info(
            "🔍 DEBUG: search_config=%s (will %s Azure AI Search)",
            "CREATED" if search_config else "None",
            "USE" if search_config else "NOT USE",
        )

        mcp_config = MCPConfig.from_env() if use_mcp_value else None

        self.logger.info(
            "🔍 DEBUG: mcp_config=%s (will %s MCP)",
            "CREATED" if mcp_config else "None",
            "USE" if mcp_config else "NOT USE",
        )

        self.logger.info(
            "Creating agent '%s' with model '%s' (use_rag=%s, use_mcp=%s, Template: %s)",
            agent_obj.name,
            deployment_name,
            use_rag_value,
            use_mcp_value,
            "Reasoning" if use_reasoning else "Foundry",
        )

        agent = FoundryAgentTemplate(
            agent_name=agent_obj.name,
            agent_description=getattr(agent_obj, "description", ""),
            agent_instructions=_with_workspace(
                getattr(agent_obj, "system_message", ""),
                user_id,
                workspace_id,
                use_mcp_value,
                chat_toolboxes,
            ),
            use_reasoning=use_reasoning,
            model_deployment_name=deployment_name,
            enable_code_interpreter=getattr(agent_obj, "coding_tools", False),
            enable_bing=getattr(agent_obj, "use_bing", False),
            enable_file_search=getattr(agent_obj, "use_file_search", False),
            enable_web_search=getattr(agent_obj, "use_web_search", False),
            enable_image_generation=getattr(agent_obj, "use_image_generation", False),
            enable_azure_functions=getattr(agent_obj, "use_azure_functions", False),
            enable_sharepoint=getattr(agent_obj, "use_sharepoint", False),
            enable_browser_automation=getattr(
                agent_obj, "use_browser_automation", False
            ),
            enable_fabric=getattr(agent_obj, "use_fabric", False),
            enable_bing_custom_search=getattr(
                agent_obj, "use_bing_custom_search", False
            ),
            project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
            mcp_config=mcp_config,
            search_config=search_config,
            team_service=self.team_service,
            team_config=team_config,
            memory_store=memory_store,
            user_access_token=user_access_token,
        )

        await agent.open()
        self.logger.info(
            "Successfully created and initialized agent '%s'", agent_obj.name
        )
        return agent

    async def get_agents(
        self,
        user_id: str,
        team_config_input: TeamConfiguration,
        memory_store: DatabaseBase,
        user_access_token: str | None = None,
        workspace_id: str | None = None,
    ) -> list:
        """
        Create and return a team of agents from JSON configuration.

        Args:
            user_id: User ID
            team_config_input: team configuration object from cosmos db

        Returns:
            List of initialized agent instances
        """
        # self.logger.info(f"Loading team configuration from: {file_path}")

        try:
            initalized_agents = []

            # El nombre del Tool Box es configuración del proyecto, igual para
            # todos los participantes: se resuelve una vez y viaja a cada agente
            # con MCP para que su instrucción nombre el Tool Box real.
            chat_toolboxes = getattr(config, "CHAT_TOOLBOXES", None) or None

            for i, agent_cfg in enumerate(team_config_input.agents, 1):
                try:
                    self.logger.info(
                        "Creating agent %d/%d: %s",
                        i,
                        len(team_config_input.agents),
                        agent_cfg.name,
                    )

                    agent = await self.create_agent_from_config(
                        user_id,
                        agent_cfg,
                        team_config_input,
                        memory_store,
                        user_access_token=user_access_token,
                        workspace_id=workspace_id,
                        chat_toolboxes=chat_toolboxes,
                    )
                    initalized_agents.append(agent)
                    self._agent_list.append(agent)  # Keep track for cleanup

                    self.logger.info(
                        "✅ Agent %d/%d created: %s",
                        i,
                        len(team_config_input.agents),
                        agent_cfg.name,
                    )

                except (UnsupportedModelError, InvalidConfigurationError) as e:
                    self.logger.warning(f"Skipped agent {agent_cfg.name}: {e}")
                    print(f"Skipped agent {agent_cfg.name}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Failed to create agent {agent_cfg.name}: {e}")
                    print(f"Failed to create agent {agent_cfg.name}: {e}")
                    continue

            self.logger.info(
                "Successfully created %d/%d agents for team '%s'",
                len(initalized_agents),
                len(team_config_input.agents),
                team_config_input.name,
            )
            return initalized_agents

        except Exception as e:
            self.logger.error(f"Failed to load team configuration: {e}")
            raise

    @classmethod
    async def cleanup_all_agents(cls, agent_list: list):
        """Clean up all created agents."""
        logger = logging.getLogger(__name__)
        logger.info(f"Cleaning up {len(agent_list)} agents")

        for agent in agent_list:
            try:
                await agent.close()
            except Exception as ex:
                name = getattr(
                    agent,
                    "agent_name",
                    getattr(agent, "__class__", type("X", (object,), {})).__name__,
                )
                logger.warning(f"Error closing agent {name}: {ex}")

        agent_list.clear()
        logger.info("Agent cleanup completed")
