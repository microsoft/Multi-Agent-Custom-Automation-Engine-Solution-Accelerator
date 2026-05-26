"""Integration smoke test for AgentTemplate — MAF 1.0 section 6 pattern.

Exercises the full open() / close() lifecycle against a live Foundry environment:

  1. get-or-create the Foundry portal agent
  2. build the per-agent Toolbox (no tools for the smoke-test agent)
  3. create Agent(FoundryChatClient)
  4. close() and verify all resources released

Run only when Azure credentials and a real project endpoint are available:

    pytest src/tests/agents/test_agent_template_integration.py -m integration -v

The tests are automatically skipped when required environment variables are
absent, so they are safe to collect in CI without credentials.

Replaces the stale test_foundry_integration.py (which tested the old two-path
FoundryAgentTemplate constructor signature).
"""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Make sure 'src/backend' is on the path (covers running from repo root and
# from src/backend/, matching how unit tests and the backend venv are set up).
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[3] / "src" / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Load .env so that developers can run integration tests with a local .env
# without exporting variables manually.  dotenv is installed in the backend
# venv (python-dotenv is a transitive dep of azure-ai-projects).
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    _env_path = _BACKEND_DIR / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # dotenv not installed — rely on shell environment


# ---------------------------------------------------------------------------
# Required environment variables for integration tests
# ---------------------------------------------------------------------------
_REQUIRED_VARS = [
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME",
]

_missing = [v for v in _REQUIRED_VARS if not os.getenv(v)]
_skip_reason = (
    f"Integration env vars not set: {', '.join(_missing)}"
    if _missing
    else ""
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper: a minimal agent config that does NOT require any tools so that
# the smoke test can pass without MCP servers, AI Search indexes, etc.
# ---------------------------------------------------------------------------
_SMOKE_AGENT_NAME = "macae-smoke-test-agent"
_SMOKE_AGENT_DESC = "Temporary agent created by the Phase 7 integration smoke test."
_SMOKE_AGENT_INSTRUCTIONS = (
    "You are a helpful assistant used for automated smoke testing only. "
    "Do not use this agent in production."
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_open_and_close_no_tools():
    """Full lifecycle: open() (get-or-create portal agent, no Toolbox) → close().

    Validates:
    - AgentTemplate.open() completes without raising
    - _agent is set after open()
    - _stack is set after open()
    - close() completes without raising
    - _agent and _stack are None after close()
    """
    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    template = AgentTemplate(
        agent_name=_SMOKE_AGENT_NAME,
        agent_description=_SMOKE_AGENT_DESC,
        agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
        model_deployment_name=model,
        project_endpoint=project_endpoint,
        enable_code_interpreter=False,
        mcp_config=None,
        search_config=None,
        team_config=None,
        memory_store=None,
    )

    await template.open()

    assert template._agent is not None, "AgentTemplate._agent must be set after open()"
    assert template._stack is not None, "AgentTemplate._stack must be set after open()"
    assert template._credential is not None, "AgentTemplate._credential must be set after open()"

    await template.close()

    assert template._agent is None, "AgentTemplate._agent must be None after close()"
    assert template._stack is None, "AgentTemplate._stack must be None after close()"


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_context_manager_protocol():
    """async with AgentTemplate(...) as t: open() and close() are called correctly."""
    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    template = AgentTemplate(
        agent_name=_SMOKE_AGENT_NAME,
        agent_description=_SMOKE_AGENT_DESC,
        agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
        model_deployment_name=model,
        project_endpoint=project_endpoint,
    )

    async with template as t:
        assert t is template
        assert template._agent is not None

    assert template._stack is None


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_second_open_is_idempotent():
    """Calling open() on an already-open agent is a no-op and returns self."""
    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    template = AgentTemplate(
        agent_name=_SMOKE_AGENT_NAME,
        agent_description=_SMOKE_AGENT_DESC,
        agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
        model_deployment_name=model,
        project_endpoint=project_endpoint,
    )

    try:
        result1 = await template.open()
        agent_after_first = template._agent

        result2 = await template.open()  # should be idempotent
        agent_after_second = template._agent

        assert result1 is template
        assert result2 is template
        assert agent_after_first is agent_after_second, (
            "Second open() must not replace the already-initialized agent"
        )
    finally:
        await template.close()


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_get_or_create_creates_when_absent(monkeypatch):
    """If the portal agent does not exist, create_agent() is called exactly once.

    Uses monkeypatching on AIProjectClient to verify the branch without
    actually hitting the Foundry API — making this a fast, deterministic
    variant of the integration test that still exercises the real open() code.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    # Build a minimal mock agent record
    mock_agent_record = MagicMock()
    mock_agent_record.model = model
    mock_agent_record.instructions = _SMOKE_AGENT_INSTRUCTIONS
    mock_agent_record.name = _SMOKE_AGENT_NAME

    # list_agents returns an async iterator with NO entries → forces the create path
    async def _empty_async_iter():
        return
        yield  # makes it an async generator

    mock_agents = MagicMock()
    mock_agents.list_agents = MagicMock(return_value=_empty_async_iter())
    mock_agents.create_agent = AsyncMock(return_value=mock_agent_record)

    mock_project_client = AsyncMock()
    mock_project_client.agents = mock_agents
    mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
    mock_project_client.__aexit__ = AsyncMock(return_value=False)
    mock_project_client.beta = MagicMock()
    mock_project_client.beta.toolboxes = MagicMock()
    mock_project_client.beta.toolboxes.create_toolbox_version = AsyncMock()

    mock_chat_client = AsyncMock()
    mock_chat_client.__aenter__ = AsyncMock(return_value=mock_chat_client)
    mock_chat_client.__aexit__ = AsyncMock(return_value=False)

    mock_agent = AsyncMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
        patch("agents.agent_template.AIProjectClient", return_value=mock_project_client),
        patch("agents.agent_template.FoundryChatClient", return_value=mock_chat_client),
        patch("agents.agent_template.Agent", return_value=mock_agent),
    ):
        template = AgentTemplate(
            agent_name=_SMOKE_AGENT_NAME,
            agent_description=_SMOKE_AGENT_DESC,
            agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
            model_deployment_name=model,
            project_endpoint=project_endpoint,
        )
        await template.open()

        mock_agents.create_agent.assert_called_once_with(
            model=model,
            name=_SMOKE_AGENT_NAME,
            instructions=_SMOKE_AGENT_INSTRUCTIONS,
            description=_SMOKE_AGENT_DESC,
        )

        await template.close()


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_get_or_create_skips_create_when_present():
    """If the portal agent already exists, create_agent() is NOT called."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    mock_agent_record = MagicMock()
    mock_agent_record.model = model
    mock_agent_record.instructions = _SMOKE_AGENT_INSTRUCTIONS
    mock_agent_record.name = _SMOKE_AGENT_NAME

    # list_agents returns an async iterator containing the existing agent
    async def _existing_agent_iter():
        yield mock_agent_record

    mock_agents = MagicMock()
    mock_agents.list_agents = MagicMock(return_value=_existing_agent_iter())
    mock_agents.create_agent = AsyncMock(return_value=mock_agent_record)

    mock_project_client = AsyncMock()
    mock_project_client.agents = mock_agents
    mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
    mock_project_client.__aexit__ = AsyncMock(return_value=False)
    mock_project_client.beta = MagicMock()
    mock_project_client.beta.toolboxes = MagicMock()
    mock_project_client.beta.toolboxes.create_toolbox_version = AsyncMock()

    mock_chat_client = AsyncMock()
    mock_chat_client.__aenter__ = AsyncMock(return_value=mock_chat_client)
    mock_chat_client.__aexit__ = AsyncMock(return_value=False)

    mock_agent = AsyncMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
        patch("agents.agent_template.AIProjectClient", return_value=mock_project_client),
        patch("agents.agent_template.FoundryChatClient", return_value=mock_chat_client),
        patch("agents.agent_template.Agent", return_value=mock_agent),
    ):
        template = AgentTemplate(
            agent_name=_SMOKE_AGENT_NAME,
            agent_description=_SMOKE_AGENT_DESC,
            agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
            model_deployment_name=model,
            project_endpoint=project_endpoint,
        )
        await template.open()

        mock_agents.create_agent.assert_not_called()

        await template.close()


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_toolbox_created_when_mcp_config_present():
    """When mcp_config is provided, create_toolbox_version() is called with an MCPTool."""
    from unittest.mock import AsyncMock, MagicMock, call, patch

    from agents.agent_template import AgentTemplate
    from config.mcp_config import MCPConfig

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    mcp_cfg = MCPConfig(
        url="http://test-mcp.local/mcp",
        name="test-mcp-server",
        description="Smoke test MCP server",
        tenant_id="",
        client_id="",
    )

    mock_agent_record = MagicMock()
    mock_agent_record.model = model
    mock_agent_record.instructions = _SMOKE_AGENT_INSTRUCTIONS
    mock_agent_record.name = _SMOKE_AGENT_NAME

    async def _empty_async_iter():
        return
        yield

    mock_toolboxes = MagicMock()
    mock_toolboxes.create_toolbox_version = AsyncMock()

    mock_agents = MagicMock()
    mock_agents.list_agents = MagicMock(return_value=_empty_async_iter())
    mock_agents.create_agent = AsyncMock(return_value=mock_agent_record)

    mock_toolbox_obj = MagicMock()
    mock_chat_client = AsyncMock()
    mock_chat_client.__aenter__ = AsyncMock(return_value=mock_chat_client)
    mock_chat_client.__aexit__ = AsyncMock(return_value=False)
    mock_chat_client.get_toolbox = AsyncMock(return_value=mock_toolbox_obj)

    mock_project_client = AsyncMock()
    mock_project_client.agents = mock_agents
    mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
    mock_project_client.__aexit__ = AsyncMock(return_value=False)
    mock_project_client.beta = MagicMock()
    mock_project_client.beta.toolboxes = mock_toolboxes

    mock_agent = AsyncMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
        patch("agents.agent_template.AIProjectClient", return_value=mock_project_client),
        patch("agents.agent_template.FoundryChatClient", return_value=mock_chat_client),
        patch("agents.agent_template.Agent", return_value=mock_agent),
    ):
        template = AgentTemplate(
            agent_name=_SMOKE_AGENT_NAME,
            agent_description=_SMOKE_AGENT_DESC,
            agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
            model_deployment_name=model,
            project_endpoint=project_endpoint,
            mcp_config=mcp_cfg,
        )
        await template.open()

        expected_toolbox_name = f"macae-{_SMOKE_AGENT_NAME}-tools"
        mock_toolboxes.create_toolbox_version.assert_called_once()
        call_kwargs = mock_toolboxes.create_toolbox_version.call_args.kwargs
        assert call_kwargs["toolbox_name"] == expected_toolbox_name
        assert len(call_kwargs["tools"]) == 1  # one MCPTool

        mock_chat_client.get_toolbox.assert_called_once_with(expected_toolbox_name)

        await template.close()


@pytest.mark.skipif(bool(_missing), reason=_skip_reason)
@pytest.mark.asyncio
async def test_no_toolbox_created_when_no_tools():
    """When no tools are configured, create_toolbox_version() is NOT called."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from agents.agent_template import AgentTemplate

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]

    mock_agent_record = MagicMock()
    mock_agent_record.model = model
    mock_agent_record.instructions = _SMOKE_AGENT_INSTRUCTIONS
    mock_agent_record.name = _SMOKE_AGENT_NAME

    async def _empty_async_iter():
        return
        yield

    mock_toolboxes = MagicMock()
    mock_toolboxes.create_toolbox_version = AsyncMock()

    mock_agents = MagicMock()
    mock_agents.list_agents = MagicMock(return_value=_empty_async_iter())
    mock_agents.create_agent = AsyncMock(return_value=mock_agent_record)

    mock_project_client = AsyncMock()
    mock_project_client.agents = mock_agents
    mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
    mock_project_client.__aexit__ = AsyncMock(return_value=False)
    mock_project_client.beta = MagicMock()
    mock_project_client.beta.toolboxes = mock_toolboxes

    mock_chat_client = AsyncMock()
    mock_chat_client.__aenter__ = AsyncMock(return_value=mock_chat_client)
    mock_chat_client.__aexit__ = AsyncMock(return_value=False)

    mock_agent = AsyncMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
        patch("agents.agent_template.AIProjectClient", return_value=mock_project_client),
        patch("agents.agent_template.FoundryChatClient", return_value=mock_chat_client),
        patch("agents.agent_template.Agent", return_value=mock_agent),
    ):
        template = AgentTemplate(
            agent_name=_SMOKE_AGENT_NAME,
            agent_description=_SMOKE_AGENT_DESC,
            agent_instructions=_SMOKE_AGENT_INSTRUCTIONS,
            model_deployment_name=model,
            project_endpoint=project_endpoint,
            enable_code_interpreter=False,
            mcp_config=None,
            search_config=None,
        )
        await template.open()

        mock_toolboxes.create_toolbox_version.assert_not_called()

        await template.close()
