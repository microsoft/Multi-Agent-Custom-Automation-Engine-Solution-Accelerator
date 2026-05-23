# Copyright (c) Microsoft. All rights reserved.
"""Factory for creating and managing agents from JSON team configurations.

Replaces v4/magentic_agents/magentic_agent_factory.py.
Key change: uses AgentTemplate (FoundryChatClient + Agent, GA) instead of
FoundryAgentTemplate (AzureAIAgentClient + ChatAgent, deprecated).
"""

import json
import logging
from types import SimpleNamespace
from typing import List, Optional

from agents.agent_template import AgentTemplate
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration
from config.mcp_config import (KnowledgeBaseConfig, MCPConfig, SearchConfig,
                               VectorStoreConfig)


class UnsupportedModelError(Exception):
    """Raised when the configured model is not in the supported-models list."""


# ---------------------------------------------------------------------------
# Universal prompt segment for agents whose team config has user_responses=true.
# Directs them to request clarification from the chat manager (who routes to
# UserInteractionAgent) rather than calling ask_user directly.
# ---------------------------------------------------------------------------

_UNIVERSAL_USER_INTERACTION_PROMPT = """

CRITICAL RULES — READ BEFORE ACTING:

1. NEVER FABRICATE INFORMATION. If a tool requires a parameter you do not have
   (dates, names, emails, hardware models, salary, preferences), you MUST request
   it from the user. Do NOT invent values, use placeholders, or guess.

2. GATHER ALL MISSING INFO BEFORE EXECUTING. Before calling action tools, check
   whether you have every required parameter. If ANY required parameter is missing
   from the conversation context, state clearly:
   "I need the following information from the user: [list]"
   The chat manager will route to UserInteractionAgent to collect answers.

3. PRESENT OPTIONS TO THE USER. If you have optional steps or overridable
   defaults, include them in your clarification request so the user can decide.

4. EXECUTE ONLY AFTER ANSWERS ARRIVE. Once user answers are in conversation
   history, proceed with execution using the real values provided.

5. REQUEST CLARIFICATION VIA THE MANAGER. Do NOT call ask_user yourself — only
   the UserInteractionAgent can communicate with the user. If mid-execution you
   discover a genuinely required value is still missing, state:
   "I need the following information from the user: [specific questions]"

6. Do NOT re-ask anything already answered in the conversation history.
"""


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
    ) -> AgentTemplate:
        """Create and open a single agent from a SimpleNamespace config object.

        Args:
            user_id:      The requesting user ID.
            agent_obj:    Per-agent config parsed from the team JSON.
            team_config:  The parent team configuration.
            memory_store: Cosmos DB store for agent persistence.

        Returns:
            An initialized ``AgentTemplate``.

        Raises:
            UnsupportedModelError:      If the deployment name is not in SUPPORTED_MODELS.
        """
        deployment_name = getattr(agent_obj, "deployment_name", None)

        # Validate model
        supported_models = json.loads(config.SUPPORTED_MODELS)
        if deployment_name not in supported_models:
            raise UnsupportedModelError(
                f"Model '{deployment_name}' is not supported. "
                f"Supported models: {supported_models}"
            )

        use_reasoning = self._extract_use_reasoning(agent_obj)

        # Build optional tool configs
        index_name = getattr(agent_obj, "index_name", None)
        search_config: Optional[SearchConfig] = (
            SearchConfig.from_env(index_name)
            if getattr(agent_obj, "use_rag", False)
            else None
        )

        # Foundry IQ (FileSearchTool + vector stores)
        vector_store_name = getattr(agent_obj, "vector_store_name", None)
        vector_store_config: Optional[VectorStoreConfig] = (
            VectorStoreConfig(vector_store_name=vector_store_name)
            if getattr(agent_obj, "use_file_search", False) and vector_store_name
            else None
        )

        # Foundry IQ Knowledge Base (server-side MCP on Azure AI Search)
        kb_name = getattr(agent_obj, "knowledge_base_name", None)
        kb_config: Optional[KnowledgeBaseConfig] = (
            KnowledgeBaseConfig.from_env(kb_name)
            if getattr(agent_obj, "use_knowledge_base", False) and kb_name
            else None
        )

        # MCP config: domain-specific server only (use_mcp).
        # user_responses=true no longer gives agents the ask_user tool directly;
        # they request clarification via their response text, and the manager
        # routes to UserInteractionAgent.
        use_mcp = getattr(agent_obj, "use_mcp", False)
        user_responses = getattr(agent_obj, "user_responses", False)
        if use_mcp:
            mcp_domain = getattr(agent_obj, "mcp_domain", None)
            # Fallback: derive domain from agent name if the team config didn't
            # supply one. Stops the agent from connecting to the base /mcp
            # endpoint and pulling in cross-pack tools like generate_press_release.
            if not mcp_domain:
                _NAME_TO_DOMAIN = {
                    "ImageContentAgent": "image",
                    "ImageGenerationAgent": "image",
                }
                mcp_domain = _NAME_TO_DOMAIN.get(agent_obj.name)
                if mcp_domain:
                    self.logger.warning(
                        "Agent '%s' has use_mcp=True but no mcp_domain in team config; "
                        "defaulting to domain='%s' based on agent name.",
                        agent_obj.name, mcp_domain,
                    )
            mcp_config: Optional[MCPConfig] = MCPConfig.from_env(domain=mcp_domain)
        else:
            mcp_config = None

        self.logger.info(
            "Creating AgentTemplate '%s' (model=%s, use_rag=%s, use_file_search=%s, use_mcp=%s, reasoning=%s).",
            agent_obj.name,
            deployment_name,
            search_config is not None,
            vector_store_config is not None,
            mcp_config is not None,
            use_reasoning,
        )

        # Build agent instructions from system_message + optional interaction rules
        instructions = getattr(agent_obj, "system_message", "")

        # Universal user-interaction rules for agents that have
        # user_responses=true — tells them to request clarification via the
        # chat manager rather than calling ask_user directly.
        if user_responses:
            instructions += _UNIVERSAL_USER_INTERACTION_PROMPT

        agent = AgentTemplate(
            agent_name=agent_obj.name,
            agent_description=getattr(agent_obj, "description", ""),
            agent_instructions=instructions,
            use_reasoning=use_reasoning,
            model_deployment_name=deployment_name,
            project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
            enable_code_interpreter=getattr(agent_obj, "coding_tools", False),
            mcp_config=mcp_config,
            search_config=search_config,
            vector_store_config=vector_store_config,
            kb_config=kb_config,
            temperature=getattr(agent_obj, "temperature", None),
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
            List of initialized ``AgentTemplate`` instances.
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
            except UnsupportedModelError as exc:
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
