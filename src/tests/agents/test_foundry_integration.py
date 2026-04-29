"""
Integration tests for FoundryAgentTemplate functionality.
Tests Bing search, RAG, MCP tools, and Code Interpreter capabilities.

These tests use a thread-isolated asyncio.run() to avoid conflicts between
pytest's process-level event loop management and anyio's cancel scopes used
inside the MCP SDK's streamablehttp_client.
"""
# pylint: disable=E0401, E0611, C0413

import asyncio
import os
import sys
import threading
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load backend .env before any config modules are imported so that local
# environment variables (e.g. user-level overrides) don't shadow the real
# values.  The file is gitignored and won't exist in CI, making this a no-op
# in pipeline runs where secrets are injected directly as env vars.
backend_path = Path(__file__).parent.parent.parent / "backend"
_env_file = backend_path / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=True)

sys.path.insert(0, str(backend_path))

from backend.v4.magentic_agents.foundry_agent import FoundryAgentTemplate
from backend.v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from common.config.app_config import config as _app_config


def _reset_cached_clients():
    """Clear module-level singleton clients so each test thread gets a fresh one.

    AppConfig caches AIProjectClient and DefaultAzureCredential on first use.
    Those objects are bound to the asyncio event loop that was running when they
    were first awaited.  Because each test uses asyncio.run() inside its own
    thread (a new event loop per thread), the cached client from test N will
    reference a *closed* event loop by the time test N+1 runs, producing
    "Event loop is closed" errors.  Resetting them here forces re-creation
    inside the new event loop.
    """
    _app_config._ai_project_client = None
    _app_config._azure_credentials = None


def _run_async_in_thread(coro_fn, timeout=120):
    """Run an async function in a separate thread with its own event loop.

    This isolates from pytest's event loop management which conflicts with
    anyio cancel scopes inside the MCP SDK.
    """
    _reset_cached_clients()

    result = {"value": None, "error": None}

    def _target():
        try:
            result["value"] = asyncio.run(coro_fn())
        except BaseException as e:
            result["error"] = e

    t = threading.Thread(target=_target)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        raise TimeoutError(f"Test timed out after {timeout}s")
    if result["error"] is not None:
        raise result["error"]
    return result["value"]


class TestFoundryAgentIntegration:
    """Integration tests for FoundryAgentTemplate capabilities."""

    def get_agent_configs(self):
        """Create agent configurations from environment variables."""
        mcp_config = MCPConfig.from_env()
        search_config = SearchConfig.from_env("SEARCH")
        return {
            'mcp_config': mcp_config,
            'search_config': search_config
        }

    def _get_project_endpoint(self):
        return os.environ.get(
            "AZURE_AI_PROJECT_ENDPOINT",
            os.environ.get("AZURE_AI_AGENT_ENDPOINT", "")
        )

    async def create_foundry_agent(self, use_mcp=True, use_search=True):
        """Create and initialize a FoundryAgentTemplate for testing."""
        agent_configs = self.get_agent_configs()

        agent = FoundryAgentTemplate(
            agent_name="TestFoundryAgent",
            agent_description="A comprehensive research assistant for integration testing",
            agent_instructions=(
                "You are an Enhanced Research Agent with multiple information sources:\n"
                "1. Bing search for current web information and recent events\n"
                "2. Azure AI Search for internal knowledge base and documents\n"
                "3. MCP tools for specialized data access\n\n"
                "Search Strategy:\n"
                "- Use Azure AI Search first for internal/proprietary information\n"
                "- Use Bing search for current events, recent news, and public information\n"
                "- Always cite your sources and specify which search method provided the information\n"
                "- Provide comprehensive answers combining multiple sources when relevant\n"
                "- Ask for clarification only if the task is genuinely ambiguous"
            ),
            use_reasoning=False,
            model_deployment_name="gpt-4.1",
            project_endpoint=self._get_project_endpoint(),
            enable_code_interpreter=True,
            mcp_config=agent_configs['mcp_config'] if use_mcp else None,
            search_config=agent_configs['search_config'] if use_search else None,
        )

        await agent.open()
        return agent

    async def _get_agent_response(self, agent: FoundryAgentTemplate, query: str) -> str:
        """Helper method to get complete response from agent."""
        response_parts = []
        async for message in agent.invoke(query):
            if hasattr(message, 'content'):
                content = message.content
                if hasattr(content, 'text'):
                    response_parts.append(str(content.text))
                elif isinstance(content, list):
                    for item in content:
                        if hasattr(item, 'text'):
                            response_parts.append(str(item.text))
                        else:
                            response_parts.append(str(item))
                else:
                    response_parts.append(str(content))
            else:
                s = str(message)
                if s and s != 'None':
                    response_parts.append(s)
        return ''.join(response_parts)

    def test_bing_search_functionality(self):
        """Test that Bing search is working correctly."""
        async def _run():
            agent = await self.create_foundry_agent()
            try:
                bing = getattr(agent, 'bing', None)
                if not bing or not getattr(bing, 'connection_name', None):
                    pytest.skip("Bing configuration not available")

                query = (
                    "Please try to get todays weather in Redmond WA using a bing search. "
                    "If this succeeds, please just respond with yes, "
                    "if it does not, please respond with no"
                )
                response = await self._get_agent_response(agent, query)
                assert 'yes' in response.lower(), \
                    "Responded that the agent could not perform the Bing search"
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_rag_search_functionality(self):
        """Test that Azure AI Search RAG is working correctly."""
        async def _run():
            # Use search mode (no MCP) for RAG test
            agent = await self.create_foundry_agent(use_mcp=False, use_search=True)
            try:
                if not agent.search or not agent.search.connection_name:
                    pytest.skip("Azure AI Search configuration not available")

                starter = "Do you have access to internal documents?"
                await self._get_agent_response(agent, starter)

                query = (
                    "Can you tell me about any incident reports that have "
                    "affected the warehouses?"
                )
                response = await self._get_agent_response(agent, query)

                # The agent should return substantive content about warehouse incidents.
                # Exact wording varies by run; assert the response is non-trivial and
                # mentions warehouses or incidents in some form.
                assert len(response) > 50, f"Expected substantive RAG response, got: {response}"
                assert any(indicator in response.lower() for indicator in [
                    'warehouse', 'incident', 'report', 'injury', 'safety', 'damage'
                ]), f"Expected warehouse incident content in response, got: {response}"
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_mcp_functionality(self):
        """Test that MCP tools are working correctly."""
        async def _run():
            # Use MCP mode (no search) so agent takes the MCP path
            agent = await self.create_foundry_agent(use_mcp=True, use_search=False)
            try:
                if not agent.mcp_cfg or not agent.mcp_cfg.url:
                    pytest.skip("MCP configuration not available")

                # Use send_welcome_email from TechSupportService (registered on the deployed server)
                query = "Please send a welcome email to Alice using email alice@example.com using the send_welcome_email tool"
                response = await self._get_agent_response(agent, query)

                assert any(indicator in response.lower() for indicator in [
                    'welcome', 'email', 'sent', 'alice'
                ]), (
                    f"Expected MCP tool response with welcome/email/sent/alice, "
                    f"got: {response}"
                )
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_code_interpreter_functionality(self):
        """Test that Code Interpreter is working correctly."""
        async def _run():
            # Use MCP mode (no search) to enable Code Interpreter
            agent = await self.create_foundry_agent(use_mcp=False, use_search=False)
            try:
                if not agent.enable_code_interpreter:
                    pytest.skip("Code Interpreter not enabled")

                query = "Can you write and execute Python code to calculate the factorial of 5?"
                response = await self._get_agent_response(agent, query)

                assert any(indicator in response.lower() for indicator in [
                    'factorial', '120', 'code', 'python', 'execution', 'result'
                ]), f"Expected code execution indicators in response, got: {response}"

                assert "120" in response, \
                    f"Expected factorial result '120' in response, got: {response}"
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_agent_initialization(self):
        """Test that the agent initializes correctly with available configurations."""
        async def _run():
            # Use MCP mode to verify MCP tool initialization
            agent = await self.create_foundry_agent(use_mcp=True, use_search=False)
            try:
                assert agent.agent_name == "TestFoundryAgent"
                assert agent._agent is not None, "Agent should be initialized"

                if agent.mcp_cfg and agent.mcp_cfg.url:
                    assert agent.mcp_tool is not None, "MCP tool should be available"
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_agent_handles_missing_configs_gracefully(self):
        """Test that agent handles missing configurations without crashing."""
        async def _run():
            agent = FoundryAgentTemplate(
                agent_name="TestAgent",
                agent_description="Test agent",
                agent_instructions="Test instructions",
                use_reasoning=False,
                model_deployment_name="gpt-4.1",
                project_endpoint=self._get_project_endpoint(),
                enable_code_interpreter=False,
                mcp_config=None,
                search_config=None
            )

            try:
                await agent.open()
                response = await self._get_agent_response(agent, "Hello, how are you?")
                assert len(response) > 0, "Should get some response even without tools"
            finally:
                await agent.close()

        _run_async_in_thread(_run)

    def test_multiple_capabilities_together(self):
        """Test that multiple capabilities can work together in a single query."""
        async def _run():
            agent = await self.create_foundry_agent(use_mcp=True, use_search=True)
            try:
                available_capabilities = []
                bing = getattr(agent, 'bing', None)
                if bing and getattr(bing, 'connection_name', None):
                    available_capabilities.append("Bing")
                if agent.search and agent.search.connection_name:
                    available_capabilities.append("RAG")
                if agent.mcp_cfg and agent.mcp_cfg.url:
                    available_capabilities.append("MCP")

                if len(available_capabilities) < 2:
                    pytest.skip("Need at least 2 capabilities for integration test")

                query = (
                    "Can you search for recent AI news and also check if you "
                    "have any internal documents about AI?"
                )
                response = await self._get_agent_response(agent, query)

                assert len(response) > 100, (
                    "Should get comprehensive response using multiple capabilities"
                )
            finally:
                await agent.close()

        _run_async_in_thread(_run)


if __name__ == "__main__":
    """Run the tests directly for debugging."""
    pytest.main([__file__, "-v", "-s"])
