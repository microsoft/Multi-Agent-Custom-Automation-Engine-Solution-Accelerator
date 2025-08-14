"""
Quick test for the fixed utils_date.py functionality
"""

import os
from datetime import datetime
from utils_date import format_date_for_user


def test_date_formatting():
    """Test the date formatting function with various inputs"""

    # Set up different language environments
    test_cases = [
        ('en-US', '2025-07-29', 'US English'),
        ('en-IN', '2025-07-29', 'Indian English'),
        ('en-GB', '2025-07-29', 'British English'),
        ('fr-FR', '2025-07-29', 'French'),
        ('de-DE', '2025-07-29', 'German'),
    ]

    print("Testing date formatting with different locales:")
    print("=" * 50)

    for locale, date_str, description in test_cases:
        os.environ['USER_LOCAL_BROWSER_LANGUAGE'] = locale
        try:
            result = format_date_for_user(date_str)
            print(f"{description} ({locale}): {result}")
        except Exception as e:
            print(f"{description} ({locale}): ERROR - {e}")

    print("\n" + "=" * 50)
    print("Testing with datetime object:")

    # Test with datetime object
    os.environ['USER_LOCAL_BROWSER_LANGUAGE'] = 'en-US'
    dt = datetime(2025, 7, 29, 14, 30, 0)
    result = format_date_for_user(dt)
    print(f"Datetime object: {result}")

    print("\nTesting error handling:")
    print("=" * 30)

    # Test error handling
    try:
        result = format_date_for_user('invalid-date-string')
        print(f"Invalid date: {result}")
    except Exception as e:
        print(f"Invalid date: ERROR - {e}")


if __name__ == "__main__":
    test_date_formatting()
