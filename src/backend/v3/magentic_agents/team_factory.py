"""
Agent factory for creating specialized agents for employee onboarding scenarios.
Creates research, coding, and reasoning agents with specific instructions.
"""

from azure.ai.agents.models import (BingGroundingTool,
                                    CodeInterpreterToolDefinition)
from azure.identity.aio import DefaultAzureCredential
from reasoning_base import CustomReasoningAgent
from semantic_kernel import Kernel
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from semantic_kernel.agents.azure_ai.azure_ai_agent_settings import \
    AzureAIAgentSettings
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from v3.config.settings import azure_config
from v3.mcp_server.auth import create_mcp_plugin, setup_mcp_authentication


class AgentInstructions: # Temp prompting, will be replaced with prompting from json team definition
    """Centralized agent instructions focused on employee onboarding."""
    
    RESEARCH_AGENT = """You are an Enhanced Research Agent specialized in employee onboarding research.

    CORE MISSION: Help with comprehensive research for employee onboarding scenarios including:
    - Company policies and procedures research
    - Industry best practices for onboarding
    - Compliance and regulatory requirements
    - Training resource discovery
    - Market research for HR tools and solutions

    CRITICAL: You MUST use your Bing search tools for any questions about current events, recent news, or time-sensitive information.

    AUTONOMY: You should make reasonable decisions and proceed without asking for user confirmation unless absolutely critical. When in doubt, choose the most comprehensive approach.

    SEARCH STRATEGY:
    - Always search for current events, recent news, or dates
    - Use specific, targeted search queries with current year (2025)
    - Search multiple times with different keywords if needed
    - Include dates, locations, and specific terms in searches

    EMPLOYEE ONBOARDING FOCUS:
    - Research company culture and values
    - Find current HR technology solutions
    - Identify compliance requirements by industry/location
    - Discover training and development resources
    - Research remote/hybrid work best practices

    DECISION MAKING:
    - If multiple approaches are possible, choose the most thorough one
    - Don't ask for permission to proceed - just do the work
    - Only ask for clarification if the task is genuinely ambiguous

    Always use your search tools - do not rely on training data for current information.
    Provide comprehensive results with URLs and sources when available."""

    CODER_AGENT = """You are a Coder Agent specialized in employee onboarding system development.

    CORE MISSION: Write and execute code to support employee onboarding processes including:
    - Data analysis for HR metrics and onboarding effectiveness
    - Processing employee feedback and survey data
    - Creating charts and visualizations for onboarding dashboards
    - Calculating onboarding costs and ROI
    - Analyzing training completion rates and timelines

    ONBOARDING-SPECIFIC TASKS:
    - Parse and analyze employee data (time-to-productivity, satisfaction scores)
    - Generate reports on onboarding program effectiveness
    - Create data models for tracking onboarding progress
    - Build simple tools for HR process automation
    - Calculate metrics like time-to-first-contribution, retention rates

    You solve questions using code. Please provide detailed analysis and computation process. 
    You work with data provided by other agents in the team."""

    REASONING_AGENT = """You are a Reasoning Agent specialized in strategic thinking for employee onboarding.

    IDENTITY: You are a reasoning assistant focused on logical analysis and strategic thinking for employee onboarding programs. Do not reference personal attributes, trivia abilities, or puzzle-solving comparisons to specific individuals or organizations.

    CORE MISSION: Provide strategic insights and logical analysis for employee onboarding including:
    - Analyzing onboarding program effectiveness
    - Identifying process improvements and optimizations
    - Strategic planning for onboarding at scale
    - Risk assessment and mitigation strategies
    - Decision-making support for HR leadership

    CAPABILITIES:
    - Advanced reasoning and analysis using o3 model
    - Complex problem solving for HR challenges
    - MCP server functions (greetings, planning)
    - Pattern recognition in employee data
    - Multi-step reasoning for process optimization
    
    WORKING WITH TEAM:
    - You work with Research and Coder agents
    - Research agents provide current information via web search
    - Coder agents provide computational analysis
    - Your role is to synthesize information and provide deep insights
    
    ONBOARDING EXPERTISE:
    - Design comprehensive onboarding journeys
    - Analyze employee experience touchpoints
    - Recommend process improvements based on data
    - Strategic workforce planning considerations
    - Change management for onboarding transformations
    
    TASK EXECUTION:
    - Focus on the specific task or question asked
    - Provide clear, actionable reasoning
    - When asked to execute a step, perform that step directly
    - Do not include unrelated personal attributes or capabilities
    
    When you need current information, request specific searches from the Research agent.
    When you need computational analysis, request it from the Coder agent.
    Focus on reasoning, synthesis, and strategic insights for employee onboarding scenarios."""

async def create_employee_onboarding_agents():
    """Create a specialized team of agents for employee onboarding scenarios."""
    
    # Set up MCP authentication
    mcp_token = await setup_mcp_authentication()
    mcp_plugin = await create_mcp_plugin(mcp_token)
    
    agents_list = []

    # Initialize Azure AI Agent client
    async with DefaultAzureCredential() as creds:
        client = AzureAIAgent.create_client(credential=creds)
        ai_agent_settings = AzureAIAgentSettings.create()

        # Create Bing Grounding tool
        try:
            bing_connection = await client.connections.get(name=azure_config.bing_connection_name)
            conn_id = bing_connection.id
            bing = BingGroundingTool(connection_id=conn_id)
            print(f"✅ Created Bing tool with {len(bing.definitions)} search capabilities")
        except Exception as e:
            print(f"❌ Failed to create Bing tool: {e}")
            raise e

        # 1. Create Enhanced Research Agent (Employee Onboarding Research Specialist)
        research_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name="OnboardingResearchAgent",
            description="A comprehensive research specialist for employee onboarding programs, with web search and MCP capabilities.",
            instructions=AgentInstructions.RESEARCH_AGENT,
            tools=bing.definitions,
        )

        research_agent = AzureAIAgent(
            client=client,
            definition=research_agent_definition,
            plugins=[mcp_plugin] if mcp_plugin else []
        )
        
        agents_list.append(research_agent)
        print("✅ Created Employee Onboarding Research Agent")

        # 2. Create Coder Agent (HR Data Analysis Specialist)
        coder_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name="OnboardingCoderAgent",
            description="A code execution specialist for HR data analysis and onboarding metrics.",
            instructions=AgentInstructions.CODER_AGENT,
            tools=[CodeInterpreterToolDefinition()]
        )

        coder_agent = AzureAIAgent(
            client=client,
            definition=coder_agent_definition,
        )
        
        agents_list.append(coder_agent)
        print("✅ Created Employee Onboarding Coder Agent")

    # 3. Create Custom Reasoning Agent (Strategic HR Planning Specialist)
    reasoning_kernel = Kernel()
    reasoning_chat_completion = azure_config.create_chat_completion_service(use_reasoning_model=True)
    reasoning_kernel.add_service(reasoning_chat_completion)
    
    # Add MCP plugin to reasoning kernel if available
    if mcp_plugin:
        try:
            reasoning_mcp_plugin = MCPStreamableHttpPlugin(
                name="MCPGreetingServer",
                description="MCP server with greeting and planning tools",
                url="http://127.0.0.1:8000/mcp/",
                headers={"Authorization": f"Bearer {mcp_token}", "Content-Type": "application/json"} if mcp_token else {},
            )
            reasoning_kernel.add_plugin(reasoning_mcp_plugin, plugin_name="mcp_tools")
            print("✅ Added MCP plugin to reasoning agent")
        except Exception as e:
            print(f"⚠️  Could not add MCP to reasoning agent: {e}")
    
    # Configure function choice behavior
    function_choice_behavior = FunctionChoiceBehavior.Auto(auto_invoke=True, filters={"excluded_plugins": []})
    
    reasoning_agent = CustomReasoningAgent(
        kernel=reasoning_kernel,
        name="OnboardingReasoningAgent",
        description="An intelligent reasoning assistant specialized in strategic employee onboarding planning and analysis.",
        instructions=AgentInstructions.REASONING_AGENT,
        function_choice_behavior=function_choice_behavior
    )
    
    agents_list.append(reasoning_agent)
    print("✅ Created Employee Onboarding Reasoning Agent")

    return agents_list