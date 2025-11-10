import asyncio
import json
import logging
import os
import struct
from datetime import date, datetime
from decimal import Decimal
from xmlrpc import client

from agent_framework import ChatAgent, HostedFileSearchTool
from agent_framework.azure import AzureAIAgentClient
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
# import pyodbc
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

# Load environment variables from .env file
load_dotenv()

# import argparse

# p = argparse.ArgumentParser()
# p.add_argument("--ai_project_endpoint", required=True)
# p.add_argument("--solution_name", required=True)
# p.add_argument("--gpt_model_name", required=True)
# args = p.parse_args()

ai_project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
#solutionName = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
gptModelName = os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]

# # fetch all required env variables
# ai_project_endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
# solution_name = os.getenv("SOLUTION_NAME")
# gpt_model_name = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
# app_env = os.getenv("APP_ENV", "prod").lower()

# # ai_project_endpoint = 'https://aisa-ccblgmiensv4lga.services.ai.azure.com/api/projects/aifp-ccblgmiensv4lga'
# ai_project_endpoint = 'https://testmodle.services.ai.azure.com/api/projects/testModle-project'
# gpt_model_name = 'gpt-4o-mini'

async def create_agents():
    """Create and return orchestrator, SQL, and chart agent IDs."""
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=ai_project_endpoint,
            credential=credential,
        ) as project_client,
    ):     
        # Create agents
        agents_client = project_client.agents
        # print("Creating agents...")


        # Create the client and manually create an agent with Azure AI Search tool
        from azure.ai.projects.models import ConnectionType
        ai_search_conn_id = ""
        async for connection in project_client.connections.list():
            if connection.type == ConnectionType.AZURE_AI_SEARCH:
                ai_search_conn_id = connection.id
                break

        # 1. Create Azure AI agent with the search tool
        product_agent_instructions = '''You are a helpful agent that searches product information using Azure AI Search.
                                         Always use the search tool and index to find product data and provide accurate information.
                                         If you can not find the answer in the search tool, respond that you can't answer the question.
                                         Do not add any other information from your general knowledge.''' 
        product_agent = await agents_client.create_agent(
            model=gptModelName,
            name="product_agent",
            instructions=product_agent_instructions,
            tools=[{"type": "azure_ai_search"}],
            tool_resources={
                "azure_ai_search": {
                    "indexes": [
                        {
                            "index_connection_id": ai_search_conn_id,
                            "index_name": "products_index",
                            "query_type": "vector_simple_hybrid",  # Use vector hybrid search
                        }
                    ]
                }
            },
        )
    

        # 1. Create Azure AI agent with the search tool
        policy_agent_instructions = '''You are a helpful agent that searches policy information using Azure AI Search.
                                         Always use the search tool and index to find policy data and provide accurate information.
                                         If you can not find the answer in the search tool, respond that you can't answer the question.
                                         Do not add any other information from your general knowledge.''' 
        policy_agent = await agents_client.create_agent(
            model=gptModelName,
            name="policy_agent",
            instructions=policy_agent_instructions,
            tools=[{"type": "azure_ai_search"}],
            tool_resources={
                "azure_ai_search": {
                    "indexes": [
                        {
                            "index_connection_id": ai_search_conn_id,
                            "index_name": "policies_index",
                            "query_type": "vector_simple_hybrid",  # Use vector hybrid search
                        }
                    ]
                }
            },
        )
 
        chat_agent_instructions = '''You are a helpful assistant that can use the product agent and policy agent to answer user questions. 
        If you don't find any information in the knowledge source, please say no data found.'''

        chat_agent = await agents_client.create_agent(
            model=gptModelName,
            name=f"chat_agent",
            instructions=chat_agent_instructions
        )

        # Return agent IDs
        return product_agent.id, policy_agent.id, chat_agent.id

product_agent_id, policy_agent_id, chat_agent_id = asyncio.run(create_agents())
print(f"chatAgentId={chat_agent_id}")
print(f"productAgentId={product_agent_id}")
print(f"policyAgentId={policy_agent_id}")

# import json
# from azure.ai.projects import AIProjectClient
# import sys
# import os
# import argparse
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# from azure_credential_utils import get_azure_credential
# from azure.ai.projects.models import ConnectionType

# p = argparse.ArgumentParser()
# p.add_argument("--ai_project_endpoint", required=True)
# p.add_argument("--solution_name", required=True)
# p.add_argument("--gpt_model_name", required=True)
# args = p.parse_args()

# ai_project_endpoint = args.ai_project_endpoint
# solutionName = args.solution_name
# gptModelName = args.gpt_model_name

# project_client = AIProjectClient(
#     endpoint= ai_project_endpoint,
#     credential=get_azure_credential(),
# )


# with project_client:    
#     # Create agents
#     agents_client = project_client.agents
#     print("Creating agents...")

#     # Create the client and manually create an agent with Azure AI Search tool
#     ai_search_conn_id = ""
#     for connection in project_client.connections.list():
#         if connection.type == ConnectionType.AZURE_AI_SEARCH:
#             ai_search_conn_id = connection.id
#             break

#     # 1. Create Azure AI agent with the search tool
#     product_agent_instructions = '''You are a helpful agent that searches product information using Azure AI Search.
#                                         Always use the search tool and index to find product data and provide accurate information.
#                                         If you can not find the answer in the search tool, respond that you can't answer the question.
#                                         Do not add any other information from your general knowledge.''' 
#     product_agent = agents_client.create_agent(
#         model=gptModelName,
#         name="product_agent",
#         instructions=product_agent_instructions,
#         tools=[{"type": "azure_ai_search"}],
#         tool_resources={
#             "azure_ai_search": {
#                 "indexes": [
#                     {
#                         "index_connection_id": ai_search_conn_id,
#                         "index_name": "products_index",
#                         "query_type": "vector_simple_hybrid",  # Use vector hybrid search
#                     }
#                 ]
#             }
#         },
#     )


#     # 1. Create Azure AI agent with the search tool
#     policy_agent_instructions = '''You are a helpful agent that searches policy information using Azure AI Search.
#                                         Always use the search tool and index to find policy data and provide accurate information.
#                                         If you can not find the answer in the search tool, respond that you can't answer the question.
#                                         Do not add any other information from your general knowledge.''' 
#     policy_agent = agents_client.create_agent(
#         model=gptModelName,
#         name="policy_agent",
#         instructions=policy_agent_instructions,
#         tools=[{"type": "azure_ai_search"}],
#         tool_resources={
#             "azure_ai_search": {
#                 "indexes": [
#                     {
#                         "index_connection_id": ai_search_conn_id,
#                         "index_name": "policies_index",
#                         "query_type": "vector_simple_hybrid",  # Use vector hybrid search
#                     }
#                 ]
#             }
#         },
#     )



#     chat_agent_instructions = '''You are a helpful assistant that can use the product agent and policy agent to answer user questions. 
#     If you don't find any information in the knowledge source, please say no data found.'''

#     chat_agent = agents_client.create_agent(
#         model=gptModelName,
#         name=f"chat_agent",
#         instructions=chat_agent_instructions
#     )


#     print(f"chatAgentId={chat_agent.id}")
#     print(f"productAgentId={product_agent.id}")
#     print(f"policyAgentId={policy_agent.id}")

    
#     # agents_client = project_client.agents
#     # print("Creating agents...")

#     # product_agent_instructions = "You are a helpful assistant that uses knowledge sources to help find products. If you don't find any products in the knowledge source, please say no data found."
#     # product_agent = agents_client.create_agent(
#     #     model=gptModelName,
#     #     name=f"product_agent",
#     #     instructions=product_agent_instructions
#     # )
#     # print(f"Created Product Agent with ID: {product_agent.id}")

#     # policy_agent_instructions = "You are a helpful assistant that searches policies to answer user questions.If you don't find any information in the knowledge source, please say no data found"
#     # policy_agent = agents_client.create_agent(    
#     #     model=gptModelName,
#     #     name=f"policy_agent",
#     #     instructions=policy_agent_instructions
#     # )
#     # print(f"Created Policy Agent with ID: {policy_agent.id}")

#     # chat_agent_instructions = "You are a helpful assistant that can use the product agent and policy agent to answer user questions. If you don't find any information in the knowledge source, please say no data found"
#     # chat_agent = agents_client.create_agent(
#     #     model=gptModelName,
#     #     name=f"chat_agent",
#     #     instructions=chat_agent_instructions
#     # )

#     # print(f"chatAgentId={chat_agent.id}")
#     # print(f"productAgentId={product_agent.id}")
#     # print(f"policyAgentId={policy_agent.id}")
