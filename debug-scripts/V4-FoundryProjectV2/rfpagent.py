# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from dotenv import load_dotenv

from agent_utils import (
    AgentConfig,
    get_azure_clients,
    create_agent_with_search,
    create_magentic_manager,
    build_workflow,
    run_workflow_with_streaming,
    cleanup_agents,
)

load_dotenv()

"""
Sample: RFP Analysis with Magentic Orchestration (multi-agent)

What it does:
- Orchestrates multiple specialized agents for RFP (Request for Proposal) analysis
  using `MagenticBuilder` with streaming callbacks.

- RfpSummaryAgent: Summarizes RFP and contract documents into structured overviews
- RfpRiskAgent: Identifies and assesses potential risks (legal, financial, operational, technical)
- RfpComplianceAgent: Evaluates compliance with internal policies and regulatory standards

The workflow is configured with:
- A Standard Magentic manager (uses a chat client for planning and progress).
- Azure AI Search (RAG) integration for document knowledge retrieval.
- Human approval step before plan execution.

Prerequisites:
- Azure AI Project configuration with Azure AI Search indexes for RFP data
- Environment variables for Azure AI Project endpoint and credentials
- Indexes: macae-rfp-summary-index, macae-rfp-risk-index, macae-rfp-compliance-index

Usage:
  python rfpagent_refactored.py   # Runs with human approval
"""

# Agent configurations for RFP scenario
RFP_AGENTS = [
    AgentConfig(
        name="RfpSummaryAgent-local",
        description="Summarizes RFP and contract documents into structured, easy-to-understand overviews.",
        instructions=(
            "You are the Summary Agent. Your role is to read and synthesize RFP or proposal documents "
            "into clear, structured executive summaries. Focus on key clauses, deliverables, evaluation "
            "criteria, pricing terms, timelines, and obligations. Organize your output into sections such "
            "as Overview, Key Clauses, Deliverables, Terms, and Notable Conditions. Highlight unique or "
            "high-impact items that other agents (Risk or Compliance) should review. Be concise, factual, "
            "and neutral in tone."
        ),
        index_name="macae-rfp-summary-index",
    ),
    AgentConfig(
        name="RfpRiskAgent-local",
        description="Analyzes the dataset for risks such as delivery, financial, operational, and compliance-related vulnerabilities.",
        instructions=(
            "You are the Risk Agent. Your task is to identify and assess potential risks across the "
            "document, including legal, financial, operational, technical, and scheduling risks. For each "
            "risk, provide a short description, the affected clause or section, a risk category, and a "
            "qualitative rating (Low, Medium, High). Focus on material issues that could impact delivery, "
            "compliance, or business exposure. Summarize findings clearly to support decision-making and "
            "escalation."
        ),
        index_name="macae-rfp-risk-index",
    ),
    AgentConfig(
        name="RfpComplianceAgent-local",
        description="Checks for compliance gaps against regulations, policies, and standard contracting practices.",
        instructions=(
            "You are the Compliance Agent. Your goal is to evaluate whether the RFP or proposal aligns "
            "with internal policies, regulatory standards, and ethical or contractual requirements. "
            "Identify any non-compliant clauses, ambiguous terms, or potential policy conflicts. For each "
            "issue, specify the related policy area (e.g., data privacy, labor, financial controls) and "
            "classify it as Mandatory or Recommended for review. Maintain a professional, objective tone "
            "and emphasize actionable compliance insights."
        ),
        index_name="macae-rfp-compliance-index",
    ),
]


async def main() -> None:
    # Initialize Azure clients
    clients = get_azure_clients()

    print("\nCreating RFP Analysis Agents with Azure AI Search...")

    # Create all agents
    agents = []
    for config in RFP_AGENTS:
        agent = await create_agent_with_search(clients, config)
        agents.append(agent)
        print(f"  ✓ Created {config.name}")

    print("✓ All agents created successfully with Azure AI Search integration")

    # Build agent dictionary for workflow
    agent_dict = {agent.name.replace("-local", ""): agent for agent in agents}
    agent_names = list(agent_dict.keys())

    try:
        # Create orchestration manager
        orchestrator_model = os.environ.get("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
        manager, manager_chat_client = create_magentic_manager(
            clients=clients,
            team_name="RFPTeam-local",
            agent_names=agent_names,
            model=orchestrator_model,
            require_approval=True,  # Human approval enabled by default
        )

        print("\nBuilding RFP Analysis Magentic Workflow...")
        print(f"Configured {len(agent_dict)} participants: {agent_names}")

        # Build workflow
        workflow = build_workflow(agent_dict, manager)

        # Define task - from the rfp_analysis_team.json starting_tasks
        task = "I would like to review the Woodgrove Bank RFP response from Contoso"

        # Run workflow with streaming
        final_output = await run_workflow_with_streaming(workflow, task)

        print("\nFinal Output:")
        print(final_output)

    finally:
        await cleanup_agents(clients, agents, manager_chat_client)


if __name__ == "__main__":
    asyncio.run(main())
