import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import (
    ChatMessage,
    ChatOptions,
    ChatResponseUpdate,
    HostedMCPTool,
    Role,
)
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from af.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from af.config.agent_registry import agent_registry


logger = logging.getLogger(__name__)


# -----------------------------
# Lightweight search helper
# -----------------------------
@dataclass
class _SearchContext:
    client: SearchClient
    top_k: int

    def fetch(self, query: str) -> List[str]:
        docs: List[str] = []
        try:
            results = self.client.search(
                search_text=query,
                query_type="simple",
                select=["content"],
                top=self.top_k,
            )
            for r in results:
                try:
                    docs.append(str(r["content"]))
                except Exception:  # noqa: BLE001
                    continue
        except Exception as ex:  # noqa: BLE001
            logger.debug("Search fetch error: %s", ex)
        return docs


class ReasoningAgentTemplate:
    """
    agent_framework-based reasoning agent (replaces SK ChatCompletionAgent).
    Class name preserved for backward compatibility.

    Differences vs original:
      - No Semantic Kernel Kernel / ChatCompletionAgent.
      - Streams agent_framework ChatResponseUpdate objects.
      - Optional inline RAG (search results stuffed into instructions).
      - Optional MCP tool exposure via HostedMCPTool.

    If callers relied on SK's ChatMessageContent objects, add an adapter layer.
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        model_deployment_name: str,
        azure_openai_endpoint: str,                 # kept name for compatibility; now Azure AI Project endpoint
        search_config: SearchConfig | None = None,
        mcp_config: MCPConfig | None = None,
        max_search_docs: int = 3,
    ) -> None:
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.base_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.project_endpoint = azure_openai_endpoint  # reused meaning
        self.search_config = search_config
        self.mcp_config = mcp_config
        self.max_search_docs = max_search_docs

        # Azure + client resources
        self._credential: DefaultAzureCredential | None = None
        self._project_client: AIProjectClient | None = None
        self._client: AzureAIAgentClient | None = None

        # Optional search
        self._search_ctx: _SearchContext | None = None

        self._opened = False

    # ------------- Lifecycle -------------
    async def open(self) -> "ReasoningAgentTemplate":
        if self._opened:
            return self

        self._credential = DefaultAzureCredential()
        self._project_client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=self._credential,
        )

        # Create AzureAIAgentClient (ephemeral agent will be created on first run)
        self._client = AzureAIAgentClient(
            project_client=self._project_client,
            agent_id=None,
            agent_name=self.agent_name,
            model_deployment_name=self.model_deployment_name,
        )

        # Optional search setup
        if self.search_config and all(
            [
                self.search_config.endpoint,
                self.search_config.index_name,
                self.search_config.api_key,
            ]
        ):
            try:
                sc = SearchClient(
                    endpoint=self.search_config.endpoint,
                    index_name=self.search_config.index_name,
                    credential=AzureKeyCredential(self.search_config.api_key),
                )
                self._search_ctx = _SearchContext(client=sc, top_k=self.max_search_docs)
                logger.info(
                    "ReasoningAgentTemplate: search index '%s' configured.",
                    self.search_config.index_name,
                )
            except Exception as ex:  # noqa: BLE001
                logger.warning("ReasoningAgentTemplate: search initialization failed: %s", ex)

        # Registry
        try:
            agent_registry.register_agent(self)
        except Exception:  # noqa: BLE001
            pass

        self._opened = True
        return self

    async def close(self) -> None:
        if not self._opened:
            return
        try:
            if self._client:
                await self._client.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._credential:
                await self._credential.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            agent_registry.unregister_agent(self)
        except Exception:  # noqa: BLE001
            pass

        self._client = None
        self._project_client = None
        self._credential = None
        self._search_ctx = None
        self._opened = False

    async def __aenter__(self) -> "ReasoningAgentTemplate":
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # ------------- Public Invocation -------------
    async def invoke(self, message: str) -> AsyncIterator[ChatResponseUpdate]:
        """
        Mirrors old streaming interface:
        Yields ChatResponseUpdate objects (instead of SK ChatMessageContent).
        Consumers expecting SK types should translate here.
        """
        async for update in self._invoke_stream_internal(message):
            yield update

    # ------------- Internal streaming logic -------------
    async def _invoke_stream_internal(self, prompt: str) -> AsyncIterator[ChatResponseUpdate]:
        if not self._opened or not self._client:
            raise RuntimeError("Agent not opened. Call open().")

        # Build instructions with optional search
        instructions = self.base_instructions
        if self._search_ctx and prompt.strip():
            docs = await self._fetch_docs_async(prompt)
            if docs:
                joined = "\n\n".join(f"[Doc {i+1}] {d}" for i, d in enumerate(docs))
                instructions = (
                    f"{instructions}\n\nRelevant reference documents:\n{joined}\n\n"
                    "Use them only if they help answer the question."
                )

        tools = []
        if self.mcp_config:
            tools.append(
                HostedMCPTool(
                    name=self.mcp_config.name,
                    description=self.mcp_config.description,
                    server_label=self.mcp_config.name.replace(" ", "_"),
                )
            )

        chat_options = ChatOptions(
            model_id=self.model_deployment_name,
            tools=tools if tools else None,
            tool_choice="auto" if tools else "none",
            temperature=0.7,
            allow_multiple_tool_calls=True,
        )

        messages = [ChatMessage(role=Role.USER, text=prompt)]

        async for update in self._client.get_streaming_response(
            messages=messages,
            chat_options=chat_options,
            instructions=instructions,
        ):
            yield update

    async def _fetch_docs_async(self, query: str) -> List[str]:
        if not self._search_ctx:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._search_ctx.fetch(query))

    # ------------- Convenience -------------
    @property
    def client(self) -> AzureAIAgentClient | None:
        return self._client


# Factory (name preserved)
async def create_reasoning_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    azure_openai_endpoint: str,
    search_config: SearchConfig | None = None,
    mcp_config: MCPConfig | None = None,
) -> ReasoningAgentTemplate:
    agent = ReasoningAgentTemplate(
        agent_name=agent_name,
        agent_description=agent_description,
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        azure_openai_endpoint=azure_openai_endpoint,
        search_config=search_config,
        mcp_config=mcp_config,
    )
    await agent.open()
    return agent