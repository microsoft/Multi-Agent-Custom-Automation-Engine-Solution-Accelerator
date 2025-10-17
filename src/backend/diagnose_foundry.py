"""
Diagnostic script to check Azure AI Foundry Project configuration.
Run this to see what models and resources are available.
"""
import asyncio
import sys
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

async def diagnose():
    print("="*70)
    print(" Azure AI Foundry Project Diagnostics")
    print("="*70)
    print()
    
    # Get configuration
    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    print(f"Endpoint: {endpoint}")
    print()
    
    # Create client
    print("Creating AI Project client...")
    creds = DefaultAzureCredential()
    client = AIProjectClient(endpoint=endpoint, credential=creds)
    
    try:
        print("✅ Client created successfully")
        print()
        
        # Try to list connections
        print("-" * 70)
        print("Connections:")
        print("-" * 70)
        try:
            connections = client.connections.list()
            async for conn in connections:
                print(f"  - {conn.name}")
                print(f"    Type: {conn.connection_type}")
                if hasattr(conn, 'endpoint_url'):
                    print(f"    Endpoint: {conn.endpoint_url}")
                print()
        except Exception as e:
            print(f"❌ Error listing connections: {e}")
        
        # Try to list existing agents
        print("-" * 70)
        print("Existing Agents:")
        print("-" * 70)
        try:
            agents = client.agents.list_agents()
            count = 0
            async for agent in agents:
                count += 1
                print(f"  {count}. {agent.name}")
                print(f"     ID: {agent.id}")
                print(f"     Model: {agent.model}")
                print()
            if count == 0:
                print("  No agents found")
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
            print(f"   Error type: {type(e).__name__}")
        
        print()
        print("-" * 70)
        print("Attempting to create a test agent...")
        print("-" * 70)
        
        # Try to create an agent with gpt-4.1
        try:
            test_agent = await client.agents.create_agent(
                model="gpt-4.1",
                name="DiagnosticTestAgent",
                description="Test agent for diagnostics",
                instructions="You are a test agent"
            )
            print(f"✅ SUCCESS! Agent created with ID: {test_agent.id}")
            print(f"   Model used: {test_agent.model}")
            
            # Clean up
            print(f"   Deleting test agent...")
            await client.agents.delete_agent(test_agent.id)
            print(f"   ✅ Test agent deleted")
            
        except Exception as e:
            print(f"❌ FAILED to create agent")
            print(f"   Error: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Try with different model names
            print()
            print("Trying alternative model names...")
            for model_name in ["gpt-4", "gpt-4o", "gpt-4-turbo", "gpt-4-32k"]:
                try:
                    print(f"  Trying '{model_name}'...")
                    test_agent = await client.agents.create_agent(
                        model=model_name,
                        name="DiagnosticTestAgent",
                        description="Test agent",
                        instructions="Test"
                    )
                    print(f"  ✅ SUCCESS with '{model_name}'! Agent ID: {test_agent.id}")
                    await client.agents.delete_agent(test_agent.id)
                    break
                except Exception as ex:
                    print(f"  ❌ Failed with '{model_name}': {ex}")
        
    finally:
        await creds.close()
        await client.close()
    
    print()
    print("="*70)
    print(" Diagnostics Complete")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(diagnose())



