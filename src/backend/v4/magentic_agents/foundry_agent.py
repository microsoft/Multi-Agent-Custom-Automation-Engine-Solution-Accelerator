"""Agent template for building Foundry agents with Azure AI Search, optional MCP tool, and Code Interpreter (agent_framework version)."""

import logging
from typing import List, Optional

from agent_framework import (ChatAgent, ChatMessage, HostedCodeInterpreterTool,
                             Role)
from agent_framework_azure_ai import \
    AzureAIClient  # Provided by agent_framework
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
)
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_af import TeamConfiguration
from v4.common.services.team_service import TeamService
from v4.config.agent_registry import agent_registry
from v4.magentic_agents.common.lifecycle import AzureAgentBase
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig


class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search (raw tool) OR MCP tool + optional Code Interpreter.

    Priority:
      1. Azure AI Search (if search_config contains required Azure Search fields)
      2. MCP tool (legacy path)
    Code Interpreter is only attached on the MCP path (unless you want it also with Azure Search—currently skipped for incompatibility per request).
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        use_reasoning: bool,
        model_deployment_name: str,
        project_endpoint: str,
        enable_code_interpreter: bool = False,
        mcp_config: MCPConfig | None = None,
        search_config: SearchConfig | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
    ) -> None:
        # Get project_client before calling super().__init__
        project_client = config.get_ai_project_client()

        super().__init__(
            mcp=mcp_config,
            model_deployment_name=model_deployment_name,
            project_endpoint=project_endpoint,
            team_service=team_service,
            team_config=team_config,
            memory_store=memory_store,
            agent_name=agent_name,
            agent_description=agent_description,
            agent_instructions=agent_instructions,
            project_client=project_client,
        )

        self.enable_code_interpreter = enable_code_interpreter
        self.search = search_config
        self.logger = logging.getLogger(__name__)

        # Decide early whether Azure Search mode should be activated
        self._use_azure_search = self._is_azure_search_requested()
        self.use_reasoning = use_reasoning

        # Placeholder for server-created Azure AI agent id/version (if Azure Search path)
        self._azure_server_agent_id: Optional[str] = None
        self._azure_server_agent_version: Optional[str] = None

    # -------------------------
    # Mode detection
    # -------------------------
    def _is_azure_search_requested(self) -> bool:
        """Determine if Azure AI Search raw tool path should be used."""
        print(f"[DEBUG _is_azure_search_requested] Agent={self.agent_name}, search={self.search}")
        if not self.search:
            print(f"[DEBUG _is_azure_search_requested] Agent={self.agent_name}: No search config, returning False")
            return False
        # Minimal heuristic: presence of required attributes

        has_index = hasattr(self.search, "index_name") and bool(self.search.index_name)
        print(f"[DEBUG _is_azure_search_requested] Agent={self.agent_name}: has_index={has_index}, index_name={getattr(self.search, 'index_name', None)}")
        if has_index:
            self.logger.info(
                "Azure AI Search requested (connection_id=%s, index=%s).",
                getattr(self.search, "connection_name", None),
                getattr(self.search, "index_name", None),
            )
            return True
        return False

    async def _collect_tools(self) -> List:
        """Collect tool definitions for ChatAgent (MCP path only)."""
        tools: List = []

        # Code Interpreter (only in MCP path per incompatibility note)
        if self.enable_code_interpreter:
            try:
                code_tool = HostedCodeInterpreterTool()
                tools.append(code_tool)
                self.logger.info("Added Code Interpreter tool.")
            except Exception as ie:
                self.logger.error("Code Interpreter tool creation failed: %s", ie)

        # MCP Tool (from base class)
        if self.mcp_tool:
            tools.append(self.mcp_tool)
            self.logger.info("Added MCP tool: %s", self.mcp_tool.name)

        self.logger.info("Total tools collected (MCP path): %d", len(tools))
        return tools

    # -------------------------
    # Azure Search helper
    # -------------------------
    async def _create_azure_search_enabled_client(self, chatClient=None) -> Optional[AzureAIClient]:
        """
        Create a server-side Azure AI agent with Azure AI Search tool using create_version.

        This uses the AIProjectClient.agents.create_version() approach with:
        - PromptAgentDefinition for agent configuration
        - AzureAISearchAgentTool with AzureAISearchToolResource for search capability
        - AISearchIndexResource for index configuration with project_connection_id

        Requirements:
          - An Azure AI Project Connection for Azure AI Search
          - search_config.index_name must exist in the Search service.
          - search_config.connection_name should match the AI Project connection name

        Returns:
            AzureAIClient | None
        """
        print(f"[DEBUG _create_azure_search_enabled_client] Agent={self.agent_name}, chatClient={chatClient}, search_config={self.search}")
        if chatClient:
            self.logger.info("Reusing existing chatClient for agent '%s' (already has Azure Search configured)", self.agent_name)
            return chatClient

        if not self.search:
            self.logger.error("Search configuration missing.")
            return None

        # Get connection name - this is used as project_connection_id in create_version
        connection_name = getattr(self.search, "connection_name", None)
        if not connection_name:
            # Fallback to environment variable
            connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME
            self.logger.info("Using connection_name from environment: %s", connection_name)

        index_name = getattr(self.search, "index_name", "")
        query_type = getattr(self.search, "search_query_type", "simple")
        top_k = getattr(self.search, "top_k", 5)

        if not index_name:
            self.logger.error(
                "index_name not provided in search_config; aborting Azure Search path."
            )
            return None

        if not connection_name:
            self.logger.error(
                "connection_name not provided; aborting Azure Search path."
            )
            return None

        self.logger.info(
            "Creating Azure AI Search agent with create_version: connection_name=%s, index=%s, query_type=%s, top_k=%s",
            connection_name,
            index_name,
            query_type,
            top_k,
        )

        # Create agent using create_version with PromptAgentDefinition and AzureAISearchAgentTool
        # This approach matches the Knowledge Mining Solution Accelerator pattern
        try:
            enhanced_instructions = (
                f"{self.agent_instructions} "
                "Always use the Azure AI Search tool and configured index for knowledge retrieval."
            )
            
            print(f"[AGENT CREATE] 🆕 Creating agent in Foundry: '{self.agent_name}'", flush=True)
            print(f"[AGENT CREATE] Model: {self.model_deployment_name}", flush=True)
            print(f"[AGENT CREATE] Search: connection={connection_name}, index={index_name}", flush=True)

            azure_agent = await self.project_client.agents.create_version(
                agent_name=self.agent_name,  # Use original name
                definition=PromptAgentDefinition(
                    model=self.model_deployment_name,
                    instructions=enhanced_instructions,
                    tools=[
                        AzureAISearchAgentTool(
                            azure_ai_search=AzureAISearchToolResource(
                                indexes=[
                                    AISearchIndexResource(
                                        project_connection_id=connection_name,
                                        index_name=index_name,
                                        query_type=query_type,
                                        top_k=top_k,
                                    )
                                ]
                            )
                        )
                    ],
                ),
            )

            self._azure_server_agent_id = azure_agent.id
            self._azure_server_agent_version = azure_agent.version
            print(f"[AGENT CREATE] ✅ Created agent: name={azure_agent.name}, id={azure_agent.id}, version={azure_agent.version}", flush=True)
            self.logger.info(
                "Created Azure AI Search agent via create_version (name=%s, id=%s, version=%s).",
                azure_agent.name,
                azure_agent.id,
                azure_agent.version,
            )

            # Wrap in AzureAIClient using agent_name and agent_version (NOT agent_id)
            # Include model_deployment_name to ensure SDK has model info for streaming
            deployment_name = self.model_deployment_name or config.AZURE_OPENAI_DEPLOYMENT_NAME
            chat_client = AzureAIClient(
                project_endpoint=self.project_endpoint,
                agent_name=azure_agent.name,
                agent_version=azure_agent.version,  # Use the specific version we just created
                model_deployment_name=deployment_name,
                credential=self.creds,
            )
            return chat_client

        except Exception as ex:
            self.logger.error(
                "Failed to create Azure Search enabled agent via create_version (connection=%s, index=%s): %s",
                connection_name,
                index_name,
                ex,
            )
            import traceback
            traceback.print_exc()
            return None

    # -------------------------
    # Agent lifecycle override
    # -------------------------
    async def _after_open(self) -> None:
        """Initialize ChatAgent after connections are established."""
        if self.use_reasoning:
            self.logger.info("Initializing agent in Reasoning mode.")
            temp = None
        else:
            self.logger.info("Initializing agent in Foundry mode.")
            temp = 0.1

        try:
            chatClient = await self.get_database_team_agent()
            print(f"[DEBUG _after_open] Agent={self.agent_name}, _use_azure_search={self._use_azure_search}, search_config={self.search}, chatClient={chatClient}")

            if self._use_azure_search:
                # Azure Search mode (skip MCP + Code Interpreter due to incompatibility)
                self.logger.info(
                    "Initializing agent '%s' in Azure AI Search mode (exclusive) with index=%s.",
                    self.agent_name,
                    getattr(self.search, "index_name", "N/A") if self.search else "N/A"
                )
                print(f"[DEBUG _after_open] Creating Azure Search client for {self.agent_name}")
                chat_client = await self._create_azure_search_enabled_client(chatClient)
                if not chat_client:
                    raise RuntimeError(
                        "Azure AI Search mode requested but setup failed."
                    )

                # In Azure Search raw tool path, tools/tool_choice are handled server-side.
                self._agent = ChatAgent(
                    id=self.get_agent_id(chat_client),
                    chat_client=self.get_chat_client(chat_client),
                    instructions=self.agent_instructions,
                    name=self.agent_name,
                    description=self.agent_description,
                    tool_choice="required",  # Force usage
                    temperature=temp,
                    model_id=self.model_deployment_name,
                )
            else:
                # use MCP path
                self.logger.info("Initializing agent in MCP mode.")
                tools = await self._collect_tools()
                self._agent = ChatAgent(
                    id=self.get_agent_id(chatClient),
                    chat_client=self.get_chat_client(chatClient),
                    instructions=self.agent_instructions,
                    name=self.agent_name,
                    description=self.agent_description,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else "none",
                    temperature=temp,
                    model_id=self.model_deployment_name,
                )
            self.logger.info("Initialized ChatAgent '%s'", self.agent_name)

        except Exception as ex:
            self.logger.error("Failed to initialize ChatAgent: %s", ex)
            raise

        # Register agent globally
        try:
            agent_registry.register_agent(self)
            self.logger.info(
                "Registered agent '%s' in global registry.", self.agent_name
            )
        except Exception as reg_ex:
            self.logger.warning(
                "Could not register agent '%s': %s", self.agent_name, reg_ex
            )

    # -------------------------
    # Invocation (streaming)
    # -------------------------
    async def invoke(self, prompt: str):
        """Stream model output for a prompt."""
        if not self._agent:
            raise RuntimeError("Agent not initialized; call open() first.")

        messages = [ChatMessage(role=Role.USER, text=prompt)]

        agent_saved = False
        async for update in self._agent.run_stream(messages):
            # Save agent ID only once on first update
            if not agent_saved:
                await self.save_database_team_agent()
                agent_saved = True
            yield update

    # -------------------------
    # Cleanup (optional override if you want to delete server-side agent)
    # -------------------------
    async def close(self) -> None:
        """Extend base close to optionally delete server-side Azure agent."""
        try:
            if (
                self._use_azure_search
                and self._azure_server_agent_id
                and hasattr(self, "project_client")
            ):
                try:
                    await self.project_client.agents.delete_agent(
                        self._azure_server_agent_id
                    )
                    self.logger.info(
                        "Deleted Azure server agent (id=%s) during close.",
                        self._azure_server_agent_id,
                    )
                except Exception as ex:
                    self.logger.warning(
                        "Failed to delete Azure server agent (id=%s): %s",
                        self._azure_server_agent_id,
                        ex,
                    )
        finally:
            await super().close()


# -------------------------
# Factory
# -------------------------
# async def create_foundry_agent(
#     agent_name: str,
#     agent_description: str,
#     agent_instructions: str,
#     model_deployment_name: str,
#     mcp_config: MCPConfig | None,
#     search_config: SearchConfig | None,
# ) -> FoundryAgentTemplate:
#     """Factory to create and open a FoundryAgentTemplate."""
#     agent = FoundryAgentTemplate(
#         agent_name=agent_name,
#         agent_description=agent_description,
#         agent_instructions=agent_instructions,
#         model_deployment_name=model_deployment_name,
#         enable_code_interpreter=True,
#         mcp_config=mcp_config,
#         search_config=search_config,

#     )
#     await agent.open()
#     return agent
