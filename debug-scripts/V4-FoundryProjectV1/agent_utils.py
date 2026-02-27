# Copyright (c) Microsoft. All rights reserved.

"""
Shared utilities for standalone Agent Framework scenarios.
Provides reusable functions for creating agents, managers, and running workflows.
"""

import logging
from typing import cast
from dataclasses import dataclass

from agent_framework import (
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    MagenticBuilder,
    WorkflowOutputEvent,
    InMemoryCheckpointStorage,
    MagenticOrchestratorMessageEvent,
    MagenticAgentMessageEvent,
    MagenticAgentDeltaEvent,
    MagenticFinalResultEvent,
)
from agent_framework._workflows._magentic import (
    StandardMagenticManager,
    MagenticContext,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
)
from typing import Any
from agent_framework_azure_ai import AzureAIAgentClient
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.ai.agents.aio import AgentsClient
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as DefaultAzureCredentialAsync
import os

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class HumanApprovalManager(StandardMagenticManager):
    """
    Extended Magentic manager that requires human approval before executing plan steps.
    Provides interactive console-based approval for standalone scripts.
    """

    def __init__(self, *args, require_approval: bool = True, **kwargs):
        """
        Initialize the HumanApprovalManager.

        Args:
            require_approval: If True, pauses for user approval after plan generation.
            *args: Additional positional arguments for StandardMagenticManager.
            **kwargs: Additional keyword arguments for StandardMagenticManager.
        """
        self.require_approval = require_approval
        super().__init__(*args, **kwargs)

    async def plan(self, magentic_context: MagenticContext) -> Any:
        """
        Override the plan method to create the plan first, then ask for approval before execution.
        Returns the original plan ChatMessage if approved, otherwise raises.
        """
        # Get task text for display
        task_text = getattr(magentic_context.task, "text", str(magentic_context.task))

        logger.info("\nHuman Approval Manager Creating Plan:")
        logger.info("   Task: %s", task_text)

        # Call parent to generate the plan
        plan_message = await super().plan(magentic_context)

        if not self.require_approval:
            return plan_message

        # Display the generated plan
        print("\n" + "=" * 80)
        print("PROPOSED PLAN")
        print("=" * 80)
        if plan_message and plan_message.text:
            print(plan_message.text)
        print("=" * 80)

        # Wait for user approval via console input
        while True:
            response = input("\nDo you approve this plan? (yes/no/y/n): ").strip().lower()
            if response in ("yes", "y"):
                print("✓ Plan approved - proceeding with execution...")
                return plan_message
            elif response in ("no", "n"):
                print("✗ Plan rejected by user")
                raise Exception("Plan execution cancelled by user")
            else:
                print("Please enter 'yes' or 'no'")


@dataclass
class AgentConfig:
    """Configuration for creating an agent with Azure AI Search."""
    name: str
    description: str
    instructions: str
    index_name: str
    model: str = "gpt-4.1-mini"


@dataclass
class AzureClients:
    """Container for Azure clients used in agent workflows."""
    project_client: AIProjectClient
    agents_client: AgentsClient
    credential_sync: DefaultAzureCredential
    credential_async: DefaultAzureCredentialAsync
    project_endpoint: str

    async def close(self):
        """Close all async clients."""
        await self.agents_client.close()
        await self.credential_async.close()


def get_azure_clients(project_endpoint: str | None = None) -> AzureClients:
    """
    Initialize Azure clients for agent creation and management.

    Args:
        project_endpoint: Azure AI Project endpoint. If None, reads from environment.

    Returns:
        AzureClients container with all initialized clients.
    """
    endpoint = project_endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")

    credential_sync = DefaultAzureCredential()
    credential_async = DefaultAzureCredentialAsync()

    project_client = AIProjectClient(
        credential=credential_sync,
        endpoint=endpoint
    )

    agents_client = AgentsClient(
        endpoint=endpoint,
        credential=credential_async,
    )

    return AzureClients(
        project_client=project_client,
        agents_client=agents_client,
        credential_sync=credential_sync,
        credential_async=credential_async,
        project_endpoint=endpoint
    )


async def create_agent_with_search(
    clients: AzureClients,
    config: AgentConfig,
    search_connection_name: str | None = None,
) -> ChatAgent:
    """
    Create an Azure AI Agent with Azure AI Search tool.

    Args:
        clients: AzureClients container with initialized clients
        config: AgentConfig with agent settings
        search_connection_name: Optional specific search connection name

    Returns:
        ChatAgent configured with Azure AI Search
    """
    # Find Azure AI Search connection
    search_connection_id = None
    for connection in clients.project_client.connections.list():
        if connection.type == ConnectionType.AZURE_AI_SEARCH:
            if search_connection_name and connection.name == search_connection_name:
                search_connection_id = connection.id
                logger.info("Found specified search connection: %s (ID: %s)", connection.name, connection.id)
                break
            elif not search_connection_name and not search_connection_id:
                search_connection_id = connection.id
                logger.info("Using search connection: %s (ID: %s)", connection.name, connection.id)

    if not search_connection_id:
        raise ValueError(
            f"No Azure AI Search connection found. "
            f"{'Requested: ' + search_connection_name if search_connection_name else 'No connections available'}"
        )

    # Create server-side agent with Azure AI Search tool
    azure_agent = await clients.agents_client.create_agent(
        model=config.model,
        name=config.name,
        instructions=(
            f"{config.instructions} "
            f"Always use the Azure AI Search tool and configured index for knowledge retrieval."
        ),
        tools=[{"type": "azure_ai_search"}],
        tool_resources={
            "azure_ai_search": {
                "indexes": [
                    {
                        "index_connection_id": search_connection_id,
                        "index_name": config.index_name,
                        "query_type": "simple",
                    }
                ]
            }
        },
    )

    logger.info(
        "Created Azure agent '%s' (ID: %s) with search index '%s'",
        config.name, azure_agent.id, config.index_name
    )

    # Create chat client for the agent
    chat_client = AzureAIAgentClient(
        project_client=clients.project_client,
        agent_id=azure_agent.id,
        async_credential=clients.credential_async,
    )

    return ChatAgent(
        id=azure_agent.id,
        name=config.name,
        description=config.description,
        instructions=config.instructions,
        chat_client=chat_client,
        tool_choice="required",
        temperature=0.1,
        model_id=config.model,
    )


def create_magentic_manager(
    clients: AzureClients,
    team_name: str,
    agent_names: list[str],
    model: str = "gpt-4.1-mini",
    max_round_count: int = 20,
    require_approval: bool = False,
) -> tuple[StandardMagenticManager, AzureAIAgentClient]:
    """
    Create a StandardMagenticManager with custom prompts for multi-agent orchestration.

    Args:
        clients: AzureClients container
        team_name: Name for the orchestrator team
        agent_names: List of agent names for planning guidance
        model: Model deployment name for orchestrator
        max_round_count: Maximum rounds for orchestration
        require_approval: If True, uses HumanApprovalManager for interactive approval

    Returns:
        Tuple of (StandardMagenticManager or HumanApprovalManager, manager_chat_client)
    """
    manager_chat_client = AzureAIAgentClient(
        project_endpoint=clients.project_endpoint,
        model_deployment_name=model,
        agent_name=team_name,
        async_credential=clients.credential_async,
    )

    # Build agent list string for prompts
    agent_list_str = ", ".join(agent_names)

    plan_append = f"""

IMPORTANT: Never ask the user for information or clarification until all agents on the team have been asked first.

EXAMPLE: If the user request involves document analysis, first ask all agents on the team ({agent_list_str})
to provide their analysis. Do not ask the user unless all agents have been consulted and the information is still missing.

Plan steps should always include a bullet point, followed by an agent name, followed by a description of the action
to be taken. If a step involves multiple actions, separate them into distinct steps with an agent included in each step.

If the step is taken by an agent that is not part of the team, such as the MagenticManager, please always list the
MagenticManager as the agent for that step.

Here is an example of a well-structured analysis plan:
""" + "\n".join([f"- **{name}** to analyze and provide findings based on their specialized focus area." for name in agent_names]) + """
- **MagenticManager** to consolidate findings from all agents and prepare the final comprehensive analysis.
"""

    final_append = """
DO NOT EVER OFFER TO HELP FURTHER IN THE FINAL ANSWER! Just provide the final answer and end with a polite closing.
"""

    # Choose manager class based on approval requirement
    manager_class = HumanApprovalManager if require_approval else StandardMagenticManager

    manager_kwargs = {
        "chat_client": manager_chat_client,
        "task_ledger_plan_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append,
        "task_ledger_plan_update_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append,
        "final_answer_prompt": ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append,
        "max_round_count": max_round_count,
    }

    if require_approval:
        manager_kwargs["require_approval"] = True

    manager = manager_class(**manager_kwargs)

    return manager, manager_chat_client


def build_workflow(
    agents: dict[str, ChatAgent],
    manager: StandardMagenticManager,
):
    """
    Build a Magentic workflow with the given agents and manager.

    Args:
        agents: Dictionary mapping agent names to ChatAgent instances
        manager: StandardMagenticManager for orchestration

    Returns:
        Configured Magentic workflow ready to execute
    """
    storage = InMemoryCheckpointStorage()
    workflow = (
        MagenticBuilder()
        .participants(**agents)
        .with_standard_manager(
            manager=manager,
            max_stall_count=0,
        )
        .with_checkpointing(storage)
        .build()
    )
    return workflow


async def run_workflow_with_streaming(workflow, task: str) -> str:
    """
    Execute a workflow with streaming output and return the final result.

    Args:
        workflow: The Magentic workflow to execute
        task: The task description to process

    Returns:
        The final output text from the workflow
    """
    print(f"\nTask: {task}")
    print("\nStarting workflow execution...")

    last_message_id: str | None = None
    output_event: WorkflowOutputEvent | None = None

    async for event in workflow.run_stream(task):
        if isinstance(event, MagenticOrchestratorMessageEvent):
            message_text = getattr(event.message, 'text', '')
            print(f"\n[Orchestrator:{event.kind}] {message_text}", flush=True)

        elif isinstance(event, MagenticAgentDeltaEvent):
            agent_id = getattr(event, 'agent_id', 'Unknown')
            if agent_id != last_message_id:
                if last_message_id is not None:
                    print("\n")
                print(f"\n[Agent Response - {agent_id}]: ", end="", flush=True)
                last_message_id = agent_id
            if hasattr(event, 'text'):
                print(event.text, end="", flush=True)
            elif hasattr(event, 'content'):
                print(event.content, end="", flush=True)

        elif isinstance(event, MagenticAgentMessageEvent):
            agent_id = getattr(event, 'agent_id', 'Unknown')
            print(f"\n[Agent Complete - {agent_id}]", flush=True)

        elif isinstance(event, MagenticFinalResultEvent):
            final_text = getattr(event.message, 'text', '')
            print(f"\n[Final Result] Length: {len(final_text)} chars", flush=True)

        elif isinstance(event, AgentRunUpdateEvent):
            message_id = event.data.message_id if event.data else None
            if message_id and message_id != last_message_id:
                if last_message_id is not None:
                    print("\n")
                print(f"- {event.executor_id}:", end=" ", flush=True)
                last_message_id = message_id
            if event.data:
                print(event.data, end="", flush=True)

        elif isinstance(event, WorkflowOutputEvent):
            output_event = event

    if not output_event:
        raise RuntimeError("Workflow did not produce a final output event.")

    print("\n\nWorkflow completed!")
    output_message = cast(ChatMessage, output_event.data)
    return output_message.text if output_message and output_message.text else ""


async def cleanup_agents(
    clients: AzureClients,
    agents: list[ChatAgent],
    manager_chat_client: AzureAIAgentClient | None = None,
):
    """
    Clean up Azure agents and close all clients.

    Args:
        clients: AzureClients container
        agents: List of ChatAgent instances to clean up
        manager_chat_client: Optional manager chat client to close
    """
    print("\n\nCleaning up Azure agents...")

    # Close chat clients for all agents
    for agent in agents:
        try:
            if hasattr(agent, 'chat_client') and hasattr(agent.chat_client, 'close'):
                await agent.chat_client.close()
                logger.info("Closed chat client for: %s", agent.name)
        except Exception as e:
            logger.warning("Failed to close chat client for %s: %s", agent.name, e)

    # Close manager chat client
    if manager_chat_client:
        try:
            if hasattr(manager_chat_client, 'close'):
                await manager_chat_client.close()
                logger.info("Closed manager chat client")
        except Exception as e:
            logger.warning("Failed to close manager chat client: %s", e)

    # Delete server-side agents
    for agent in agents:
        try:
            await clients.agents_client.delete_agent(agent.id)
            logger.info("Deleted Azure agent: %s (ID: %s)", agent.name, agent.id)
        except Exception as e:
            logger.warning("Failed to delete agent %s: %s", agent.name, e)

    # Close Azure clients
    await clients.close()
    print("✓ Cleanup completed")
