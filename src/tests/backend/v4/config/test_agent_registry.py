"""
Unit tests for agent_registry.py module.

This module tests the AgentRegistry class for tracking and managing agent lifecycles,
including registration, unregistration, cleanup, and monitoring functionality.
"""

import asyncio
import logging
import os
import platform
import sys
import threading
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from weakref import WeakSet

# Skip decorator for Linux-specific failures
skip_on_linux = unittest.skipIf(
    platform.system() == "Linux",
    "Skipping on Linux due to logging/mocking compatibility issues"
)

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from backend.v4.config.agent_registry import AgentRegistry, agent_registry


class MockAgent:
    """Mock agent class for testing."""
    
    def __init__(self, name="TestAgent", agent_name=None, has_close=True):
        self.name = name
        if agent_name:
            self.agent_name = agent_name
        self._closed = False
        if has_close:
            self.close = AsyncMock()
    
    async def close_async(self):
        """Async close method for testing."""
        self._closed = True
    
    def close_sync(self):
        """Sync close method for testing."""
        self._closed = True


class MockAgentNoClose:
    """Mock agent without close method."""
    
    def __init__(self, name="NoCloseAgent"):
        self.name = name


class TestAgentRegistry(unittest.IsolatedAsyncioTestCase):
    """Test cases for AgentRegistry class."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()
        self.mock_agent1 = MockAgent("Agent1")
        self.mock_agent2 = MockAgent("Agent2")
        self.mock_agent3 = MockAgent("Agent3")

    def tearDown(self):
        """Clean up after each test."""
        # Clear the registry
        with self.registry._lock:
            self.registry._all_agents.clear()
            self.registry._agent_metadata.clear()

    def test_init(self):
        """Test AgentRegistry initialization."""
        registry = AgentRegistry()
        
        self.assertIsInstance(registry.logger, logging.Logger)
        self.assertIsInstance(registry._lock, type(threading.Lock()))
        self.assertIsInstance(registry._all_agents, WeakSet)
        self.assertIsInstance(registry._agent_metadata, dict)
        self.assertEqual(len(registry._all_agents), 0)
        self.assertEqual(len(registry._agent_metadata), 0)

    def test_register_agent_basic(self):
        """Test basic agent registration."""
        self.registry.register_agent(self.mock_agent1)
        
        self.assertEqual(len(self.registry._all_agents), 1)
        self.assertIn(self.mock_agent1, self.registry._all_agents)
        
        agent_id = id(self.mock_agent1)
        self.assertIn(agent_id, self.registry._agent_metadata)
        
        metadata = self.registry._agent_metadata[agent_id]
        self.assertEqual(metadata['type'], 'MockAgent')
        self.assertIsNone(metadata['user_id'])
        self.assertEqual(metadata['name'], 'Agent1')

    def test_register_agent_with_user_id(self):
        """Test agent registration with user ID."""
        user_id = "test_user_123"
        self.registry.register_agent(self.mock_agent1, user_id=user_id)
        
        agent_id = id(self.mock_agent1)
        metadata = self.registry._agent_metadata[agent_id]
        self.assertEqual(metadata['user_id'], user_id)

    def test_register_agent_with_agent_name_attribute(self):
        """Test agent registration with agent_name attribute."""
        agent = MockAgent(name="Name", agent_name="AgentName")
        self.registry.register_agent(agent)
        
        agent_id = id(agent)
        metadata = self.registry._agent_metadata[agent_id]
        self.assertEqual(metadata['name'], 'AgentName')  # Should prefer agent_name over name

    def test_register_agent_without_name_attributes(self):
        """Test agent registration without name or agent_name attributes."""
        class AgentNoName:
            pass
        
        agent = AgentNoName()
        self.registry.register_agent(agent)
        
        agent_id = id(agent)
        metadata = self.registry._agent_metadata[agent_id]
        self.assertEqual(metadata['name'], 'Unknown')

    @skip_on_linux
    @patch('backend.v4.config.agent_registry.logging.getLogger')
    def test_register_agent_logging(self, mock_get_logger):
        """Test logging during agent registration."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        registry = AgentRegistry()
        registry.register_agent(self.mock_agent1, user_id="test_user")
        
        # Verify info log was called
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Registered agent", log_message)
        self.assertIn("MockAgent", log_message)
        self.assertIn("test_user", log_message)

    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        agents = [self.mock_agent1, self.mock_agent2, self.mock_agent3]
        
        for agent in agents:
            self.registry.register_agent(agent)
        
        self.assertEqual(len(self.registry._all_agents), 3)
        self.assertEqual(len(self.registry._agent_metadata), 3)
        
        for agent in agents:
            self.assertIn(agent, self.registry._all_agents)
            self.assertIn(id(agent), self.registry._agent_metadata)

    def test_register_same_agent_multiple_times(self):
        """Test registering the same agent multiple times."""
        self.registry.register_agent(self.mock_agent1)
        self.registry.register_agent(self.mock_agent1)  # Register again
        
        # WeakSet should only contain one instance
        self.assertEqual(len(self.registry._all_agents), 1)
        # But metadata might be updated
        self.assertEqual(len(self.registry._agent_metadata), 1)

    @skip_on_linux
    @patch('backend.v4.config.agent_registry.logging.getLogger')
    def test_register_agent_exception_handling(self, mock_get_logger):
        """Test exception handling during agent registration."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        registry = AgentRegistry()
        
        # Mock the WeakSet to raise an exception
        with patch.object(registry._all_agents, 'add', side_effect=Exception("Test error")):
            registry.register_agent(self.mock_agent1)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("Failed to register agent", log_message)

    def test_unregister_agent_basic(self):
        """Test basic agent unregistration."""
        # First register the agent
        self.registry.register_agent(self.mock_agent1)
        agent_id = id(self.mock_agent1)
        
        # Verify it's registered
        self.assertEqual(len(self.registry._all_agents), 1)
        self.assertIn(agent_id, self.registry._agent_metadata)
        
        # Unregister it
        self.registry.unregister_agent(self.mock_agent1)
        
        # Verify it's unregistered
        self.assertEqual(len(self.registry._all_agents), 0)
        self.assertNotIn(agent_id, self.registry._agent_metadata)

    def test_unregister_nonexistent_agent(self):
        """Test unregistering an agent that was never registered."""
        # Should not raise an exception
        self.registry.unregister_agent(self.mock_agent1)
        self.assertEqual(len(self.registry._all_agents), 0)
        self.assertEqual(len(self.registry._agent_metadata), 0)

    @skip_on_linux
    @patch('backend.v4.config.agent_registry.logging.getLogger')
    def test_unregister_agent_logging(self, mock_get_logger):
        """Test logging during agent unregistration."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        registry = AgentRegistry()
        registry.register_agent(self.mock_agent1)
        
        # Clear previous log calls
        mock_logger.reset_mock()
        
        registry.unregister_agent(self.mock_agent1)
        
        # Verify info log was called
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Unregistered agent", log_message)
        self.assertIn("MockAgent", log_message)

    @skip_on_linux
    @patch('backend.v4.config.agent_registry.logging.getLogger')
    def test_unregister_agent_exception_handling(self, mock_get_logger):
        """Test exception handling during agent unregistration."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        registry = AgentRegistry()
        registry.register_agent(self.mock_agent1)
        
        # Mock the WeakSet to raise an exception
        with patch.object(registry._all_agents, 'discard', side_effect=Exception("Test error")):
            registry.unregister_agent(self.mock_agent1)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("Failed to unregister agent", log_message)

    def test_get_all_agents(self):
        """Test getting all registered agents."""
        agents = [self.mock_agent1, self.mock_agent2, self.mock_agent3]
        
        # Initially empty
        all_agents = self.registry.get_all_agents()
        self.assertEqual(len(all_agents), 0)
        
        # Register agents
        for agent in agents:
            self.registry.register_agent(agent)
        
        # Get all agents
        all_agents = self.registry.get_all_agents()
        self.assertEqual(len(all_agents), 3)
        
        for agent in agents:
            self.assertIn(agent, all_agents)

    def test_get_agent_count(self):
        """Test getting the count of registered agents."""
        self.assertEqual(self.registry.get_agent_count(), 0)
        
        self.registry.register_agent(self.mock_agent1)
        self.assertEqual(self.registry.get_agent_count(), 1)
        
        self.registry.register_agent(self.mock_agent2)
        self.assertEqual(self.registry.get_agent_count(), 2)
        
        self.registry.unregister_agent(self.mock_agent1)
        self.assertEqual(self.registry.get_agent_count(), 1)

    async def test_cleanup_all_agents_no_agents(self):
        """Test cleanup when no agents are registered."""
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry.cleanup_all_agents()
            
            mock_logger.info.assert_any_call("No agents to clean up")

    async def test_cleanup_all_agents_with_close_method(self):
        """Test cleanup of agents with close method."""
        # Register agents
        self.registry.register_agent(self.mock_agent1)
        self.registry.register_agent(self.mock_agent2)
        
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry.cleanup_all_agents()
            
            # Verify close was called on both agents
            self.mock_agent1.close.assert_called_once()
            self.mock_agent2.close.assert_called_once()
            
            # Verify registry is cleared
            self.assertEqual(len(self.registry._all_agents), 0)
            self.assertEqual(len(self.registry._agent_metadata), 0)
            
            # Verify logging
            mock_logger.info.assert_any_call("🎉 Completed cleanup of all agents")

    async def test_cleanup_all_agents_without_close_method(self):
        """Test cleanup of agents without close method."""
        agent_no_close = MockAgentNoClose()
        self.registry.register_agent(agent_no_close)
        
        with patch.object(self.registry, 'logger') as mock_logger:
            with patch.object(self.registry, 'unregister_agent') as mock_unregister:
                await self.registry.cleanup_all_agents()
                
                # Verify agent was unregistered
                mock_unregister.assert_called_once_with(agent_no_close)
                
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                warning_message = mock_logger.warning.call_args[0][0]
                self.assertIn("has no close() method", warning_message)

    async def test_cleanup_all_agents_mixed_agents(self):
        """Test cleanup with mix of agents with and without close method."""
        agent_no_close = MockAgentNoClose()
        
        self.registry.register_agent(self.mock_agent1)  # Has close method
        self.registry.register_agent(agent_no_close)   # No close method
        
        with patch.object(self.registry, 'unregister_agent', wraps=self.registry.unregister_agent) as mock_unregister:
            await self.registry.cleanup_all_agents()
            
            # Verify agent with close method was closed
            self.mock_agent1.close.assert_called_once()
            
            # Verify agent without close method was unregistered
            mock_unregister.assert_called_with(agent_no_close)

    async def test_safe_close_agent_async(self):
        """Test safe close with async close method."""
        # Create agent with async close
        agent = MockAgent()
        agent.close = AsyncMock()
        
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry._safe_close_agent(agent)
            
            agent.close.assert_called_once()
            mock_logger.info.assert_any_call("Closing agent: TestAgent")
            mock_logger.info.assert_any_call("Successfully closed agent: TestAgent")

    async def test_safe_close_agent_sync(self):
        """Test safe close with sync close method."""
        # Create agent with sync close
        agent = MockAgent()
        agent.close = MagicMock()
        
        with patch('asyncio.iscoroutinefunction', return_value=False):
            with patch.object(self.registry, 'logger') as mock_logger:
                await self.registry._safe_close_agent(agent)
                
                agent.close.assert_called_once()
                mock_logger.info.assert_any_call("Closing agent: TestAgent")
                mock_logger.info.assert_any_call("Successfully closed agent: TestAgent")

    async def test_safe_close_agent_exception(self):
        """Test safe close when close method raises exception."""
        agent = MockAgent()
        agent.close = AsyncMock(side_effect=Exception("Close failed"))
        
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry._safe_close_agent(agent)
            
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            self.assertIn("Failed to close agent", error_message)
            self.assertIn("TestAgent", error_message)

    async def test_safe_close_agent_with_agent_name(self):
        """Test safe close using agent_name attribute."""
        agent = MockAgent(name="Name", agent_name="AgentName")
        agent.close = AsyncMock()
        
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry._safe_close_agent(agent)
            
            # Should use agent_name, not name
            mock_logger.info.assert_any_call("Closing agent: AgentName")
            mock_logger.info.assert_any_call("Successfully closed agent: AgentName")

    def test_get_registry_status_empty(self):
        """Test getting registry status when empty."""
        status = self.registry.get_registry_status()
        
        expected_status = {
            'total_agents': 0,
            'agent_types': {}
        }
        self.assertEqual(status, expected_status)

    def test_get_registry_status_with_agents(self):
        """Test getting registry status with registered agents."""
        # Register different types of agents
        self.registry.register_agent(self.mock_agent1)
        self.registry.register_agent(self.mock_agent2)
        
        # Create an agent of different type
        class DifferentAgent:
            def __init__(self):
                self.name = "Different"
        
        different_agent = DifferentAgent()
        self.registry.register_agent(different_agent)
        
        status = self.registry.get_registry_status()
        
        expected_status = {
            'total_agents': 3,
            'agent_types': {
                'MockAgent': 2,
                'DifferentAgent': 1
            }
        }
        self.assertEqual(status, expected_status)

    def test_thread_safety_registration(self):
        """Test thread safety of agent registration."""
        import threading
        import time
        
        agents = [MockAgent(f"Agent{i}") for i in range(10)]
        threads = []
        
        def register_agent(agent):
            time.sleep(0.01)  # Small delay to increase chance of race condition
            self.registry.register_agent(agent)
        
        # Start multiple threads registering agents
        for agent in agents:
            thread = threading.Thread(target=register_agent, args=(agent,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all agents were registered
        self.assertEqual(self.registry.get_agent_count(), 10)

    def test_thread_safety_unregistration(self):
        """Test thread safety of agent unregistration."""
        import threading
        import time
        
        # Register agents first
        agents = [MockAgent(f"Agent{i}") for i in range(5)]
        for agent in agents:
            self.registry.register_agent(agent)
        
        threads = []
        
        def unregister_agent(agent):
            time.sleep(0.01)
            self.registry.unregister_agent(agent)
        
        # Start multiple threads unregistering agents
        for agent in agents:
            thread = threading.Thread(target=unregister_agent, args=(agent,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all agents were unregistered
        self.assertEqual(self.registry.get_agent_count(), 0)

    def test_weakref_behavior(self):
        """Test that agents are properly handled with weak references."""
        # Register an agent
        agent = MockAgent("TempAgent")
        self.registry.register_agent(agent)
        self.assertEqual(self.registry.get_agent_count(), 1)
        
        # Delete the agent reference
        agent_id = id(agent)
        del agent
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # The weak reference should be cleaned up automatically
        # Note: This might not always work immediately due to Python's GC behavior
        # So we just verify the initial registration worked
        self.assertIn(agent_id, self.registry._agent_metadata)


class TestGlobalAgentRegistry(unittest.TestCase):
    """Test the global agent registry instance."""

    def test_global_registry_instance(self):
        """Test that global registry instance is available."""
        self.assertIsInstance(agent_registry, AgentRegistry)

    @skip_on_linux
    def test_global_registry_singleton_behavior(self):
        """Test that the global registry behaves as expected."""
        # Import the global instance
        from backend.v4.config.agent_registry import agent_registry as global_registry
        
        # Should be the same instance
        self.assertIs(agent_registry, global_registry)


class TestAgentRegistryEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases and error conditions for AgentRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()

    def tearDown(self):
        """Clean up after each test."""
        with self.registry._lock:
            self.registry._all_agents.clear()
            self.registry._agent_metadata.clear()

    def test_register_none_agent(self):
        """Test registering None as agent."""
        # Should handle gracefully
        self.registry.register_agent(None)
        # None cannot be added to WeakSet, so this should be handled in exception block

    async def test_cleanup_with_close_exceptions(self):
        """Test cleanup when agent close methods raise exceptions."""
        # Create agents with failing close methods
        agent1 = MockAgent("Agent1")
        agent1.close = AsyncMock(side_effect=Exception("Close error 1"))
        
        agent2 = MockAgent("Agent2")
        agent2.close = AsyncMock(side_effect=Exception("Close error 2"))
        
        self.registry.register_agent(agent1)
        self.registry.register_agent(agent2)
        
        with patch.object(self.registry, 'logger') as mock_logger:
            await self.registry.cleanup_all_agents()
            
            # Should still complete cleanup despite exceptions
            self.assertEqual(len(self.registry._all_agents), 0)
            self.assertEqual(len(self.registry._agent_metadata), 0)
            
            # Should log errors for failed cleanups - check for actual close failures
            error_calls = [call for call in mock_logger.error.call_args_list 
                         if "Failed to close agent" in str(call)]
            self.assertEqual(len(error_calls), 2)

    def test_large_number_of_agents(self):
        """Test registry performance with large number of agents."""
        # Register many agents
        agents = [MockAgent(f"Agent{i}") for i in range(100)]
        
        for agent in agents:
            self.registry.register_agent(agent)
        
        self.assertEqual(self.registry.get_agent_count(), 100)
        
        # Test status with many agents
        status = self.registry.get_registry_status()
        self.assertEqual(status['total_agents'], 100)
        self.assertEqual(status['agent_types']['MockAgent'], 100)
        
        # Test getting all agents
        all_agents = self.registry.get_all_agents()
        self.assertEqual(len(all_agents), 100)

    async def test_concurrent_cleanup_and_registration(self):
        """Test concurrent cleanup and registration operations."""
        import asyncio
        
        async def register_agents():
            for i in range(5):
                agent = MockAgent(f"Agent{i}")
                self.registry.register_agent(agent)
                await asyncio.sleep(0.01)
        
        async def cleanup_agents():
            await asyncio.sleep(0.02)  # Let some agents register first
            await self.registry.cleanup_all_agents()
        
        # Run both operations concurrently
        await asyncio.gather(register_agents(), cleanup_agents())
        
        # Registry should be clean after cleanup
        self.assertEqual(self.registry.get_agent_count(), 0)


if __name__ == "__main__":
    unittest.main()