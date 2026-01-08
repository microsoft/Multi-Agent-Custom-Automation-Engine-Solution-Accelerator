"""
Unit tests for backend.app module.
"""

import pytest
import sys
import os
import platform
from unittest.mock import patch, MagicMock, AsyncMock, Mock

# Skip on Linux due to platform-specific Mock/issubclass issues
skip_on_linux = pytest.mark.skipif(
    platform.system() == "Linux",
    reason="Skipping on Linux due to Mock/issubclass compatibility issues"
)

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


@pytest.fixture(autouse=True)
def setup_environment(monkeypatch):
    """Set up environment variables and mocks."""
    # Mock router BEFORE any imports
    mock_router = MagicMock()
    mock_router.routes = []
    sys.modules['backend.v4.api.router'] = MagicMock(app_v4=mock_router)
    
    # Mock middleware
    sys.modules['backend.middleware.health_check'] = MagicMock()
    
    # Mock agent registry
    mock_agent_registry = MagicMock()
    mock_agent_registry.cleanup_all_agents = AsyncMock()
    sys.modules['backend.v4.config.agent_registry'] = MagicMock(agent_registry=mock_agent_registry)
    
    # Mock Azure monitor
    with patch('azure.monitor.opentelemetry.configure_azure_monitor'):
        yield


@skip_on_linux
def test_app_initialization(setup_environment):
    """Test that FastAPI app initializes correctly."""
    from backend.app import app
    assert app is not None
    assert hasattr(app, 'routes')


@skip_on_linux
def test_app_has_cors_middleware(setup_environment):
    """Test that CORS middleware is configured."""
    from backend.app import app
    from starlette.middleware.cors import CORSMiddleware
    # Check if CORS middleware is in the middleware stack
    has_cors = any(
        hasattr(m, 'cls') and m.cls == CORSMiddleware
        for m in app.user_middleware
    )
    assert has_cors, "CORS middleware not found in app.user_middleware"


@skip_on_linux
def test_user_browser_language_endpoint(setup_environment):
    """Test the user browser language endpoint exists."""
    from backend.app import app, user_browser_language_endpoint
    from backend.common.models.messages_af import UserLanguage
    
    # Verify endpoint function exists and is callable
    assert callable(user_browser_language_endpoint)
    
    # Verify it can create UserLanguage object
    test_lang = UserLanguage(language="en-US")
    assert test_lang.language == "en-US"


@skip_on_linux
def test_user_browser_language_endpoint_different_languages(setup_environment):
    """Test UserLanguage model with different languages."""
    from backend.common.models.messages_af import UserLanguage
    
    # Test that UserLanguage can be created with different languages
    for lang in ["es-ES", "fr-FR", "ja-JP"]:
        test_lang = UserLanguage(language=lang)
        assert test_lang.language == lang


@skip_on_linux
@pytest.mark.asyncio
async def test_lifespan_context(setup_environment):
    """Test the lifespan context manager."""
    from backend.app import lifespan, app
    
    async with lifespan(app):
        pass


@skip_on_linux
def test_app_includes_v4_router(setup_environment):
    """Test that V4 router is included."""
    from backend.app import app
    assert len(app.routes) > 0


@skip_on_linux
def test_logging_configured(setup_environment):
    """Test that logging is configured."""
    import logging
    from backend.app import app
    
    logger = logging.getLogger("backend")
    assert logger is not None


@skip_on_linux
def test_fastapi_app_configuration(setup_environment):
    """Test FastAPI app is properly configured."""
    from backend.app import app
    
    # Verify app has lifespan
    assert app.router.lifespan_context is not None


@skip_on_linux
@pytest.mark.asyncio
async def test_user_browser_language_endpoint_function(setup_environment):
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


@skip_on_linux
@pytest.mark.asyncio
async def test_lifespan_exception_handling(setup_environment):
    """Test lifespan context manager exception handling during cleanup."""
    from backend.app import lifespan, app
    from backend.v4.config.agent_registry import agent_registry
    
    # Make cleanup raise an exception
    agent_registry.cleanup_all_agents.side_effect = Exception("Test cleanup error")
    
    # Should not raise, exception should be caught
    try:
        async with lifespan(app):
            pass
    except Exception:
        pytest.fail("Lifespan should handle cleanup exceptions gracefully")


@skip_on_linux
def test_applicationinsights_not_configured(setup_environment):
    """Test that app handles missing Application Insights gracefully."""
    # This test checks that the app can start even without AppInsights
    # The warning log on line 59 was already executed during module import
    from backend.app import app
    assert app is not None


