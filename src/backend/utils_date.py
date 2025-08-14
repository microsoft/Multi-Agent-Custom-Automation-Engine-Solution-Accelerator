import locale
from datetime import datetime
import logging
from typing import Optional


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
        locale.setlocale(locale.LC_TIME, user_locale or '')
        return date_obj.strftime("%B %d, %Y")
    except Exception as e:
        logging.warning(f"Date formatting failed for '{date_str}': {e}")
        return date_str
