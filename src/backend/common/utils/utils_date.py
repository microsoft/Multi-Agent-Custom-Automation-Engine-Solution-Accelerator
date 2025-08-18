import json
import locale
from datetime import datetime
import logging
from typing import Optional
from dateutil import parser


def format_date_for_user(date_str: str, user_locale: Optional[str] = None) -> str:
    """
    Format date based on user's desktop locale preference.

    Args:
        date_str (str): Date in ISO format (YYYY-MM-DD).
        user_locale (str, optional): User's locale string, e.g., 'en_US', 'en_GB'.

    Returns:
        str: Formatted date respecting locale or raw date if formatting fails.
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        locale.setlocale(locale.LC_TIME, user_locale or "")
        return date_obj.strftime("%B %d, %Y")
    except Exception as e:
        logging.warning(f"Date formatting failed for '{date_str}': {e}")
        return date_str


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def format_dates_in_messages(messages, target_locale="en-US"):
    """
    Format dates in agent messages according to the specified locale.

    Args:
        messages: List of message objects or string content
        target_locale: Target locale for date formatting (default: en-US)

    Returns:
        Formatted messages with dates converted to target locale format
    """
    # Define target format patterns per locale
    locale_date_formats = {
        "en-IN": "%d %b %Y",  # 30 Jul 2025
        "en-US": "%b %d, %Y",  # Jul 30, 2025
    }

    output_format = locale_date_formats.get(target_locale, "%d %b %Y")
    # Match both "Jul 30, 2025, 12:00:00 AM" and "30 Jul 2025"
    date_pattern = r"(\d{1,2} [A-Za-z]{3,9} \d{4}|[A-Za-z]{3,9} \d{1,2}, \d{4}(, \d{1,2}:\d{2}:\d{2} ?[APap][Mm])?)"

    def convert_date(match):
        date_str = match.group(0)
        try:
            dt = parser.parse(date_str)
            return dt.strftime(output_format)
        except Exception:
            return date_str  # Leave it unchanged if parsing fails

    # Process messages
    if isinstance(messages, list):
        formatted_messages = []
        for message in messages:
            if hasattr(message, "content") and message.content:
                # Create a copy of the message with formatted content
                formatted_message = (
                    message.model_copy() if hasattr(message, "model_copy") else message
                )
                if hasattr(formatted_message, "content"):
                    formatted_message.content = re.sub(
                        date_pattern, convert_date, formatted_message.content
                    )
                formatted_messages.append(formatted_message)
            else:
                formatted_messages.append(message)
        return formatted_messages
    elif isinstance(messages, str):
        return re.sub(date_pattern, convert_date, messages)
    else:
        return messages
