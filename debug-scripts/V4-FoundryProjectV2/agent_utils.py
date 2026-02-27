# Copyright (c) Microsoft. All rights reserved.

"""
Shared utilities for standalone Agent Framework scenarios.
Provides reusable functions for creating agents, managers, and running workflows.
"""

import logging
import re
from typing import Any
from dataclasses import dataclass

from agent_framework import (
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    MagenticBuilder,
    WorkflowOutputEvent,
    InMemoryCheckpointStorage,
    GroupChatRequestSentEvent,
    GroupChatResponseReceivedEvent,
    ExecutorCompletedEvent,
    MagenticOrchestratorEvent,
    MagenticProgressLedger,
)
from agent_framework._workflows._magentic import (
    StandardMagenticManager,
    MagenticContext,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
)
from agent_framework_azure_ai import AzureAIClient
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
)
from azure.identity.aio import DefaultAzureCredential
import os

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class HumanApprovalManager(StandardMagenticManager):
    """
    Extended Magentic manager that requires human approval before executing plan steps.
    Provides interactive console-based approval for standalone scripts.
    Mirrors the v4 backend HumanApprovalMagenticManager patterns.
    """

    def __init__(self, agent, *args, require_approval: bool = True, max_rounds: int = 20, **kwargs):
        """
        Initialize the HumanApprovalManager.

        Args:
            agent: The manager ChatAgent for orchestration (required by new API).
            require_approval: If True, pauses for user approval after plan generation.
            max_rounds: Maximum number of orchestration rounds before termination.
            *args: Additional positional arguments for StandardMagenticManager.
            **kwargs: Additional keyword arguments for StandardMagenticManager.
        """
        self.require_approval = require_approval
        self.max_rounds = max_rounds

        # Add progress ledger prompt to prevent re-calling agents (matching v4 backend)
        progress_append = """
CRITICAL RULE: DO NOT call the same agent more than once unless absolutely necessary.
If an agent has already provided a response, consider their task COMPLETE and move to the next agent.
Only re-call an agent if their previous response was explicitly an error or failure.
"""
        kwargs["progress_ledger_prompt"] = ORCHESTRATOR_PROGRESS_LEDGER_PROMPT + progress_append

        # New API: StandardMagenticManager takes agent as first positional argument
        super().__init__(agent, *args, **kwargs)

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

    async def replan(self, magentic_context: MagenticContext) -> Any:
        """
        Override to add logging for replanning events.
        """
        logger.info("\nHuman Approval Manager replanning...")
        replan_message = await super().replan(magentic_context=magentic_context)
        logger.info(
            "Replanned message length: %d",
            len(replan_message.text) if replan_message and replan_message.text else 0,
        )
        return replan_message

    async def create_progress_ledger(self, magentic_context: MagenticContext):
        """
        Check for max rounds exceeded and terminate if so, else defer to base.
        Matches v4 backend pattern.
        """
        if magentic_context.round_count >= self.max_rounds:
            print(f"\n⚠ Process terminated: Maximum rounds ({self.max_rounds}) exceeded")

            # Call base class to get the proper ledger type, then override to terminate
            ledger = await super().create_progress_ledger(magentic_context)

            # Override key fields to signal termination
            ledger.is_request_satisfied.answer = True
            ledger.is_request_satisfied.reason = "Maximum rounds exceeded"
            ledger.is_in_loop.answer = False
            ledger.is_in_loop.reason = "Terminating"
            ledger.is_progress_being_made.answer = False
            ledger.is_progress_being_made.reason = "Terminating"
            ledger.next_speaker.answer = ""
            ledger.next_speaker.reason = "Task complete"
            ledger.instruction_or_question.answer = "Process terminated due to maximum rounds exceeded"
            ledger.instruction_or_question.reason = "Task complete"

            return ledger

        # Delegate to base for normal progress ledger creation
        return await super().create_progress_ledger(magentic_context)

    async def prepare_final_answer(self, magentic_context: MagenticContext) -> ChatMessage:
        """
        Override to ensure final answer is prepared after all steps are executed.
        """
        logger.info("\nMagentic Manager - Preparing final answer...")
        return await super().prepare_final_answer(magentic_context)


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
    credential: DefaultAzureCredential
    project_endpoint: str

    async def close(self):
        """Close all async clients."""
        await self.project_client.close()
        await self.credential.close()


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

    credential = DefaultAzureCredential()

    project_client = AIProjectClient(
        credential=credential,
        endpoint=endpoint
    )

    return AzureClients(
        project_client=project_client,
        credential=credential,
        project_endpoint=endpoint
    )


async def create_agent_with_search(
    clients: AzureClients,
    config: AgentConfig,
    search_connection_name: str | None = None,
) -> ChatAgent:
    """
    Create an Azure AI Agent with Azure AI Search tool using create_version.

    Uses the v2 API pattern:
    - AIProjectClient.agents.create_version() with PromptAgentDefinition
    - AzureAISearchAgentTool with AzureAISearchToolResource for search capability
    - AISearchIndexResource with project_connection_id for index configuration

    Args:
        clients: AzureClients container with initialized clients
        config: AgentConfig with agent settings
        search_connection_name: Optional specific search connection name

    Returns:
        ChatAgent configured with Azure AI Search
    """
    # Resolve connection name for Azure AI Search
    connection_name = search_connection_name or os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")
    if not connection_name:
        raise ValueError(
            "Azure AI Search connection name is required. "
            "Set AZURE_AI_SEARCH_CONNECTION_NAME environment variable or pass search_connection_name."
        )

    enhanced_instructions = (
        f"{config.instructions} "
        f"Always use the Azure AI Search tool and configured index for knowledge retrieval."
    )

    # Create server-side agent using create_version with PromptAgentDefinition
    azure_agent = await clients.project_client.agents.create_version(
        agent_name=config.name,
        definition=PromptAgentDefinition(
            model=config.model,
            instructions=enhanced_instructions,
            tools=[
                AzureAISearchAgentTool(
                    azure_ai_search=AzureAISearchToolResource(
                        indexes=[
                            AISearchIndexResource(
                                project_connection_id=connection_name,
                                index_name=config.index_name,
                                query_type="simple",
                                top_k=5,
                            )
                        ]
                    )
                )
            ],
        ),
    )

    logger.info(
        "Created Azure agent via create_version (name=%s, id=%s, version=%s) with search index '%s'",
        azure_agent.name, azure_agent.id, azure_agent.version, config.index_name
    )

    # Create chat client using AzureAIClient with agent_name and agent_version
    chat_client = AzureAIClient(
        project_endpoint=clients.project_endpoint,
        agent_name=azure_agent.name,
        agent_version=azure_agent.version,
        model_deployment_name=config.model,
        credential=clients.credential,
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
        default_options={"store": False},
    )


def create_magentic_manager(
    clients: AzureClients,
    team_name: str,
    agent_names: list[str],
    model: str = "gpt-4.1-mini",
    max_round_count: int = 20,
    require_approval: bool = False,
) -> tuple[StandardMagenticManager, AzureAIClient]:
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
    # Sanitize agent name: must start/end with alphanumeric, only hyphens allowed, max 63 chars
    # (matching v4 backend orchestration_manager.py pattern)
    raw_name = team_name if team_name else "OrchestratorAgent"
    sanitized_name = re.sub(r'[^a-zA-Z0-9-]', '-', raw_name)
    sanitized_name = re.sub(r'-+', '-', sanitized_name)  # Collapse multiple hyphens
    sanitized_name = sanitized_name.strip('-')[:63]  # Trim and limit length
    agent_name = sanitized_name if sanitized_name else "OrchestratorAgent"

    manager_chat_client = AzureAIClient(
        project_endpoint=clients.project_endpoint,
        model_deployment_name=model,
        agent_name=agent_name,
        credential=clients.credential,
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

CRITICAL: Each agent should only be called ONCE to perform their task. Do NOT call the same agent multiple times.
After an agent has provided their response, move on to the next agent in the plan.

Here is an example of a well-structured analysis plan:
""" + "\n".join([f"- **{name}** to analyze and provide findings based on their specialized focus area." for name in agent_names]) + """
- **MagenticManager** to consolidate findings from all agents and prepare the final comprehensive analysis.
"""

    final_append = """
DO NOT EVER OFFER TO HELP FURTHER IN THE FINAL ANSWER! Just provide the final answer and end with a polite closing.
"""

    # Wrap chat client in a ChatAgent for the manager (new v2 API requirement)
    manager_agent = ChatAgent(
        chat_client=manager_chat_client,
        name="MagenticManager",
        default_options={"store": False},
    )

    # Choose manager class based on approval requirement
    manager_class = HumanApprovalManager if require_approval else StandardMagenticManager

    manager_kwargs = {
        "task_ledger_plan_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append,
        "task_ledger_plan_update_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append,
        "final_answer_prompt": ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append,
        "max_round_count": max_round_count,
    }

    if require_approval:
        manager_kwargs["require_approval"] = True
        manager_kwargs["max_rounds"] = max_round_count

    # New v2 API: pass agent as first positional argument
    manager = manager_class(manager_agent, **manager_kwargs)

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
    # New v2 API: participants() accepts a list; with_manager() replaces with_standard_manager()
    participant_list = list(agents.values())
    workflow = (
        MagenticBuilder()
        .participants(participant_list)
        .with_manager(
            manager=manager,
            max_round_count=20,
            max_stall_count=0,
        )
        .with_checkpointing(storage)
        .build()
    )
    return workflow


def _extract_response_text(data) -> str:
    """
    Extract text content from various agent_framework response types.
    Matches v4 backend orchestration_manager.py pattern.

    Handles:
    - ChatMessage: Extract .text
    - AgentResponse: Extract .text
    - AgentExecutorResponse: Extract from agent_response.text or full_conversation[-1].text
    - List of any of the above
    """
    if data is None:
        return ""

    # Direct ChatMessage
    if isinstance(data, ChatMessage):
        return data.text or ""

    # Has .text attribute directly (AgentResponse, etc.)
    if hasattr(data, "text") and data.text:
        return data.text

    # AgentExecutorResponse - has agent_response and full_conversation
    if hasattr(data, "agent_response"):
        agent_resp = data.agent_response
        if agent_resp and hasattr(agent_resp, "text") and agent_resp.text:
            return agent_resp.text
        if hasattr(data, "full_conversation") and data.full_conversation:
            last_msg = data.full_conversation[-1]
            if isinstance(last_msg, ChatMessage) and last_msg.text:
                return last_msg.text

    # List of items
    if isinstance(data, list) and len(data) > 0:
        texts = []
        for item in data:
            item_text = _extract_response_text(item)
            if item_text:
                texts.append(item_text)
        if texts:
            return texts[-1]

    return ""


async def run_workflow_with_streaming(workflow, task: str) -> str:
    """
    Execute a workflow with streaming output and return the final result.
    Uses v4 backend event types: MagenticOrchestratorEvent, AgentRunUpdateEvent,
    GroupChatRequestSentEvent, GroupChatResponseReceivedEvent, ExecutorCompletedEvent.

    Args:
        workflow: The Magentic workflow to execute
        task: The task description to process

    Returns:
        The final output text from the workflow
    """
    print(f"\nTask: {task}")
    print("\nStarting workflow execution...")

    last_message_id: str | None = None
    final_output: str | None = None
    agent_call_counts: dict = {}

    # Clear per-executor state to avoid cross-run bleed (matching v4 backend pattern)
    executors = getattr(workflow, "executors", {})
    for exec_key, executor in executors.items():
        try:
            if exec_key == "magentic_orchestrator":
                if hasattr(executor, "_conversation"):
                    conv = getattr(executor, "_conversation")
                    if hasattr(conv, "clear") and callable(conv.clear):
                        conv.clear()
                    elif isinstance(conv, list):
                        conv[:] = []
            else:
                if hasattr(executor, "_chat_history"):
                    hist = getattr(executor, "_chat_history")
                    if hasattr(hist, "clear") and callable(hist.clear):
                        hist.clear()
                    elif isinstance(hist, list):
                        hist[:] = []
        except Exception as e:
            logger.warning("Failed clearing state for executor %s: %s", exec_key, e)

    async for event in workflow.run_stream(task):
        try:

            # Handle orchestrator events (plan, progress ledger)
            if isinstance(event, MagenticOrchestratorEvent):
                logger.info("[Magentic Orchestrator Event] Type: %s", event.event_type.name)
                if isinstance(event.data, ChatMessage):
                    message_text = event.data.text[:200] if event.data.text else ""
                    print(f"\n[Orchestrator] {message_text}", flush=True)
                elif isinstance(event.data, MagenticProgressLedger):
                    logger.info("Progress ledger received")

            # Handle agent streaming/updates
            elif isinstance(event, AgentRunUpdateEvent):
                message_id = getattr(event.data, 'message_id', None) if event.data else None
                executor_id = event.executor_id

                if message_id and message_id != last_message_id:
                    if last_message_id is not None:
                        print("\n")
                    print(f"\n[{executor_id}]: ", end="", flush=True)
                    last_message_id = message_id

                if event.data:
                    data_text = getattr(event.data, 'text', str(event.data))
                    if data_text:
                        print(data_text, end="", flush=True)

            # Handle group chat request sent (agent about to be called)
            elif isinstance(event, GroupChatRequestSentEvent):
                agent_name = event.participant_name
                agent_call_counts[agent_name] = agent_call_counts.get(agent_name, 0) + 1
                call_num = agent_call_counts[agent_name]

                print(f"\n\n[REQUEST → {agent_name}] (round {event.round_index}, call #{call_num})", flush=True)

                if call_num > 1:
                    logger.warning("Agent '%s' called %d times", agent_name, call_num)

            # Handle group chat response received (agent finished)
            elif isinstance(event, GroupChatResponseReceivedEvent):
                agent_name = event.participant_name
                print(f"\n[RESPONSE ← {agent_name}] (round {event.round_index})", flush=True)

                if event.data:
                    response_text = _extract_response_text(event.data)
                    if response_text:
                        # Print a summary (full text can be very long)
                        summary = response_text[:500] + "..." if len(response_text) > 500 else response_text
                        print(f"  Response ({len(response_text)} chars): {summary}", flush=True)

            # Handle executor completed
            elif isinstance(event, ExecutorCompletedEvent):
                logger.debug("[EXECUTOR COMPLETED] agent: %s", event.executor_id)

            # Handle workflow output event (captures final result)
            elif isinstance(event, WorkflowOutputEvent):
                output_data = event.data
                if isinstance(output_data, ChatMessage):
                    final_output = output_data.text or ""
                elif isinstance(output_data, list):
                    texts = []
                    for item in output_data:
                        if isinstance(item, ChatMessage):
                            if item.text:
                                texts.append(item.text)
                        else:
                            texts.append(str(item))
                    final_output = "\n".join(texts)
                elif hasattr(output_data, "text"):
                    final_output = output_data.text or ""
                else:
                    final_output = str(output_data) if output_data else ""

        except Exception as e:
            logger.error("Error processing event %s: %s", type(event).__name__, e, exc_info=True)

    final_text = final_output if final_output else ""

    # Log agent call summary
    if agent_call_counts:
        print(f"\n\nAgent call summary: {agent_call_counts}")

    print("\nWorkflow completed!")
    print(f"Final result length: {len(final_text)} chars")

    return final_text


async def cleanup_agents(
    clients: AzureClients,
    agents: list[ChatAgent],
    manager_chat_client: AzureAIClient | None = None,
):
    """
    Clean up Azure agents and close all clients.

    Args:
        clients: AzureClients container
        agents: List of ChatAgent instances to clean up
        manager_chat_client: Optional manager chat client to close
    """
    print("\n\nCleaning up Azure agents...")

    # Close AzureAIClient chat clients for all agents
    for agent in agents:
        try:
            if hasattr(agent, 'chat_client') and hasattr(agent.chat_client, 'close'):
                await agent.chat_client.close()
                logger.info("Closed chat client for: %s", agent.name)
        except Exception as e:
            logger.warning("Failed to close chat client for %s: %s", agent.name, e)

    # Close manager AzureAIClient
    if manager_chat_client:
        try:
            if hasattr(manager_chat_client, 'close'):
                await manager_chat_client.close()
                logger.info("Closed manager chat client")
        except Exception as e:
            logger.warning("Failed to close manager chat client: %s", e)

    # Delete server-side agents via project_client.agents (v2 API: delete by agent_name)
    for agent in agents:
        try:
            await clients.project_client.agents.delete(agent_name=agent.name)
            logger.info("Deleted Azure agent: %s", agent.name)
        except Exception as e:
            logger.warning("Failed to delete agent %s: %s", agent.name, e)

    # Close Azure clients
    await clients.close()
    print("✓ Cleanup completed")
