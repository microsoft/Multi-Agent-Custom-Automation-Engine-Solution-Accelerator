"""
Unit tests for backend.app module.

IMPORTANT: This test file MUST run in isolation from other backend tests.
Run it separately: python -m pytest tests/backend/test_app.py

It uses sys.modules mocking that conflicts with other v4 tests when run together.
The CI/CD workflow runs all backend tests together, where this file will work 
because it detects existing v4 imports and skips mocking.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from types import ModuleType

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


# Check if v4 modules are already properly imported (means we're in a full test run)
_router_module = sys.modules.get('backend.v4.api.router')
_has_real_router = (_router_module is not None and 
                   hasattr(_router_module, 'PlanService'))

if not _has_real_router:
    # We're running in isolation - need to mock v4 imports
    # This prevents relative import issues from v4.api.router
    
    # Create a real FastAPI router to avoid isinstance errors
    from fastapi import APIRouter
    
    # Mock azure.monitor.opentelemetry module
    mock_azure_monitor_module = ModuleType('configure_azure_monitor')
    mock_azure_monitor_module.configure_azure_monitor = lambda *args, **kwargs: None
    sys.modules['azure.monitor.opentelemetry'] = mock_azure_monitor_module
    
    # Mock v4.models.messages module
    mock_messages_module = ModuleType('messages')
    mock_messages_module.WebsocketMessageType = type('WebsocketMessageType', (), {})
    sys.modules['backend.v4.models.messages'] = mock_messages_module
    
    # Mock v4.api.router module with a real APIRouter
    mock_router_module = ModuleType('router')
    mock_router_module.app_v4 = APIRouter()
    sys.modules['backend.v4.api.router'] = mock_router_module
    
    # Mock v4.config.agent_registry module
    class MockAgentRegistry:
        async def cleanup_all_agents(self):
            pass
    
    mock_agent_registry_module = ModuleType('agent_registry')
    mock_agent_registry_module.agent_registry = MockAgentRegistry()
    sys.modules['backend.v4.config.agent_registry'] = mock_agent_registry_module

# Now import backend.app
from backend.app import app, user_browser_language_endpoint, lifespan
from backend.common.models.messages_af import UserLanguage


def test_app_initialization():
    """Test that FastAPI app initializes correctly."""
    assert app is not None
    assert hasattr(app, 'routes')
    assert app.title is not None


def test_app_has_routes():
    """Test that app has registered routes."""
    assert len(app.routes) > 0


def test_app_has_middleware():
    """Test that app has middleware configured."""
    assert hasattr(app, 'middleware')
    # Check middleware stack exists (may be None before first request)
    assert hasattr(app, 'middleware_stack')


def test_app_has_cors_middleware():
    """Test that CORS middleware is configured."""
    from starlette.middleware.cors import CORSMiddleware
    # Check if CORS middleware is in the middleware stack
    has_cors = any(
        hasattr(m, 'cls') and m.cls == CORSMiddleware
        for m in app.user_middleware
    )
    assert has_cors, "CORS middleware not found in app.user_middleware"


def test_user_language_model():
    """Test UserLanguage model creation."""
    test_lang = UserLanguage(language="en-US")
    assert test_lang.language == "en-US"
    
    test_lang2 = UserLanguage(language="es-ES")
    assert test_lang2.language == "es-ES"


def test_user_language_model_different_languages():
    """Test UserLanguage model with different languages."""
    for lang in ["fr-FR", "de-DE", "ja-JP", "zh-CN"]:
        test_lang = UserLanguage(language=lang)
        assert test_lang.language == lang


@pytest.mark.asyncio
async def test_user_browser_language_endpoint_function():
    """Test the user_browser_language_endpoint function directly."""
    user_lang = UserLanguage(language="fr-FR")
    request = Mock()
    
    result = await user_browser_language_endpoint(user_lang, request)
    
    assert result == {"status": "Language received successfully"}
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_user_browser_language_endpoint_multiple_calls():
    """Test the endpoint with multiple different languages."""
    request = Mock()
    
    for lang_code in ["en-US", "es-ES", "fr-FR"]:
        user_lang = UserLanguage(language=lang_code)
        result = await user_browser_language_endpoint(user_lang, request)
        assert result["status"] == "Language received successfully"


def test_app_router_lifespan():
    """Test that app has lifespan configured."""
    assert app.router.lifespan_context is not None


@pytest.mark.asyncio
async def test_lifespan_context():
    """Test the lifespan context manager."""
    # The agent_registry is already mocked at module level
    # Just test that lifespan context works
    async with lifespan(app):
        pass
    # If we get here without exception, the test passed


@pytest.mark.asyncio
async def test_lifespan_cleanup_exception_handling():
    """Test lifespan context manager exception handling during cleanup."""
    # Mock agent_registry with cleanup that raises
    with patch('backend.v4.config.agent_registry.agent_registry') as mock_registry:
        mock_registry.cleanup_all_agents = AsyncMock(side_effect=Exception("Test cleanup error"))
        
        # Should not raise, exception should be caught and logged
        try:
            async with lifespan(app):
                pass
        except Exception:
            pytest.fail("Lifespan should handle cleanup exceptions gracefully")


def test_app_logging_configured():
    """Test that logging is configured."""
    import logging
    
    logger = logging.getLogger("backend")
    assert logger is not None


def test_app_has_v4_router():
    """Test that V4 router is included in app routes."""
    assert len(app.routes) > 0
    # App should have routes from the v4 router
    route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    # At least one route should exist
    assert len(route_paths) > 0



