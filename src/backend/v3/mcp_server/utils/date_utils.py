"""
Date and time utilities for MCP server.
"""

from datetime import datetime, timezone
from typing import Optional


def format_date_for_user(date_str: str) -> str:
    """
    Format a date string for user-friendly display.

    Args:
        date_str: Input date string in various formats

    Returns:
        Formatted date string
    """
    try:
        # Try to parse common date formats
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            # If parsing fails, return the original string
            return date_str

        # Format for user display
        return parsed_date.strftime("%B %d, %Y at %I:%M %p")

    except Exception:
        # If any error occurs, return the original string
        return date_str


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def format_timestamp_for_display(timestamp: Optional[str] = None) -> str:
    """
    Format timestamp for user display.

    Args:
        timestamp: ISO timestamp string, if None uses current time

    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        dt = datetime.now(timezone.utc)
    else:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp or "Unknown time"

    return dt.strftime("%B %d, %Y at %I:%M %p UTC")
