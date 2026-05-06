# Copyright (c) Microsoft. All rights reserved.
"""Factory for creating and managing agents from JSON team configurations.

Replaces v4/magentic_agents/magentic_agent_factory.py.
Key change: uses AgentTemplate (FoundryChatClient + Agent, GA) instead of
FoundryAgentTemplate (AzureAIAgentClient + ChatAgent, deprecated).
"""

import json
import logging
from types import SimpleNamespace
from typing import List, Optional, Union

from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration

from agents.agent_template import AgentTemplate
from agents.proxy_agent import ProxyAgent
from config.mcp_config import MCPConfig, SearchConfig


class UnsupportedModelError(Exception):
    """Raised when the configured model is not in the supported-models list."""


class InvalidConfigurationError(Exception):
    """Raised when the agent JSON configuration is invalid."""


class AgentFactory:
    """Create and manage teams of agents from JSON configuration.

    Usage::

        factory = AgentFactory()
        agents = await factory.get_agents(user_id, team_config, memory_store)
        # ... use agents in orchestrator ...
        await factory.close_all()
    """

    def __init__(self, team_service: Optional[object] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.team_service = team_service
        self._agent_list: List = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_use_reasoning(agent_obj: SimpleNamespace) -> bool:
        """Return True only when the agent config explicitly sets use_reasoning=True."""
        val = (
            agent_obj.get("use_reasoning", False)
            if isinstance(agent_obj, dict)
            else getattr(agent_obj, "use_reasoning", False)
        )
        return val is True

    # ------------------------------------------------------------------
    # Single-agent creation
    # ------------------------------------------------------------------

    async def create_agent_from_config(
        self,
        user_id: str,
        agent_obj: SimpleNamespace,
        team_config: TeamConfiguration,
        memory_store: DatabaseBase,
    ) -> Union[AgentTemplate, ProxyAgent]:
        """Create and open a single agent from a SimpleNamespace config object.

        Args:
            user_id:      The requesting user ID (passed to ProxyAgent).
            agent_obj:    Per-agent config parsed from the team JSON.
            team_config:  The parent team configuration.
            memory_store: Cosmos DB store for agent persistence.

        Returns:
            An initialized ``AgentTemplate`` or ``ProxyAgent``.

        Raises:
            UnsupportedModelError:      If the deployment name is not in SUPPORTED_MODELS.
            InvalidConfigurationError:  If reasoning + incompatible tools are requested.
        """
        deployment_name = getattr(agent_obj, "deployment_name", None)

        # ProxyAgent does not need a deployment
        if not deployment_name and getattr(agent_obj, "name", "").lower() == "proxyagent":
            self.logger.info("Creating ProxyAgent (user_id=%s).", user_id)
            return ProxyAgent(user_id=user_id)

        # Validate model
        supported_models = json.loads(config.SUPPORTED_MODELS)
        if deployment_name not in supported_models:
            raise UnsupportedModelError(
                f"Model '{deployment_name}' is not supported. "
                f"Supported models: {supported_models}"
            )

        use_reasoning = self._extract_use_reasoning(agent_obj)

        # Reasoning models cannot be combined with Bing or code tools
        if use_reasoning:
            use_bing = getattr(agent_obj, "use_bing", False)
            coding_tools = getattr(agent_obj, "coding_tools", False)
            if use_bing or coding_tools:
                raise InvalidConfigurationError(
                    f"Agent '{agent_obj.name}' has use_reasoning=True but also requests "
                    f"use_bing={use_bing} or coding_tools={coding_tools}, which are "
                    "incompatible with reasoning models."
                )

        # Build optional tool configs
        index_name = getattr(agent_obj, "index_name", None)
        search_config: Optional[SearchConfig] = (
            SearchConfig.from_env(index_name)
            if getattr(agent_obj, "use_rag", False)
            else None
        )
        mcp_config: Optional[MCPConfig] = (
            MCPConfig.from_env()
            if getattr(agent_obj, "use_mcp", False)
            else None
        )

        self.logger.info(
            "Creating AgentTemplate '%s' (model=%s, use_rag=%s, use_mcp=%s, reasoning=%s).",
            agent_obj.name,
            deployment_name,
            search_config is not None,
            mcp_config is not None,
            use_reasoning,
        )

        agent = AgentTemplate(
            agent_name=agent_obj.name,
            agent_description=getattr(agent_obj, "description", ""),
            agent_instructions=getattr(agent_obj, "system_message", ""),
            use_reasoning=use_reasoning,
            model_deployment_name=deployment_name,
            project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
            enable_code_interpreter=getattr(agent_obj, "coding_tools", False),
            mcp_config=mcp_config,
            search_config=search_config,
            team_config=team_config,
            memory_store=memory_store,
        )

        await agent.open()
        self.logger.info("Initialized agent '%s'.", agent_obj.name)
        return agent

    # ------------------------------------------------------------------
    # Team creation
    # ------------------------------------------------------------------

    async def get_agents(
        self,
        user_id: str,
        team_config_input: TeamConfiguration,
        memory_store: DatabaseBase,
    ) -> List:
        """Create and return a full team of agents from a TeamConfiguration.

        Args:
            user_id:           The requesting user ID.
            team_config_input: Parsed team configuration from Cosmos DB.
            memory_store:      Cosmos DB store for agent persistence.

        Returns:
            List of initialized agent instances (AgentTemplate or ProxyAgent).
        """
        initialized: List = []

        for i, agent_cfg in enumerate(team_config_input.agents, 1):
            try:
                self.logger.info(
                    "Creating agent %d/%d: %s.",
                    i,
                    len(team_config_input.agents),
                    agent_cfg.name,
                )
                agent = await self.create_agent_from_config(
                    user_id, agent_cfg, team_config_input, memory_store
                )
                initialized.append(agent)
                self._agent_list.append(agent)
                self.logger.info(
                    "Agent %d/%d ready: %s.",
                    i,
                    len(team_config_input.agents),
                    agent_cfg.name,
                )
            except (UnsupportedModelError, InvalidConfigurationError) as exc:
                self.logger.warning(
                    "Skipping agent %d/%d '%s' — configuration error: %s",
                    i,
                    len(team_config_input.agents),
                    agent_cfg.name,
                    exc,
                )
            except Exception as exc:
                self.logger.error(
                    "Skipping agent %d/%d '%s' — unexpected error: %s.",
                    i,
                    len(team_config_input.agents),
                    agent_cfg.name,
                    exc,
                )

        return initialized

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close_all(self) -> None:
        """Close all agents created by this factory instance."""
        await AgentFactory.cleanup_all_agents(self._agent_list)

    @staticmethod
    async def cleanup_all_agents(agent_list: list) -> None:
        """Close all agents in the given list and clear it.

        Mirrors the v4 MagenticAgentFactory.cleanup_all_agents static method.
        Safe to call with an empty list; errors are logged but do not propagate.
        """
        logger = logging.getLogger(__name__)
        for agent in list(agent_list):
            try:
                if hasattr(agent, "close"):
                    await agent.close()
            except Exception as exc:
                logger.warning(
                    "Error closing agent '%s': %s.",
                    getattr(agent, "agent_name", type(agent).__name__),
                    exc,
                )
        agent_list.clear()
