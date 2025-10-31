"""Agent template for building Foundry agents with Azure AI Search, optional MCP tool, and Code Interpreter (agent_framework version)."""

import logging
from typing import List, Optional

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Role,
    HostedCodeInterpreterTool,
)
from azure.ai.projects.models import ConnectionType
from agent_framework_azure_ai import AzureAIAgentClient  # Provided by agent_framework


from v4.magentic_agents.common.lifecycle import AzureAgentBase
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v4.config.agent_registry import agent_registry


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
        model_deployment_name: str,
        enable_code_interpreter: bool = False,
        mcp_config: MCPConfig | None = None,
        search_config: SearchConfig | None = None,
    ) -> None:
        super().__init__(mcp=mcp_config, model_deployment_name=model_deployment_name)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.enable_code_interpreter = enable_code_interpreter
        self.search = search_config
        self.logger = logging.getLogger(__name__)

        # Decide early whether Azure Search mode should be activated
        self._use_azure_search = self._is_azure_search_requested()

        # Placeholder for server-created Azure AI agent id (if Azure Search path)
        self._azure_server_agent_id: Optional[str] = None

    # -------------------------
    # Mode detection
    # -------------------------
    def _is_azure_search_requested(self) -> bool:
        """Determine if Azure AI Search raw tool path should be used."""
        if not self.search:
            return False
        # Minimal heuristic: presence of required attributes

        has_index = hasattr(self.search, "index_name") and bool(self.search.index_name)
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
    async def _create_azure_search_enabled_client(self):
        """
        Create a server-side Azure AI agent with raw Azure AI Search tool and return an AzureAIAgentClient.
        This mirrors your example while fitting existing lifecycle.

        If these assumptions differ, adjust accordingly.
        """

        connection_id = getattr(self.search, "connection_name", "")
        index_name = getattr(self.search, "index_name", "")
        query_type = getattr(self.search, "search_query_type", "vector")
        
        # ai_search_conn_id = ""
        # async for connection in self.client.project_client.connections.list():
        #     if connection.type == ConnectionType.AZURE_AI_SEARCH:
        #         ai_search_conn_id = connection.id
        #         break
        if not connection_id or not index_name:
            self.logger.error(
                "Missing azure_search_connection_id or azure_search_index_name in search_config; aborting Azure Search path."
            )
            return None

        try:
            azure_agent = await self.client.project_client.agents.create_agent(
                model=self.model_deployment_name,
                name=self.agent_name,
                instructions=(
                    f"{self.agent_instructions} "
                    "Always use the Azure AI Search tool and configured index for knowledge retrieval."
                ),
                tools=[{"type": "azure_ai_search"}],
                tool_resources={
                    "azure_ai_search": {
                        "indexes": [
                            {
                                "index_connection_id": connection_id,
                                "index_name": index_name,
                                "query_type": query_type,
                            }
                        ]
                    }
                },
            )
            self._azure_server_agent_id = azure_agent.id
            self.logger.info(
                "Created Azure server agent with Azure AI Search tool (agent_id=%s, index=%s).",
                azure_agent.id,
                index_name,
            )

            chat_client = AzureAIAgentClient(
                project_client=self.client.project_client,
                agent_id=azure_agent.id,
            )
            return chat_client
        except Exception as ex:
            self.logger.error("Failed to create Azure Search enabled agent: %s", ex)
            return None

    # -------------------------
    # Agent lifecycle override
    # -------------------------
    async def _after_open(self) -> None:
        """Initialize ChatAgent after connections are established."""
        try:
            if self._use_azure_search:
                # Azure Search mode (skip MCP + Code Interpreter due to incompatibility)
                self.logger.info("Initializing agent in Azure AI Search mode (exclusive).")
                chat_client = await self._create_azure_search_enabled_client()
                if not chat_client:
                    raise RuntimeError("Azure AI Search mode requested but setup failed.")

                # In Azure Search raw tool path, tools/tool_choice are handled server-side.
                self._agent = ChatAgent(
                    chat_client=chat_client,
                    instructions=self.agent_instructions,
                    name=self.agent_name,
                    description=self.agent_description,
                    tool_choice="required",  # Force usage
                    temperature=0.7,
                    model_id=self.model_deployment_name,
                )
            else:
                # use MCP path
                self.logger.info("Initializing agent in MCP mode.")
                tools = await self._collect_tools()
                self._agent = ChatAgent(
                    chat_client=self.client,
                    instructions=self.agent_instructions,
                    name=self.agent_name,
                    description=self.agent_description,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else "none",
                    temperature=0.7,
                    model_id=self.model_deployment_name,
                )

            self.logger.info("Initialized ChatAgent '%s'", self.agent_name)
        except Exception as ex:
            self.logger.error("Failed to initialize ChatAgent: %s", ex)
            raise

        # Register agent globally
        try:
            agent_registry.register_agent(self)
            self.logger.info("Registered agent '%s' in global registry.", self.agent_name)
        except Exception as reg_ex:
            self.logger.warning("Could not register agent '%s': %s", self.agent_name, reg_ex)

    # -------------------------
    # Invocation (streaming)
    # -------------------------
    async def invoke(self, prompt: str):
        """Stream model output for a prompt."""
        if not self._agent:
            raise RuntimeError("Agent not initialized; call open() first.")

        messages = [ChatMessage(role=Role.USER, text=prompt)]

        async for update in self._agent.run_stream(messages=messages):
            yield update

    # -------------------------
    # Cleanup (optional override if you want to delete server-side agent)
    # -------------------------
    async def close(self) -> None:
        """Extend base close to optionally delete server-side Azure agent."""
        try:
            if self._use_azure_search and self._azure_server_agent_id and hasattr(self, "project_client"):
                try:
                    await self.project_client.agents.delete_agent(self._azure_server_agent_id)
                    self.logger.info(
                        "Deleted Azure server agent (id=%s) during close.", self._azure_server_agent_id
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
async def create_foundry_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    mcp_config: MCPConfig | None,
    search_config: SearchConfig | None,
) -> FoundryAgentTemplate:
    """Factory to create and open a FoundryAgentTemplate."""
    agent = FoundryAgentTemplate(
        agent_name=agent_name,
        agent_description=agent_description,
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        enable_code_interpreter=True,
        mcp_config=mcp_config,
        search_config=search_config,
    )
    await agent.open()
    return agent