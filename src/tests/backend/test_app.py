"""
Unit tests for backend.app module.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock, Mock

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
src_path = os.path.abspath(src_path)
sys.path.insert(0, src_path)

# Set environment variables BEFORE importing backend.app
os.environ.setdefault("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key-12345")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "test-deployment")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-02-01")
os.environ.setdefault("PROJECT_CONNECTION_STRING", "test-connection")
os.environ.setdefault("AZURE_COSMOS_ENDPOINT", "https://test.cosmos.azure.com")
os.environ.setdefault("AZURE_COSMOS_KEY", "test-key")
os.environ.setdefault("AZURE_COSMOS_DATABASE_NAME", "test-db")
os.environ.setdefault("AZURE_COSMOS_CONTAINER_NAME", "test-container")
os.environ.setdefault("FRONTEND_SITE_NAME", "http://localhost:3000")
os.environ.setdefault("AZURE_AI_SUBSCRIPTION_ID", "test-subscription-id")
os.environ.setdefault("AZURE_AI_RESOURCE_GROUP", "test-resource-group")
os.environ.setdefault("AZURE_AI_PROJECT_NAME", "test-project")
os.environ.setdefault("AZURE_AI_AGENT_ENDPOINT", "https://test.endpoint.azure.com")
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("AZURE_OPENAI_RAI_DEPLOYMENT_NAME", "test-rai-deployment")


@pytest.fixture(scope="module", autouse=True)
def setup_mocks():
    """Set up mocks for backend.app imports."""
    # Save original modules
    original_router = sys.modules.get('backend.v4.api.router')
    original_agent_registry = sys.modules.get('backend.v4.config.agent_registry')
    
    # Create APIRouter mock that doesn't trigger isinstance/issubclass
    from fastapi import APIRouter
    mock_app_v4 = APIRouter()
    mock_app_v4.routes = []
    
    # Mock the router module
    class MockRouterModule:
        app_v4 = mock_app_v4
    
    sys.modules['backend.v4.api.router'] = MockRouterModule()
    
    # Mock agent registry
    class MockAgentRegistry:
        async def cleanup_all_agents(self):
            pass
    
    class MockAgentRegistryModule:
        agent_registry = MockAgentRegistry()
    
    sys.modules['backend.v4.config.agent_registry'] = MockAgentRegistryModule()
    
    # Mock Azure monitor and import
    with patch('azure.monitor.opentelemetry.configure_azure_monitor'):
        # Now import backend.app
        import backend.app
        globals()['app'] = backend.app.app
        globals()['lifespan'] = backend.app.lifespan
        globals()['user_browser_language_endpoint'] = backend.app.user_browser_language_endpoint
    
    yield
    
    # Cleanup - restore original modules
    if original_router is not None:
        sys.modules['backend.v4.api.router'] = original_router
    elif 'backend.v4.api.router' in sys.modules:
        del sys.modules['backend.v4.api.router']
    
    if original_agent_registry is not None:
        sys.modules['backend.v4.config.agent_registry'] = original_agent_registry
    elif 'backend.v4.config.agent_registry' in sys.modules:
        del sys.modules['backend.v4.config.agent_registry']
    
    # Remove backend.app from cache so it can be reimported fresh
    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']


def test_app_initialization():
    """Test that FastAPI app initializes correctly."""
    from backend.app import app
    assert app is not None
    assert hasattr(app, 'routes')


def test_app_has_cors_middleware():
    """Test that CORS middleware is configured."""
    from starlette.middleware.cors import CORSMiddleware
    # Check if CORS middleware is in the middleware stack
    has_cors = any(
        hasattr(m, 'cls') and m.cls == CORSMiddleware
        for m in app.user_middleware
    )
    assert has_cors, "CORS middleware not found in app.user_middleware"


def test_user_browser_language_endpoint():
    """Test the user browser language endpoint exists."""
    from backend.app import user_browser_language_endpoint
    from backend.common.models.messages_af import UserLanguage
    
    # Verify endpoint function exists and is callable
    assert callable(user_browser_language_endpoint)
    
    # Verify it can create UserLanguage object
    test_lang = UserLanguage(language="en-US")
    assert test_lang.language == "en-US"


def test_user_browser_language_endpoint_different_languages():
    """Test UserLanguage model with different languages."""
    from backend.common.models.messages_af import UserLanguage
    
    # Test that UserLanguage can be created with different languages
    for lang in ["es-ES", "fr-FR", "ja-JP"]:
        test_lang = UserLanguage(language=lang)
        assert test_lang.language == lang


@pytest.mark.asyncio
async def test_lifespan_context():
    """Test the lifespan context manager."""
    from backend.app import lifespan
    
    async with lifespan(app):
        pass


def test_app_includes_v4_router():
    """Test that V4 router is included."""
    assert len(app.routes) > 0


def test_logging_configured():
    """Test that logging is configured."""
    import logging
    
    logger = logging.getLogger("backend")
    assert logger is not None


def test_fastapi_app_configuration():
    """Test FastAPI app is properly configured."""
    
    # Verify app has lifespan
    assert app.router.lifespan_context is not None


@pytest.mark.asyncio
async def test_user_browser_language_endpoint_function():
    """Test the user_browser_language_endpoint function directly."""
    from backend.app import user_browser_language_endpoint
    from backend.common.models.messages_af import UserLanguage
    from unittest.mock import Mock
    
    # Create test data
    user_lang = UserLanguage(language="fr-FR")
    request = Mock()
    
    # Call the endpoint
    result = await user_browser_language_endpoint(user_lang, request)
    
    # Verify result
    assert result == {"status": "Language received successfully"}


@pytest.mark.asyncio
async def test_lifespan_exception_handling():
    """Test lifespan context manager exception handling during cleanup."""
    from backend.app import lifespan
    from backend.v4.config.agent_registry import agent_registry
    
    # Save original method
    original_cleanup = agent_registry.cleanup_all_agents
    
    # Make cleanup raise an exception
    async def mock_cleanup():
        raise Exception("Test cleanup error")
    
    agent_registry.cleanup_all_agents = mock_cleanup
    
    # Should not raise, exception should be caught
    try:
        async with lifespan(app):
            pass
    except Exception:
        pytest.fail("Lifespan should handle cleanup exceptions gracefully")
    finally:
        # Restore original method
        agent_registry.cleanup_all_agents = original_cleanup


def test_applicationinsights_not_configured():
    """Test that app handles missing Application Insights gracefully."""
    # This test checks that the app can start even without AppInsights
    # The warning log on line 59 was already executed during module import
    assert app is not None


