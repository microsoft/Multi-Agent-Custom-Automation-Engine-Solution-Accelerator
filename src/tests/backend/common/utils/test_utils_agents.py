"""
Unit tests for utils_agents.py module.

This module tests the utility functions for agent ID generation and database operations.
"""

import logging
import string
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.database.database_base import DatabaseBase
from common.models.messages_af import CurrentTeamAgent, DataType, TeamConfiguration
from common.utils.utils_agents import (
    generate_assistant_id,
    get_database_team_agent_id,
)


class TestGenerateAssistantId(unittest.TestCase):
    """Test cases for generate_assistant_id function."""

    def test_generate_assistant_id_default_parameters(self):
        """Test generate_assistant_id with default parameters."""
        result = generate_assistant_id()
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("asst_"))
        self.assertEqual(len(result), 29)  # "asst_" (5) + 24 characters
        
        # Verify the random part contains only valid characters
        random_part = result[5:]  # Remove "asst_" prefix
        valid_chars = string.ascii_letters + string.digits
        self.assertTrue(all(char in valid_chars for char in random_part))

    def test_generate_assistant_id_custom_prefix(self):
        """Test generate_assistant_id with custom prefix."""
        custom_prefix = "agent_"
        result = generate_assistant_id(prefix=custom_prefix)
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith(custom_prefix))
        self.assertEqual(len(result), len(custom_prefix) + 24)

    def test_generate_assistant_id_custom_length(self):
        """Test generate_assistant_id with custom length."""
        custom_length = 32
        result = generate_assistant_id(length=custom_length)
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("asst_"))
        self.assertEqual(len(result), 5 + custom_length)

    def test_generate_assistant_id_custom_prefix_and_length(self):
        """Test generate_assistant_id with both custom prefix and length."""
        custom_prefix = "test_"
        custom_length = 16
        result = generate_assistant_id(prefix=custom_prefix, length=custom_length)
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith(custom_prefix))
        self.assertEqual(len(result), len(custom_prefix) + custom_length)

    def test_generate_assistant_id_empty_prefix(self):
        """Test generate_assistant_id with empty prefix."""
        result = generate_assistant_id(prefix="", length=10)
        
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 10)
        # Should contain only valid characters
        valid_chars = string.ascii_letters + string.digits
        self.assertTrue(all(char in valid_chars for char in result))

    def test_generate_assistant_id_zero_length(self):
        """Test generate_assistant_id with zero length."""
        result = generate_assistant_id(length=0)
        
        self.assertIsInstance(result, str)
        self.assertEqual(result, "asst_")

    def test_generate_assistant_id_uniqueness(self):
        """Test that generate_assistant_id produces unique results."""
        results = [generate_assistant_id() for _ in range(100)]
        
        # All results should be unique
        self.assertEqual(len(results), len(set(results)))

    def test_generate_assistant_id_character_set(self):
        """Test that generated ID uses only allowed characters."""
        result = generate_assistant_id()
        random_part = result[5:]  # Remove prefix
        
        # Should only contain a-z, A-Z, 0-9
        valid_chars = set(string.ascii_letters + string.digits)
        result_chars = set(random_part)
        
        self.assertTrue(result_chars.issubset(valid_chars))

    @patch('common.utils.utils_agents.secrets.choice')
    def test_generate_assistant_id_uses_secrets(self, mock_choice):
        """Test that generate_assistant_id uses secrets module for randomness."""
        mock_choice.return_value = 'a'
        
        result = generate_assistant_id(length=5)
        
        self.assertEqual(result, "asst_aaaaa")
        self.assertEqual(mock_choice.call_count, 5)


class TestGetDatabaseTeamAgentId(unittest.IsolatedAsyncioTestCase):
    """Test cases for get_database_team_agent_id function."""

    async def test_get_database_team_agent_id_success(self):
        """Test successful retrieval of team agent ID."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_agent = MagicMock(spec=CurrentTeamAgent)
        mock_agent.agent_foundry_id = "asst_test123456789"
        mock_memory_store.get_team_agent.return_value = mock_agent
        
        team_config = TeamConfiguration(
            team_id="team_123",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "test_agent"
        
        # Execute
        result = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name=agent_name
        )
        
        # Verify
        self.assertEqual(result, "asst_test123456789")
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team_123", agent_name="test_agent"
        )

    async def test_get_database_team_agent_id_no_agent_found(self):
        """Test when no agent is found in database."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_memory_store.get_team_agent.return_value = None
        
        team_config = TeamConfiguration(
            team_id="team_123",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "nonexistent_agent"
        
        # Execute
        result = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name=agent_name
        )
        
        # Verify
        self.assertIsNone(result)
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team_123", agent_name="nonexistent_agent"
        )

    async def test_get_database_team_agent_id_agent_without_foundry_id(self):
        """Test when agent is found but has no foundry ID."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_agent = MagicMock(spec=CurrentTeamAgent)
        mock_agent.agent_foundry_id = None
        mock_memory_store.get_team_agent.return_value = mock_agent
        
        team_config = TeamConfiguration(
            team_id="team_123",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "agent_no_foundry_id"
        
        # Execute
        result = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name=agent_name
        )
        
        # Verify
        self.assertIsNone(result)
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team_123", agent_name="agent_no_foundry_id"
        )

    async def test_get_database_team_agent_id_agent_with_empty_foundry_id(self):
        """Test when agent is found but has empty foundry ID."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_agent = MagicMock(spec=CurrentTeamAgent)
        mock_agent.agent_foundry_id = ""
        mock_memory_store.get_team_agent.return_value = mock_agent
        
        team_config = TeamConfiguration(
            team_id="team_123",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "agent_empty_foundry_id"
        
        # Execute
        result = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name=agent_name
        )
        
        # Verify
        self.assertIsNone(result)
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team_123", agent_name="agent_empty_foundry_id"
        )

    async def test_get_database_team_agent_id_database_exception(self):
        """Test exception handling during database operation."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_memory_store.get_team_agent.side_effect = Exception("Database connection failed")
        
        team_config = TeamConfiguration(
            team_id="team_123",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "test_agent"
        
        # Execute with logging capture
        with patch('common.utils.utils_agents.logging.error') as mock_logging:
            result = await get_database_team_agent_id(
                memory_store=mock_memory_store,
                team_config=team_config,
                agent_name=agent_name
            )
        
        # Verify
        self.assertIsNone(result)
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team_123", agent_name="test_agent"
        )
        mock_logging.assert_called_once()
        # Check that the error message contains expected text
        args, kwargs = mock_logging.call_args
        self.assertIn("Failed to initialize Get database team agent", args[0])
        self.assertIn("Database connection failed", str(args[1]))

    async def test_get_database_team_agent_id_specific_exceptions(self):
        """Test handling of various specific exceptions."""
        exceptions_to_test = [
            ValueError("Invalid team ID"),
            KeyError("Missing key"),
            ConnectionError("Network error"),
            RuntimeError("Runtime issue"),
            AttributeError("Missing attribute")
        ]
        
        for exception in exceptions_to_test:
            with self.subTest(exception=type(exception).__name__):
                # Setup
                mock_memory_store = AsyncMock(spec=DatabaseBase)
                mock_memory_store.get_team_agent.side_effect = exception
                
                team_config = TeamConfiguration(
                    team_id="team_123",
                    session_id="session_456",
                    name="Test Team",
                    status="active",
                    created="2023-01-01",
                    created_by="user_123",
                    deployment_name="test_deployment",
                    user_id="user_123"
                )
                agent_name = "test_agent"
                
                # Execute with logging capture
                with patch('common.utils.utils_agents.logging.error') as mock_logging:
                    result = await get_database_team_agent_id(
                        memory_store=mock_memory_store,
                        team_config=team_config,
                        agent_name=agent_name
                    )
                
                # Verify
                self.assertIsNone(result)
                mock_logging.assert_called_once()

    async def test_get_database_team_agent_id_valid_foundry_id_formats(self):
        """Test with various valid foundry ID formats."""
        foundry_ids_to_test = [
            "asst_1234567890abcdef1234",
            "agent_xyz789",
            "foundry_test_agent_123",
            "a",  # single character
            "very_long_agent_id_with_many_characters_12345"
        ]
        
        for foundry_id in foundry_ids_to_test:
            with self.subTest(foundry_id=foundry_id):
                # Setup
                mock_memory_store = AsyncMock(spec=DatabaseBase)
                mock_agent = MagicMock(spec=CurrentTeamAgent)
                mock_agent.agent_foundry_id = foundry_id
                mock_memory_store.get_team_agent.return_value = mock_agent
                
                team_config = TeamConfiguration(
                    team_id="team_123",
                    session_id="session_456",
                    name="Test Team",
                    status="active",
                    created="2023-01-01",
                    created_by="user_123",
                    deployment_name="test_deployment",
                    user_id="user_123"
                )
                agent_name = "test_agent"
                
                # Execute
                result = await get_database_team_agent_id(
                    memory_store=mock_memory_store,
                    team_config=team_config,
                    agent_name=agent_name
                )
                
                # Verify
                self.assertEqual(result, foundry_id)

    async def test_get_database_team_agent_id_with_special_characters_in_ids(self):
        """Test with special characters in team_id and agent_name."""
        # Setup
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_agent = MagicMock(spec=CurrentTeamAgent)
        mock_agent.agent_foundry_id = "asst_special123"
        mock_memory_store.get_team_agent.return_value = mock_agent
        
        team_config = TeamConfiguration(
            team_id="team-123_special@domain.com",
            session_id="session_456",
            name="Test Team",
            status="active",
            created="2023-01-01",
            created_by="user_123",
            deployment_name="test_deployment",
            user_id="user_123"
        )
        agent_name = "agent-with-hyphens_and_underscores.test"
        
        # Execute
        result = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name=agent_name
        )
        
        # Verify
        self.assertEqual(result, "asst_special123")
        mock_memory_store.get_team_agent.assert_called_once_with(
            team_id="team-123_special@domain.com",
            agent_name="agent-with-hyphens_and_underscores.test"
        )


class TestUtilsAgentsIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for utils_agents module."""

    async def test_generate_and_store_workflow(self):
        """Test a typical workflow of generating ID and storing agent."""
        # Generate a new assistant ID
        new_id = generate_assistant_id()
        self.assertIsInstance(new_id, str)
        self.assertTrue(new_id.startswith("asst_"))
        
        # Setup mock database with the generated ID
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        mock_agent = MagicMock(spec=CurrentTeamAgent)
        mock_agent.agent_foundry_id = new_id
        mock_memory_store.get_team_agent.return_value = mock_agent
        
        team_config = TeamConfiguration(
            team_id="integration_team",
            session_id="integration_session",
            name="Integration Test Team",
            status="active",
            created="2023-01-01",
            created_by="integration_user",
            deployment_name="integration_deployment",
            user_id="integration_user"
        )
        
        # Retrieve the stored agent ID
        retrieved_id = await get_database_team_agent_id(
            memory_store=mock_memory_store,
            team_config=team_config,
            agent_name="integration_agent"
        )
        
        # Verify the workflow
        self.assertEqual(retrieved_id, new_id)

    async def test_multiple_agents_different_ids(self):
        """Test that different agents can have different IDs."""
        # Generate multiple IDs
        id1 = generate_assistant_id()
        id2 = generate_assistant_id()
        id3 = generate_assistant_id()
        
        # Ensure they're all different
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)
        
        # Setup database mock for multiple agents
        mock_memory_store = AsyncMock(spec=DatabaseBase)
        
        def mock_get_team_agent(team_id, agent_name):
            agent_ids = {
                "agent1": id1,
                "agent2": id2,
                "agent3": id3
            }
            if agent_name in agent_ids:
                mock_agent = MagicMock(spec=CurrentTeamAgent)
                mock_agent.agent_foundry_id = agent_ids[agent_name]
                return mock_agent
            return None
        
        mock_memory_store.get_team_agent.side_effect = mock_get_team_agent
        
        team_config = TeamConfiguration(
            team_id="multi_agent_team",
            session_id="multi_agent_session",
            name="Multi Agent Test Team",
            status="active",
            created="2023-01-01",
            created_by="test_user",
            deployment_name="test_deployment",
            user_id="test_user"
        )
        
        # Test retrieval of different agent IDs
        retrieved_id1 = await get_database_team_agent_id(
            mock_memory_store, team_config, "agent1"
        )
        retrieved_id2 = await get_database_team_agent_id(
            mock_memory_store, team_config, "agent2"
        )
        retrieved_id3 = await get_database_team_agent_id(
            mock_memory_store, team_config, "agent3"
        )
        
        # Verify each agent has its correct ID
        self.assertEqual(retrieved_id1, id1)
        self.assertEqual(retrieved_id2, id2)
        self.assertEqual(retrieved_id3, id3)


if __name__ == "__main__":
    unittest.main()