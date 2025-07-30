#!/usr/bin/env python3
"""
Test script to verify the complete plan creation and generation flow
"""

import asyncio
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Mock Azure dependencies BEFORE any imports
sys.modules["azure.monitor"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()
sys.modules["azure.ai"] = MagicMock()
sys.modules["azure.ai.projects"] = MagicMock()
sys.modules["azure.ai.projects.aio"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.identity.aio"] = MagicMock()

# Set up environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "o3"
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-12-01-preview"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test-endpoint.com"
os.environ["AZURE_OPENAI_MODEL_NAME"] = "o3"

from fastapi.testclient import TestClient

# Mock telemetry initialization
with patch("azure.monitor.opentelemetry.configure_azure_monitor", MagicMock()):
    from app_kernel import app

client = TestClient(app)

def test_complete_flow():
    """Test the complete flow: create plan -> generate plan details"""
    
    headers = {"Authorization": "Bearer test-token"}
    
    # Mock authentication
    with patch("auth.auth_utils.get_authenticated_user_details", 
               return_value={"user_principal_id": "test-user"}), \
         patch("utils_kernel.rai_success", return_value=True), \
         patch("app_kernel.initialize_runtime_and_context") as mock_init, \
         patch("app_kernel.track_event_if_configured"):
        
        # Mock memory store
        mock_memory_store = MagicMock()
        mock_init.return_value = (MagicMock(), mock_memory_store)
        
        # Step 1: Create a plan
        test_input = {
            "session_id": "test-session-123",
            "description": "Create a marketing plan for our new product"
        }
        
        print("Step 1: Creating plan...")
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        print(f"Create plan response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            plan_id = data.get("plan_id")
            print(f"✅ Plan created successfully with ID: {plan_id}")
            
            # Step 2: Mock the generate plan stream
            print("\nStep 2: Testing generate plan endpoint...")
            
            # Mock the streaming function
            async def mock_stream():
                yield "Starting plan generation...\n"
                yield "[PROCESSING] Analyzing task...\n"
                yield "I need to create a comprehensive marketing plan.\n"
                yield "[PROCESSING] Creating steps...\n"
                yield "[SUCCESS] Plan generation complete!\n"
                yield '[RESULT] {"status": "success", "plan_id": "test-id", "steps_created": 3}\n'
            
            with patch("utils_kernel.generate_plan_with_reasoning_stream", 
                      return_value=mock_stream()):
                
                # Test the generate endpoint
                response = client.post(f"/api/generate_plan/{plan_id}", headers=headers)
                print(f"Generate plan response: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Generate plan endpoint working")
                    # In a real scenario, this would stream the response
                else:
                    print(f"❌ Generate plan failed: {response.text}")
        else:
            print(f"❌ Create plan failed: {response.text}")

def test_rai_blocking():
    """Test that RAI properly blocks harmful content"""
    
    headers = {"Authorization": "Bearer test-token"}
    
    # Mock authentication and RAI failure
    with patch("auth.auth_utils.get_authenticated_user_details", 
               return_value={"user_principal_id": "test-user"}), \
         patch("utils_kernel.rai_success", return_value=False), \
         patch("app_kernel.track_event_if_configured"):
        
        test_input = {
            "session_id": "test-session-456",
            "description": "I want to harm someone"
        }
        
        print("\nTesting RAI blocking...")
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        print(f"RAI test response: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            if "safety validation" in data.get("detail", ""):
                print("✅ RAI correctly blocked harmful content")
            else:
                print(f"❓ Blocked for different reason: {data}")
        else:
            print("❌ RAI failed to block harmful content")

if __name__ == "__main__":
    print("Testing complete MACAE flow...")
    print("=" * 60)
    
    test_complete_flow()
    test_rai_blocking()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
