# Copyright (c) Microsoft. All rights reserved.
"""Global agent registry for tracking and managing agent lifecycles across the application."""

import asyncio
import logging
import threading
from typing import List, Dict, Any, Optional
from weakref import WeakSet


class AgentRegistry:
    """Global registry for tracking and managing all agent instances across the application."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._all_agents: WeakSet = WeakSet()
        self._agent_metadata: Dict[int, Dict[str, Any]] = {}

    def register_agent(self, agent: Any, user_id: Optional[str] = None) -> None:
        """Register an agent instance for tracking and lifecycle management."""
        with self._lock:
            try:
                self._all_agents.add(agent)
                agent_id = id(agent)
                self._agent_metadata[agent_id] = {
                    'type': type(agent).__name__,
                    'user_id': user_id,
                    'name': getattr(agent, 'agent_name', getattr(agent, 'name', 'Unknown'))
                }
                self.logger.info(f"Registered agent: {type(agent).__name__} (ID: {agent_id}, User: {user_id})")
            except Exception as e:
                self.logger.error(f"Failed to register agent: {e}")

    def unregister_agent(self, agent: Any) -> None:
        """Unregister an agent instance."""
        with self._lock:
            try:
                agent_id = id(agent)
                self._all_agents.discard(agent)
                if agent_id in self._agent_metadata:
                    metadata = self._agent_metadata.pop(agent_id)
                    self.logger.info(f"Unregistered agent: {metadata.get('type', 'Unknown')} (ID: {agent_id})")
            except Exception as e:
                self.logger.error(f"Failed to unregister agent: {e}")

    def get_all_agents(self) -> List[Any]:
        """Get all currently registered agents."""
        with self._lock:
            return list(self._all_agents)

    def get_agent_count(self) -> int:
        """Get the total number of registered agents."""
        with self._lock:
            return len(self._all_agents)

    async def cleanup_all_agents(self) -> None:
        """Clean up all registered agents across all users."""
        all_agents = self.get_all_agents()

        if not all_agents:
            self.logger.info("No agents to clean up")
            return

        self.logger.info(f"🧹 Starting cleanup of {len(all_agents)} total agents")

        # Log agent details for debugging
        for i, agent in enumerate(all_agents):
            agent_name = getattr(agent, 'agent_name', getattr(agent, 'name', type(agent).__name__))
            agent_type = type(agent).__name__
            has_close = hasattr(agent, 'close')
            self.logger.info(f"Agent {i + 1}: {agent_name} (Type: {agent_type}, Has close(): {has_close})")

        # Clean up agents concurrently
        cleanup_tasks = []
        for agent in all_agents:
            if hasattr(agent, 'close'):
                cleanup_tasks.append(self._safe_close_agent(agent))
            else:
                agent_name = getattr(agent, 'agent_name', getattr(agent, 'name', type(agent).__name__))
                self.logger.warning(f"⚠️ Agent {agent_name} has no close() method - just unregistering from registry")
                self.unregister_agent(agent)

        if cleanup_tasks:
            self.logger.info(f"🔄 Executing {len(cleanup_tasks)} cleanup tasks...")
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            # Log any exceptions that occurred during cleanup
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Error cleaning up agent {i}: {result}")
                else:
                    success_count += 1

            self.logger.info(f"✅ Successfully cleaned up {success_count}/{len(cleanup_tasks)} agents")

        # Clear all tracking
        with self._lock:
            self._all_agents.clear()
            self._agent_metadata.clear()

        self.logger.info("🎉 Completed cleanup of all agents")

    async def _safe_close_agent(self, agent: Any) -> None:
        """Safely close an agent with error handling."""
        try:
            agent_name = getattr(agent, 'agent_name', getattr(agent, 'name', type(agent).__name__))
            self.logger.info(f"Closing agent: {agent_name}")

            # Call the agent's close method - it should handle Azure deletion and registry cleanup
            if asyncio.iscoroutinefunction(agent.close):
                await agent.close()
            else:
                agent.close()

            self.logger.info(f"Successfully closed agent: {agent_name}")

        except Exception as e:
            agent_name = getattr(agent, 'agent_name', getattr(agent, 'name', type(agent).__name__))
            self.logger.error(f"Failed to close agent {agent_name}: {e}")

    def get_registry_status(self) -> Dict[str, Any]:
        """Get current status of the agent registry for debugging and monitoring."""
        with self._lock:
            status = {
                'total_agents': len(self._all_agents),
                'agent_types': {}
            }

            # Count agents by type
            for agent in self._all_agents:
                agent_type = type(agent).__name__
                status['agent_types'][agent_type] = status['agent_types'].get(agent_type, 0) + 1

            return status


# Global registry instance
agent_registry = AgentRegistry()
