"""Unit tests for app.py FastAPI application."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

class TestAppLifespan:
    """Test the application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown_success(self):
        """Test successful startup and shutdown of lifespan."""
        with patch('app.agent_registry') as mock_registry, \
             patch('app.logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_registry.cleanup_all_agents = AsyncMock()
            
            from app import lifespan
            
            mock_app = MagicMock()
            
            async with lifespan(mock_app):
                # Verify startup log
                assert mock_logger.info.called
            
            # Verify cleanup was called
            mock_registry.cleanup_all_agents.assert_called_once()








class TestUserBrowserLanguageEndpoint:
    """Test the user browser language endpoint."""

    @pytest.mark.asyncio 
    async def test_user_browser_language_endpoint(self):
        """Test the user browser language endpoint."""
        with patch('app.config') as mock_config, \
             patch('app.logging') as mock_logging:
            
            mock_config.set_user_local_browser_language = MagicMock()
            
            from app import user_browser_language_endpoint
            
            # Create mock objects
            mock_user_lang = MagicMock()
            mock_user_lang.language = "en-US"
            mock_request = MagicMock()
            
            # Test the endpoint
            result = await user_browser_language_endpoint(mock_user_lang, mock_request)
            
            assert result == {"status": "Language received successfully"}
            mock_config.set_user_local_browser_language.assert_called_once_with("en-US")


class TestAppConfiguration:
    """Test app configuration."""

    def test_app_configuration(self):
        """Test that the app is properly configured."""
        with patch('app.config') as mock_config:
            mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "test-connection"
            mock_config.FRONTEND_SITE_NAME = "test-frontend"
            
            import app
            assert app.app is not None