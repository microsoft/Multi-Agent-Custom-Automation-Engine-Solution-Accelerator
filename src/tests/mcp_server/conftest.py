"""
Test configuration for MCP server tests.
"""

import sys
from pathlib import Path

import pytest

# Put src/mcp_server at the FRONT of sys.path so its packages win over any
# same-named backend packages (e.g. `services`, `config`) regardless of the
# venv's base sys.path order. A guarded insert is insufficient: src/mcp_server
# may already be on the path but AFTER src/backend, so `import services` would
# otherwise resolve to src/backend/services.
_MCP_ROOT = str(Path(__file__).resolve().parents[2] / "mcp_server")
while _MCP_ROOT in sys.path:
    sys.path.remove(_MCP_ROOT)
sys.path.insert(0, _MCP_ROOT)


@pytest.fixture
def mcp_factory():
    """Factory fixture for tests."""
    from core.factory import MCPToolFactory

    return MCPToolFactory()


@pytest.fixture
def hr_service():
    """HR service fixture."""
    from services.hr_service import HRService

    return HRService()


@pytest.fixture
def tech_support_service():
    """Tech support service fixture."""
    from services.tech_support_service import TechSupportService

    return TechSupportService()


@pytest.fixture
def general_service():
    """General service fixture."""
    from services.general_service import GeneralService

    return GeneralService()


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing."""

    class MockMCP:
        def __init__(self):
            self.tools = []

        def tool(self, tags=None):
            def decorator(func):
                self.tools.append({"func": func, "tags": tags or []})
                return func

            return decorator

    return MockMCP()
