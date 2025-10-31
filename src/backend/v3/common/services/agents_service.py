"""
AgentsService (skeleton)

Lightweight service that receives a TeamService instance and exposes helper
methods to convert a TeamConfiguration into a list/array of agent descriptors.

This is intentionally a simple skeleton — the user will later provide the
implementation that wires these descriptors into Semantic Kernel / Foundry
agent instances.
"""

import logging
from typing import Any, Dict, List, Union

from common.models.messages_kernel import TeamAgent, TeamConfiguration
from v3.common.services.team_service import TeamService


class AgentsService:
    """Service for building agent descriptors from a team configuration.

    Responsibilities (skeleton):
    - Receive a TeamService instance on construction (can be used for validation
      or lookups when needed).
    - Expose a method that accepts a TeamConfiguration (or raw dict) and
      returns a list of agent descriptors. Descriptors are plain dicts that
      contain the fields required to later instantiate runtime agents.

    The concrete instantiation logic (semantic kernel / foundry) is intentionally
    left out and should be implemented by the user later (see
    `instantiate_agents` placeholder).
    """

    def __init__(self, team_service: TeamService):
        self.team_service = team_service
        self.logger = logging.getLogger(__name__)

    async def get_agents_from_team_config(
        self, team_config: Union[TeamConfiguration, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Return a list of lightweight agent descriptors derived from a
        TeamConfiguration or a raw dict.

        Each descriptor contains the basic fields from the team config and a
        placeholder where a future runtime/agent object can be attached.

        Args:
            team_config: TeamConfiguration model instance or a raw dict

        Returns:
            List[dict] -- each dict contains keys like:
                - input_key, type, name, system_message, description, icon,
                  index_name, agent_obj (placeholder)
        """
        if not team_config:
            return []

        # Accept either the pydantic TeamConfiguration or a raw dictionary
        if hasattr(team_config, "agents"):
            agents_raw = team_config.agents or []
        elif isinstance(team_config, dict):
            agents_raw = team_config.get("agents", [])
        else:
            # Unknown type; try to coerce to a list
            try:
                agents_raw = list(team_config)
            except Exception:
                agents_raw = []

        descriptors: List[Dict[str, Any]] = []
        for a in agents_raw:
            if isinstance(a, TeamAgent):
                desc = {
                    "input_key": a.input_key,
                    "type": a.type,
                    "name": a.name,
                    "system_message": getattr(a, "system_message", ""),
                    "description": getattr(a, "description", ""),
                    "icon": getattr(a, "icon", ""),
                    "index_name": getattr(a, "index_name", ""),
                    "use_rag": getattr(a, "use_rag", False),
                    "use_mcp": getattr(a, "use_mcp", False),
                    "coding_tools": getattr(a, "coding_tools", False),
                    # Placeholder for later wiring to a runtime/agent instance
                    "agent_obj": None,
                }
            elif isinstance(a, dict):
                desc = {
                    "input_key": a.get("input_key"),
                    "type": a.get("type"),
                    "name": a.get("name"),
                    "system_message": a.get("system_message") or a.get("instructions"),
                    "description": a.get("description"),
                    "icon": a.get("icon"),
                    "index_name": a.get("index_name"),
                    "use_rag": a.get("use_rag", False),
                    "use_mcp": a.get("use_mcp", False),
                    "coding_tools": a.get("coding_tools", False),
                    "agent_obj": None,
                }
            else:
                # Fallback: keep raw object for later introspection
                desc = {"raw": a, "agent_obj": None}

            descriptors.append(desc)

        return descriptors

    async def instantiate_agents(self, agent_descriptors: List[Dict[str, Any]]):
        """Placeholder for instantiating runtime agent objects from descriptors.

        The real implementation should create Semantic Kernel / Foundry agents
        and attach them to each descriptor under the key `agent_obj` or return a
        list of instantiated agents.

        Raises:
            NotImplementedError -- this is only a skeleton.
        """
        raise NotImplementedError(
            "Agent instantiation is not implemented in the skeleton"
        )
