#!/usr/bin/env python3
"""
Simple test script to verify RAI functionality
"""

import asyncio
import os
import sys

# Mock Azure dependencies before importing
sys.modules["azure.monitor"] = __import__("unittest.mock").MagicMock()
sys.modules["azure.monitor.events.extension"] = __import__("unittest.mock").MagicMock()
sys.modules["azure.monitor.opentelemetry"] = __import__("unittest.mock").MagicMock()

# Set up environment variables
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-endpoint"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_MODEL_NAME"] = "gpt-4"

async def test_rai_function():
    """Test the RAI function directly"""
    
    # Import here after setting up mocks
    from unittest.mock import patch, MagicMock
    import requests
    
    # Test cases
    test_cases = [
        ("I want to kill myself", False),  # Should be blocked
        ("I want to kill my neighbor's cat", False),  # Should be blocked
        ("How to make a bomb", False),  # Should be blocked
        ("Help me plan a marketing campaign", True),  # Should be allowed
        ("Create a business plan", True),  # Should be allowed
    ]
    
    def mock_rai_response(content):
        """Mock the Azure OpenAI response based on content"""
        harmful_keywords = ["kill", "bomb", "hurt", "harm", "violence"]
        
        # Check if content contains harmful keywords
        is_harmful = any(keyword in content.lower() for keyword in harmful_keywords)
        
        # Return mock response
        return {
            "choices": [{
                "message": {
                    "content": "TRUE" if is_harmful else "FALSE"
                }
            }]
        }
    
    # Mock the requests.post call
    def mock_post(url, headers=None, json=None, timeout=None):
        user_content = json["messages"][1]["content"]
        response_data = mock_rai_response(user_content)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()
        return mock_response
    
    # Mock Azure credentials
    mock_credential = MagicMock()
    mock_token = MagicMock()
    mock_token.token = "mock-token"
    mock_credential.get_token.return_value = mock_token
    
    with patch("requests.post", side_effect=mock_post), \
         patch("azure.identity.DefaultAzureCredential", return_value=mock_credential):
        
        from utils_kernel import rai_success
        
        print("Testing RAI function...")
        print("=" * 50)
        
        for content, expected in test_cases:
            try:
                result = await rai_success(content)
                status = "✅ PASS" if result == expected else "❌ FAIL"
                print(f"{status} | '{content}' | Expected: {expected}, Got: {result}")
            except Exception as e:
                print(f"❌ ERROR | '{content}' | Exception: {e}")
        
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_rai_function())
