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
Sample: Contract Compliance Analysis with Magentic Orchestration (multi-agent)

What it does:
- Orchestrates multiple specialized agents for NDA/Contract compliance analysis
  using `MagenticBuilder` with streaming callbacks.

- ContractSummaryAgent: Produces comprehensive summaries of NDAs and contracts
- ContractRiskAgent: Identifies and classifies compliance risks using risk framework
- ContractComplianceAgent: Validates contracts against legal policy requirements

The workflow is configured with:
- A Standard Magentic manager (uses a chat client for planning and progress).
- Azure AI Search (RAG) integration for document knowledge retrieval.
- Optional human approval step before plan execution.

Prerequisites:
- Azure AI Project configuration with Azure AI Search indexes for contract data
- Environment variables for Azure AI Project endpoint and credentials
- Indexes: contract-summary-doc-index, contract-risk-doc-index, contract-compliance-doc-index

Usage:
  python contractagent.py   # Runs with human approval (default)
"""

# Agent configurations for Contract Compliance scenario
CONTRACT_AGENTS = [
    AgentConfig(
        name="ContractSummaryAgent-local",
        description="Produces comprehensive, structured summaries of NDAs and contracts, capturing all key terms, clauses, obligations, jurisdictions, and notable provisions.",
        instructions=(
            "You are the Summary Agent for compliance contract analysis. Your task is to produce a clear, "
            "accurate, and structured executive summary of NDA and legal agreement documents. You must "
            "deliver summaries organized into labeled sections including: Overview, Parties, Effective Date, "
            "Purpose, Definition of Confidential Information, Receiving Party Obligations, Term & Termination, "
            "Governing Law, Restrictions & Limitations, Miscellaneous Clauses, Notable or Unusual Terms, and "
            "Key Items for Risk & Compliance Agents. Highlight missing elements such as liability caps, dispute "
            "resolution mechanisms, data handling obligations, or ambiguous language. Maintain a precise, neutral "
            "legal tone. Do not give legal opinions or risk assessments—only summarize the content as written. "
            "Use retrieval results from the search index to ensure completeness and reference contextual "
            "definitions or standard clause expectations when needed."
        ),
        index_name="contract-summary-doc-index",
    ),
    AgentConfig(
        name="ContractRiskAgent-local",
        description="Identifies and classifies compliance risks in NDAs and contracts using the organization's risk framework, and provides suggested edits to reduce exposure.",
        instructions=(
            "You are the Risk Agent for NDA and compliance contract analysis. Use the NDA Risk Assessment "
            "Reference document and retrieved context to identify High, Medium, and Low risk issues. Evaluate "
            "clauses for missing liability caps, ambiguous terms, overly broad confidentiality definitions, "
            "jurisdiction misalignment, missing termination rights, unclear data handling obligations, missing "
            "dispute resolution, and any incomplete or poorly scoped definitions. For every risk you identify, "
            "provide: (1) Risk Category (High/Medium/Low), (2) Clause or Section impacted, (3) Description of "
            "the issue, (4) Why it matters or what exposure it creates, and (5) Suggested edit or corrective "
            "language. Apply the risk scoring framework: High = escalate immediately; Medium = requires revision; "
            "Low = minor issue. Be precise, legally aligned, and practical. Reference retrieved examples or "
            "standards when appropriate. Your output must be structured and actionable."
        ),
        index_name="contract-risk-doc-index",
    ),
    AgentConfig(
        name="ContractComplianceAgent-local",
        description="Performs compliance validation of NDAs and contracts against legal policy requirements, identifies gaps, and provides corrective recommendations and compliance status.",
        instructions=(
            "You are the Compliance Agent responsible for validating NDAs and legal agreements against mandatory "
            "legal and policy requirements. Use the NDA Compliance Reference Document and retrieval results to "
            "evaluate whether the contract includes all required clauses: Confidentiality, Term & Termination, "
            "Governing Law aligned to approved jurisdictions, Non-Assignment, and Entire Agreement. Identify "
            "compliance gaps including ambiguous language, missing liability protections, improper jurisdiction, "
            "excessive term length, insufficient data protection obligations, missing dispute resolution mechanisms, "
            "or export control risks. For each issue provide: (1) Compliance Area (e.g., Term Length, Jurisdiction, "
            "Confidentiality), (2) Status (Pass/Fail), (3) Issue Description, (4) Whether it is Mandatory or "
            "Recommended, (5) Corrective Recommendation or Suggested Language. Deliver a final Compliance Status "
            "summary. Maintain professional, objective, legally accurate tone."
        ),
        index_name="contract-compliance-doc-index",
    ),
]


async def main() -> None:
    # Initialize Azure clients
    clients = get_azure_clients()

    print("\nCreating Contract Compliance Agents with Azure AI Search...")

    # Create all agents
    agents = []
    for config in CONTRACT_AGENTS:
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
            team_name="ContractComplianceTeam-local",
            agent_names=agent_names,
            model=orchestrator_model,
            require_approval=True,  # Human approval enabled by default
        )

        print("\nBuilding Contract Compliance Magentic Workflow...")
        print(f"Configured {len(agent_dict)} participants: {agent_names}")

        # Build workflow
        workflow = build_workflow(agent_dict, manager)

        # Define task - from the contract_compliance_team.json starting_tasks
        task = (
            "Review Contoso's NDA. Provide a summary (parties, date, term, governing law), "
            "assess risks (High/Medium/Low with clause references), audit compliance against "
            "company policy, and suggest edits for any issues."
        )

        # Run workflow with streaming
        final_output = await run_workflow_with_streaming(workflow, task)

        print("\nFinal Output:")
        print(final_output)

    finally:
        await cleanup_agents(clients, agents, manager_chat_client)


if __name__ == "__main__":
    asyncio.run(main())
