"""
Tests for utility functions.
"""

import pytest
from datetime import datetime
from src.mcp_server.utils.date_utils import (
    format_date_for_user,
    get_current_timestamp,
    format_timestamp_for_display,
)
from src.mcp_server.utils.formatters import (
    format_mcp_response,
    format_error_response,
    format_success_response,
)


class TestDateUtils:
    """Test cases for date utilities."""

    def test_format_date_for_user_standard_formats(self):
        """Test date formatting with standard formats."""
        # Test YYYY-MM-DD format
        result = format_date_for_user("2024-12-25")
        assert "December 25, 2024" in result

        # Test MM/DD/YYYY format
        result = format_date_for_user("12/25/2024")
        assert "December 25, 2024" in result

        # Test invalid format returns original
        result = format_date_for_user("invalid-date")
        assert result == "invalid-date"

    def test_get_current_timestamp(self):
        """Test current timestamp generation."""
        timestamp = get_current_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format should contain T

        # Should be able to parse it back
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_format_timestamp_for_display(self):
        """Test timestamp formatting for display."""
        # Test with None (current time)
        result = format_timestamp_for_display()
        assert "UTC" in result

        # Test with specific timestamp
        test_timestamp = "2024-12-25T10:30:00Z"
        result = format_timestamp_for_display(test_timestamp)
        assert "December 25, 2024" in result
        assert "10:30" in result
        assert "UTC" in result

        # Test with invalid timestamp
        result = format_timestamp_for_display("invalid")
        assert result == "invalid"


class TestFormatters:
    """Test cases for response formatters."""

    def test_format_mcp_response(self):
        """Test MCP response formatting."""
        title = "Test Action"
        content = {"user": "John", "status": "success"}
        summary = "Test completed successfully"

        result = format_mcp_response(title, content, summary)

        assert "##### Test Action" in result
        assert "**User:** John" in result
        assert "**Status:** success" in result
        assert "AGENT SUMMARY: Test completed successfully" in result
        assert "Instructions:" in result

    def test_format_error_response(self):
        """Test error response formatting."""
        error_msg = "Something went wrong"
        context = "testing error handling"

        result = format_error_response(error_msg, context)

        assert "##### ❌ Error" in result
        assert "**Context:** testing error handling" in result
        assert "**Error:** Something went wrong" in result
        assert "AGENT SUMMARY: An error occurred" in result

    def test_format_error_response_no_context(self):
        """Test error response formatting without context."""
        error_msg = "Something went wrong"

        result = format_error_response(error_msg)

        assert "##### ❌ Error" in result
        assert "**Error:** Something went wrong" in result
        assert "**Context:**" not in result
        assert "AGENT SUMMARY: An error occurred" in result

    def test_format_success_response(self):
        """Test success response formatting."""
        action = "User Creation"
        details = {"user": "John", "email": "john@example.com"}
        summary = "User created successfully"

        result = format_success_response(action, details, summary)

        assert "##### User Creation Completed" in result
        assert "**User:** John" in result
        assert "**Email:** john@example.com" in result
        assert "AGENT SUMMARY: User created successfully" in result

    def test_format_success_response_auto_summary(self):
        """Test success response with auto-generated summary."""
        action = "User Creation"
        details = {"user": "John"}

        result = format_success_response(action, details)

        assert "##### User Creation Completed" in result
        assert "AGENT SUMMARY: Successfully completed user creation" in result
