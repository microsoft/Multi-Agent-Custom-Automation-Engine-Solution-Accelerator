"""
Unit tests for utils_agents.py module.

This module tests the utility functions for agent ID generation.
"""

import string
import unittest
from unittest.mock import patch

from backend.common.utils.utils_agents import generate_assistant_id


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

    @patch('backend.common.utils.utils_agents.secrets.choice')
    def test_generate_assistant_id_uses_secrets(self, mock_choice):
        """Test that generate_assistant_id uses secrets module for randomness."""
        mock_choice.return_value = 'a'
        
        result = generate_assistant_id(length=5)
        
        self.assertEqual(result, "asst_aaaaa")
        self.assertEqual(mock_choice.call_count, 5)


if __name__ == "__main__":
    unittest.main()