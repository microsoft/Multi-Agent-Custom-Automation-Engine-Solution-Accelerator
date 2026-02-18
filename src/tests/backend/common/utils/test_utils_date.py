"""
Unit tests for utils_date.py module.

This module tests the date formatting utilities, JSON encoding for datetime objects,
and message date formatting functionality.
"""

import json
import locale
import unittest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

# Set required environment variables for testing
os.environ.setdefault('APPLICATIONINSIGHTS_CONNECTION_STRING', 'test_connection_string')
os.environ.setdefault('APP_ENV', 'dev')

# Only mock external problematic dependencies - do NOT mock internal common.* modules
sys.modules['dateutil'] = Mock()
sys.modules['dateutil.parser'] = Mock()
sys.modules['regex'] = Mock()

# Only mock external problematic dependencies - do NOT mock internal common.* modules
# Mock the external dependencies but not in a way that breaks real function
sys.modules['dateutil'] = Mock()
sys.modules['dateutil.parser'] = Mock()
sys.modules['regex'] = Mock()

# Import the REAL modules using backend.* paths for proper coverage tracking
from backend.common.utils.utils_date import (
    DateTimeEncoder,
    format_date_for_user,
    format_dates_in_messages,
)

# Now patch the parser in the actual module to work correctly
import backend.common.utils.utils_date as utils_date_module

# Create proper mock for dateutil.parser that returns real datetime objects
parser_mock = Mock()
def mock_parse(date_str):
    from datetime import datetime
    import re
    
    # US format: Jul 30, 2025 or Dec 25, 2023 or December 25, 2023
    us_pattern = r'([A-Za-z]{3,9}) (\d{1,2}), (\d{4})'
    us_match = re.match(us_pattern, date_str.strip())
    if us_match:
        month_name, day, year = us_match.groups()
        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        if month_name in month_map:
            return datetime(int(year), month_map[month_name], int(day))
    
    # Indian format: 30 Jul 2025 or 25 Dec 2023 or 25 December 2023
    indian_pattern = r'(\d{1,2}) ([A-Za-z]{3,9}) (\d{4})'
    indian_match = re.match(indian_pattern, date_str.strip())
    if indian_match:
        day, month_name, year = indian_match.groups()
        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        if month_name in month_map:
            return datetime(int(year), month_map[month_name], int(day))
    
    raise ValueError(f"Unable to parse date: {date_str}")

parser_mock.parse = mock_parse

# Patch the parser in the actual utils_date module
utils_date_module.parser = parser_mock

# Also patch the regex module to use real regex
import re as real_re
utils_date_module.re = real_re


class TestFormatDateForUser(unittest.TestCase):
    """Test cases for format_date_for_user function."""

    def setUp(self):
        """Set up test fixtures."""
        # Save original locale to restore later
        try:
            self.original_locale = locale.getlocale(locale.LC_TIME)
        except Exception:
            self.original_locale = None

    def tearDown(self):
        """Restore original locale after each test."""
        try:
            if self.original_locale:
                locale.setlocale(locale.LC_TIME, self.original_locale)
            else:
                locale.setlocale(locale.LC_TIME, "")
        except Exception:
            pass

    def test_format_date_for_user_valid_iso_date(self):
        """Test format_date_for_user with valid ISO date format."""
        result = format_date_for_user("2023-12-25")
        # Should return formatted date like "December 25, 2023"
        self.assertIn("25", result)
        self.assertIn("2023", result)
        # Check that it's not the original ISO format
        self.assertNotEqual(result, "2023-12-25")

    def test_format_date_for_user_invalid_date_format(self):
        """Test format_date_for_user with invalid date format."""
        invalid_date = "25-12-2023"  # Wrong format
        result = format_date_for_user(invalid_date)
        # Should return original string when formatting fails
        self.assertEqual(result, invalid_date)

    def test_format_date_for_user_empty_string(self):
        """Test format_date_for_user with empty string."""
        result = format_date_for_user("")
        self.assertEqual(result, "")

    def test_format_date_for_user_invalid_date_values(self):
        """Test format_date_for_user with invalid date values."""
        invalid_dates = [
            "2023-13-01",  # Invalid month
            "2023-12-32",  # Invalid day
            "2023-02-30",  # Invalid day for February
            "not-a-date",  # Not a date at all
            "2023-00-01",  # Zero month
            "0000-12-01",  # Zero year
        ]
        
        for invalid_date in invalid_dates:
            with self.subTest(date=invalid_date):
                result = format_date_for_user(invalid_date)
                self.assertEqual(result, invalid_date)

    @patch('backend.common.utils.utils_date.locale.setlocale')
    def test_format_date_for_user_with_user_locale(self, mock_setlocale):
        """Test format_date_for_user with specific user locale."""
        # Mock locale setting to avoid system dependency
        mock_setlocale.return_value = None
        
        result = format_date_for_user("2023-12-25", "en_US")
        
        # Verify setlocale was called with the provided locale
        mock_setlocale.assert_called_with(locale.LC_TIME, "en_US")
        # Should still format the date
        self.assertNotEqual(result, "2023-12-25")

    @patch('backend.common.utils.utils_date.locale.setlocale')
    def test_format_date_for_user_locale_setting_fails(self, mock_setlocale):
        """Test format_date_for_user when locale setting fails."""
        # Make setlocale raise an exception
        mock_setlocale.side_effect = locale.Error("Unsupported locale")
        
        with patch('backend.common.utils.utils_date.logging.warning') as mock_warning:
            result = format_date_for_user("2023-12-25", "invalid_locale")
            
            # Should return original date when locale fails
            self.assertEqual(result, "2023-12-25")
            mock_warning.assert_called_once()

    def test_format_date_for_user_strptime_exception(self):
        """Test format_date_for_user when strptime raises exception."""
        # Test with invalid date format that will cause strptime to fail
        invalid_date = "invalid-date-format"
        
        with patch('backend.common.utils.utils_date.logging.warning') as mock_warning:
            result = format_date_for_user(invalid_date)
            
            self.assertEqual(result, invalid_date)
            mock_warning.assert_called_once()

    def test_format_date_for_user_none_locale(self):
        """Test format_date_for_user with None locale."""
        result = format_date_for_user("2023-12-25", None)
        # Should work with default locale
        self.assertNotEqual(result, "2023-12-25")

    @patch('backend.common.utils.utils_date.logging.warning')
    def test_format_date_for_user_logging_on_error(self, mock_warning):
        """Test that logging.warning is called on formatting errors."""
        invalid_date = "invalid-date-string"
        result = format_date_for_user(invalid_date)
        
        # Should log warning and return original string
        self.assertEqual(result, invalid_date)
        mock_warning.assert_called_once()
        # Check that the warning message contains expected content
        args, kwargs = mock_warning.call_args
        self.assertIn("Date formatting failed", args[0])
        self.assertIn(invalid_date, args[0])

    def test_format_date_for_user_leap_year(self):
        """Test format_date_for_user with leap year date."""
        leap_year_date = "2024-02-29"
        result = format_date_for_user(leap_year_date)
        
        # Should handle leap year correctly
        self.assertIn("29", result)
        self.assertIn("2024", result)
        self.assertNotEqual(result, leap_year_date)

    def test_format_date_for_user_various_valid_dates(self):
        """Test format_date_for_user with various valid dates."""
        test_dates = [
            "2023-01-01",  # New Year
            "2023-07-04",  # Mid year
            "2023-12-31",  # End of year
            "2000-01-01",  # Y2K
            "2024-02-29",  # Leap year
        ]
        
        for test_date in test_dates:
            with self.subTest(date=test_date):
                result = format_date_for_user(test_date)
                self.assertIsInstance(result, str)
                self.assertNotEqual(result, test_date)


class TestDateTimeEncoder(unittest.TestCase):
    """Test cases for DateTimeEncoder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = DateTimeEncoder()

    def test_datetime_encoder_datetime_object(self):
        """Test DateTimeEncoder with datetime object."""
        test_datetime = datetime(2023, 12, 25, 10, 30, 45)
        result = self.encoder.default(test_datetime)
        
        # Should return ISO format string
        self.assertEqual(result, "2023-12-25T10:30:45")

    def test_datetime_encoder_datetime_with_microseconds(self):
        """Test DateTimeEncoder with datetime including microseconds."""
        test_datetime = datetime(2023, 12, 25, 10, 30, 45, 123456)
        result = self.encoder.default(test_datetime)
        
        # Should include microseconds in ISO format
        self.assertEqual(result, "2023-12-25T10:30:45.123456")

    def test_datetime_encoder_non_datetime_object(self):
        """Test DateTimeEncoder with non-datetime object."""
        test_objects = [
            "string",
            123,
            ["list"],
            {"dict": "value"},
            None,
            True,
        ]
        
        for test_obj in test_objects:
            with self.subTest(obj=test_obj):
                with self.assertRaises((TypeError, AttributeError)):
                    # Should raise exception for non-datetime objects
                    # since super().default() will be called
                    self.encoder.default(test_obj)

    def test_datetime_encoder_json_dumps_integration(self):
        """Test DateTimeEncoder integration with json.dumps."""
        test_data = {
            "timestamp": datetime(2023, 12, 25, 10, 30, 45),
            "name": "test",
            "count": 42
        }
        
        result = json.dumps(test_data, cls=DateTimeEncoder)
        expected = '{"timestamp": "2023-12-25T10:30:45", "name": "test", "count": 42}'
        
        # Parse both to compare (order might vary)
        result_parsed = json.loads(result)
        expected_parsed = json.loads(expected)
        
        self.assertEqual(result_parsed, expected_parsed)

    def test_datetime_encoder_multiple_datetimes(self):
        """Test DateTimeEncoder with multiple datetime objects."""
        test_data = {
            "created": datetime(2023, 1, 1, 0, 0, 0),
            "updated": datetime(2023, 12, 31, 23, 59, 59),
            "events": [
                {"time": datetime(2023, 6, 15, 12, 0, 0), "type": "start"},
                {"time": datetime(2023, 6, 15, 18, 0, 0), "type": "end"}
            ]
        }
        
        result_str = json.dumps(test_data, cls=DateTimeEncoder)
        result_parsed = json.loads(result_str)
        
        # Verify all datetime objects were converted
        self.assertEqual(result_parsed["created"], "2023-01-01T00:00:00")
        self.assertEqual(result_parsed["updated"], "2023-12-31T23:59:59")
        self.assertEqual(result_parsed["events"][0]["time"], "2023-06-15T12:00:00")
        self.assertEqual(result_parsed["events"][1]["time"], "2023-06-15T18:00:00")

    def test_datetime_encoder_timezone_aware_datetime(self):
        """Test DateTimeEncoder with timezone-aware datetime."""
        from datetime import timezone
        
        # Create timezone-aware datetime
        test_datetime = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)
        result = self.encoder.default(test_datetime)
        
        # Should include timezone info in ISO format
        self.assertEqual(result, "2023-12-25T10:30:45+00:00")


class TestFormatDatesInMessages(unittest.TestCase):
    """Test cases for format_dates_in_messages function."""

    def test_format_dates_in_messages_string_input(self):
        """Test format_dates_in_messages with string input."""
        test_string = "The event is on Jul 30, 2025 at the venue."
        result = format_dates_in_messages(test_string, "en-IN")
        
        # Should convert to Indian format (DD MMM YYYY)
        self.assertIn("30 Jul 2025", result)
        self.assertNotIn("Jul 30, 2025", result)

    def test_format_dates_in_messages_us_to_indian_format(self):
        """Test format_dates_in_messages converting US to Indian format."""
        test_string = "Meeting on Dec 25, 2023 and Jan 1, 2024"
        result = format_dates_in_messages(test_string, "en-IN")
        
        self.assertIn("25 Dec 2023", result)
        self.assertIn("1 Jan 2024", result)
        self.assertNotIn("Dec 25, 2023", result)
        self.assertNotIn("Jan 1, 2024", result)

    def test_format_dates_in_messages_indian_to_us_format(self):
        """Test format_dates_in_messages converting Indian to US format."""
        test_string = "Event on 25 Dec 2023 and 1 Jan 2024"
        result = format_dates_in_messages(test_string, "en-US")
        
        self.assertIn("Dec 25, 2023", result)
        # Check for either "Jan 1, 2024" or "Jan 01, 2024" (zero-padded)
        self.assertTrue("Jan 1, 2024" in result or "Jan 01, 2024" in result)
        self.assertNotIn("25 Dec 2023", result)
        self.assertNotIn("1 Jan 2024", result if "Jan 01, 2024" in result else "dummy")

    def test_format_dates_in_messages_with_time(self):
        """Test format_dates_in_messages with dates that include time."""
        test_string = "Meeting on Jul 30, 2025, 12:00:00 AM"
        result = format_dates_in_messages(test_string, "en-IN")
        
        self.assertIn("30 Jul 2025", result)

    def test_format_dates_in_messages_no_dates(self):
        """Test format_dates_in_messages with text containing no dates."""
        test_string = "This is a simple message without any dates."
        result = format_dates_in_messages(test_string, "en-US")
        
        # Should return unchanged
        self.assertEqual(result, test_string)

    def test_format_dates_in_messages_list_input(self):
        """Test format_dates_in_messages with list of message objects."""
        # Create mock message objects
        message1 = Mock()
        message1.content = "Event on Jul 30, 2025"
        message1.model_copy.return_value = message1

        message2 = Mock()
        message2.content = "Another event on Dec 25, 2023"
        message2.model_copy.return_value = message2

        messages = [message1, message2]
        result = format_dates_in_messages(messages, "en-IN")
        
        self.assertEqual(len(result), 2)
        self.assertIn("30 Jul 2025", result[0].content)
        self.assertIn("25 Dec 2023", result[1].content)

    def test_format_dates_in_messages_list_with_no_content(self):
        """Test format_dates_in_messages with messages that have no content."""
        message1 = Mock()
        message1.content = "Event on Jul 30, 2025"
        message1.model_copy.return_value = message1

        message2 = Mock()
        message2.content = None  # No content

        message3 = Mock()
        del message3.content  # No content attribute

        messages = [message1, message2, message3]
        result = format_dates_in_messages(messages, "en-IN")
        
        self.assertEqual(len(result), 3)
        self.assertIn("30 Jul 2025", result[0].content)
        # Other messages should be returned as-is
        self.assertEqual(result[1], message2)
        self.assertEqual(result[2], message3)

    def test_format_dates_in_messages_unknown_locale(self):
        """Test format_dates_in_messages with unknown locale."""
        test_string = "Event on Jul 30, 2025"
        result = format_dates_in_messages(test_string, "unknown-locale")
        
        # Should use default format (Indian format)
        self.assertIn("30 Jul 2025", result)

    def test_format_dates_in_messages_parse_failure(self):
        """Test format_dates_in_messages when date parsing fails."""
        test_string = "Invalid date: Jul 32, 2025"  # Invalid day
        
        with patch('backend.common.utils.utils_date.parser.parse') as mock_parse:
            mock_parse.side_effect = Exception("Parse error")
            result = format_dates_in_messages(test_string, "en-US")
            
            # Should leave unchanged when parsing fails
            self.assertEqual(result, test_string)

    def test_format_dates_in_messages_multiple_dates_same_string(self):
        """Test format_dates_in_messages with multiple dates in same string."""
        test_string = "Events on Jul 30, 2025 and Dec 25, 2023 and Jan 1, 2024"
        result = format_dates_in_messages(test_string, "en-IN")
        
        self.assertIn("30 Jul 2025", result)
        self.assertIn("25 Dec 2023", result)
        self.assertIn("1 Jan 2024", result)

    def test_format_dates_in_messages_message_without_model_copy(self):
        """Test format_dates_in_messages with message objects without model_copy method."""
        message = Mock()
        message.content = "Event on Jul 30, 2025"
        del message.model_copy  # Remove model_copy method
        
        messages = [message]
        result = format_dates_in_messages(messages, "en-IN")
        
        # Should still process the message
        self.assertEqual(len(result), 1)
        self.assertIn("30 Jul 2025", result[0].content)

    def test_format_dates_in_messages_default_locale(self):
        """Test format_dates_in_messages with default locale (no parameter)."""
        test_string = "Event on Jul 30, 2025"
        result = format_dates_in_messages(test_string)
        
        # Default target_locale is "en-US", so US format should stay the same
        self.assertIsInstance(result, str)
        # The function should process the string but date format should remain the same
        self.assertIn("Jul 30, 2025", result)

    def test_format_dates_in_messages_edge_case_inputs(self):
        """Test format_dates_in_messages with edge case inputs."""
        edge_cases = [
            None,
            [],
            "",
            123,
            {"not": "a message"},
        ]
        
        for edge_case in edge_cases:
            with self.subTest(input=edge_case):
                result = format_dates_in_messages(edge_case)
                # Should return the input unchanged for non-supported types
                self.assertEqual(result, edge_case)

    def test_format_dates_in_messages_complex_date_patterns(self):
        """Test format_dates_in_messages with various date patterns."""
        test_cases = [
            ("Jul 30, 2025", "en-IN", "30 Jul 2025"),
            ("30 Jul 2025", "en-US", "Jul 30, 2025"),
            ("December 25, 2023", "en-IN", "25 Dec 2023"),
            ("25 December 2023", "en-US", "Dec 25, 2023"),
            ("Jul 30, 2025, 12:00:00 AM", "en-IN", "30 Jul 2025"),
            ("Jul 30, 2025, 11:59:59 PM", "en-IN", "30 Jul 2025"),
        ]
        
        for input_text, locale, expected_date in test_cases:
            with self.subTest(input=input_text, locale=locale):
                result = format_dates_in_messages(input_text, locale)
                self.assertIn(expected_date, result)


class TestUtilsDateIntegration(unittest.TestCase):
    """Integration tests for utils_date module."""

    def test_datetime_encoder_with_formatted_dates(self):
        """Test DateTimeEncoder working with format_date_for_user results."""
        # Create test data with datetime
        test_datetime = datetime(2023, 12, 25, 10, 30, 45)
        
        # Format date for user (this returns a string)
        formatted_date = format_date_for_user("2023-12-25")
        
        # Create data structure with both datetime and formatted date
        test_data = {
            "original_datetime": test_datetime,
            "formatted_date": formatted_date,
            "timestamp": datetime.now()
        }
        
        # Encode to JSON
        json_result = json.dumps(test_data, cls=DateTimeEncoder)
        
        # Should be valid JSON
        parsed_result = json.loads(json_result)
        
        # Verify datetime was encoded and formatted date was preserved
        self.assertEqual(parsed_result["original_datetime"], "2023-12-25T10:30:45")
        self.assertIsInstance(parsed_result["formatted_date"], str)
        self.assertIn("timestamp", parsed_result)

    def test_end_to_end_date_processing(self):
        """Test end-to-end date processing workflow."""
        # Start with raw datetime
        raw_datetime = datetime(2023, 7, 30, 14, 30, 0)
        
        # Convert to ISO string for format_date_for_user
        iso_date = raw_datetime.strftime("%Y-%m-%d")
        
        # Format for user display
        user_formatted = format_date_for_user(iso_date)
        
        # Create message with the formatted date
        message_content = f"Meeting scheduled for {user_formatted}"
        
        # Format dates in message content
        final_message = format_dates_in_messages(message_content, "en-IN")
        
        # Create final data structure
        result_data = {
            "message": final_message,
            "created_at": raw_datetime
        }
        
        # Encode to JSON
        json_output = json.dumps(result_data, cls=DateTimeEncoder)
        
        # Verify the complete workflow
        parsed_output = json.loads(json_output)
        self.assertIn("message", parsed_output)
        self.assertEqual(parsed_output["created_at"], "2023-07-30T14:30:00")


if __name__ == "__main__":
    unittest.main()