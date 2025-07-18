from datetime import datetime
import logging
from typing import Optional, Union
import locale

try:
    from babel.dates import format_date
    BABEL_AVAILABLE = True
except ImportError:
    print("[Warning] Babel is not installed. Falling back to system locale formatting.")
    BABEL_AVAILABLE = False


def format_date_for_user(date_input: Union[str, datetime], user_locale: Optional[str] = None) -> str:
    """
    Format date based on user's desktop locale preference using Babel or system locale.

    Args:
        date_input (str | datetime): Date in ISO format or datetime object.
        user_locale (str, optional): Locale string like 'en_US', 'en_GB'. Auto-detects if None.

    Returns:
        str: Locale-formatted date.
    """
    try:
        # If user_locale is None, auto-detect from system
        if user_locale is None:
            user_locale, _ = locale.getdefaultlocale()  # e.g., 'en_US'

        if isinstance(date_input, str):
            date_obj = datetime.strptime(date_input, "%Y-%m-%d")
        else:
            date_obj = date_input

        if BABEL_AVAILABLE:
            return format_date(date_obj, format="long", locale=user_locale)
        else:
            locale.setlocale(locale.LC_TIME, user_locale)
            try:
                return date_obj.strftime("%-d %B %Y")  # Linux/Mac
            except ValueError:
                return date_obj.strftime("%#d %B %Y")  # Windows fallback

    except Exception as e:
        logging.warning(f"Date formatting failed for '{date_input}': {e}")
        return str(date_input)
