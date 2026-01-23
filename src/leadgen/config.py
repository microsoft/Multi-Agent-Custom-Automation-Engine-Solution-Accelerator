"""Lead generation service configuration module.

This module provides centralized configuration management for the lead generation
pipeline, loading settings from environment variables with validation.

Configuration is loaded from:
1. .env file (if present)
2. Environment variables

All API keys and sensitive configuration should be provided via environment
variables, never hardcoded.

Usage:
    >>> from config import config
    >>> print(config.OPENAI_API_KEY[:8])
    sk-proj-
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Raised when configuration validation fails."""

    pass


class Config:
    """Application configuration class that loads settings from environment variables.

    Loads and validates all required configuration for the lead generation service,
    including API keys for external services (OpenAI, Google Maps, Firecrawl, etc.),
    database connection strings, and service-specific settings.

    Attributes:
        OPENAI_API_KEY: OpenAI API key for Agents SDK, Vector Stores, Realtime API.
        GOOGLE_MAPS_API_KEY: Google Maps Places API key for lead scraping.
        FIRECRAWL_API_KEY: Firecrawl API key for web scraping.
        APOLLO_API_KEY: Apollo.io API key for contact enrichment.
        DATABASE_URL: PostgreSQL connection string.
        TWILIO_ACCOUNT_SID: Twilio account SID for voice calls.
        TWILIO_AUTH_TOKEN: Twilio auth token.
        TWILIO_PHONE_NUMBER: Twilio voice-enabled phone number.
        SENDGRID_API_KEY: SendGrid API key for email delivery.
        VERCEL_TOKEN: Vercel API token for demo site deployments.

    Example:
        >>> config = Config()
        >>> print(config.APP_ENV)
        dev
    """

    def __init__(self) -> None:
        """Initialize configuration by loading from environment variables."""
        self.logger = logging.getLogger(__name__)

        # Application environment
        self.APP_ENV = self._get_optional("APP_ENV", "dev")
        self.DEBUG = self._get_bool("DEBUG")
        self.LOG_LEVEL = self._get_optional("LOG_LEVEL", "INFO")

        # OpenAI Configuration
        self.OPENAI_API_KEY = self._get_optional("OPENAI_API_KEY")
        self.OPENAI_MODEL = self._get_optional("OPENAI_MODEL", "gpt-4o")
        self.OPENAI_REALTIME_MODEL = self._get_optional(
            "OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview"
        )

        # Google Maps Configuration
        self.GOOGLE_MAPS_API_KEY = self._get_optional("GOOGLE_MAPS_API_KEY")
        self.GOOGLE_MAPS_RADIUS_MILES = int(
            self._get_optional("GOOGLE_MAPS_RADIUS_MILES", "20")
        )
        self.GOOGLE_MAPS_MAX_RESULTS = int(
            self._get_optional("GOOGLE_MAPS_MAX_RESULTS", "100")
        )

        # Firecrawl Configuration
        self.FIRECRAWL_API_KEY = self._get_optional("FIRECRAWL_API_KEY")
        self.FIRECRAWL_TIMEOUT_SECONDS = int(
            self._get_optional("FIRECRAWL_TIMEOUT_SECONDS", "60")
        )

        # Apollo Configuration
        self.APOLLO_API_KEY = self._get_optional("APOLLO_API_KEY")
        self.APOLLO_TIMEOUT_SECONDS = int(
            self._get_optional("APOLLO_TIMEOUT_SECONDS", "30")
        )

        # Database Configuration
        self.DATABASE_URL = self._get_optional("DATABASE_URL")
        self.DATABASE_POOL_SIZE = int(self._get_optional("DATABASE_POOL_SIZE", "5"))
        self.DATABASE_MAX_OVERFLOW = int(
            self._get_optional("DATABASE_MAX_OVERFLOW", "10")
        )

        # Twilio Configuration
        self.TWILIO_ACCOUNT_SID = self._get_optional("TWILIO_ACCOUNT_SID")
        self.TWILIO_AUTH_TOKEN = self._get_optional("TWILIO_AUTH_TOKEN")
        self.TWILIO_PHONE_NUMBER = self._get_optional("TWILIO_PHONE_NUMBER")

        # SendGrid Configuration
        self.SENDGRID_API_KEY = self._get_optional("SENDGRID_API_KEY")
        self.SENDGRID_FROM_EMAIL = self._get_optional("SENDGRID_FROM_EMAIL")
        self.SENDGRID_FROM_NAME = self._get_optional("SENDGRID_FROM_NAME")

        # Vercel Configuration
        self.VERCEL_TOKEN = self._get_optional("VERCEL_TOKEN")
        self.VERCEL_TEAM_ID = self._get_optional("VERCEL_TEAM_ID")
        self.VERCEL_PROJECT_NAME = self._get_optional(
            "VERCEL_PROJECT_NAME", "leadgen-demo"
        )

        # Voice Server Configuration
        self.VOICE_SERVER_HOST = self._get_optional("VOICE_SERVER_HOST", "0.0.0.0")
        self.VOICE_SERVER_PORT = int(self._get_optional("VOICE_SERVER_PORT", "8765"))
        self.VOICE_WEBSOCKET_URL = self._get_optional("VOICE_WEBSOCKET_URL")

        # API Server Configuration
        self.API_HOST = self._get_optional("API_HOST", "0.0.0.0")
        self.API_PORT = int(self._get_optional("API_PORT", "8080"))

        # Campaign Configuration
        self.DEFAULT_INDUSTRIES = self._get_optional(
            "DEFAULT_INDUSTRIES", "dentist,hvac,salon,plumber,electrician"
        ).split(",")
        self.MIN_REVENUE = int(self._get_optional("MIN_REVENUE", "100000"))
        self.MAX_REVENUE = int(self._get_optional("MAX_REVENUE", "1000000"))
        self.BATCH_SIZE = int(self._get_optional("BATCH_SIZE", "100"))

        # Rate Limiting
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = int(
            self._get_optional("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")
        )
        self.RETRY_MAX_ATTEMPTS = int(self._get_optional("RETRY_MAX_ATTEMPTS", "3"))
        self.RETRY_DELAY_SECONDS = float(
            self._get_optional("RETRY_DELAY_SECONDS", "1.0")
        )

    def _get_required(self, name: str, default: Optional[str] = None) -> str:
        """Get a required configuration value from environment variables.

        Args:
            name: The name of the environment variable.
            default: Optional default value if not found.

        Returns:
            The value of the environment variable or default if provided.

        Raises:
            ConfigError: If the environment variable is not found and no default provided.
        """
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            self.logger.warning(
                "Environment variable %s not found, using default value", name
            )
            return default
        raise ConfigError(
            f"Required environment variable {name} not found and no default provided"
        )

    def _get_optional(self, name: str, default: str = "") -> str:
        """Get an optional configuration value from environment variables.

        Args:
            name: The name of the environment variable.
            default: Default value if not found (default: "").

        Returns:
            The value of the environment variable or the default value.
        """
        if name in os.environ:
            return os.environ[name]
        return default

    def _get_bool(self, name: str) -> bool:
        """Get a boolean configuration value from environment variables.

        Args:
            name: The name of the environment variable.

        Returns:
            True if the environment variable exists and is set to 'true' or '1'.
        """
        return name in os.environ and os.environ[name].lower() in ["true", "1"]

    def validate_for_scraping(self) -> None:
        """Validate configuration required for lead scraping.

        Raises:
            ConfigError: If required scraping configuration is missing.
        """
        if not self.GOOGLE_MAPS_API_KEY:
            raise ConfigError("GOOGLE_MAPS_API_KEY is required for lead scraping")

    def validate_for_research(self) -> None:
        """Validate configuration required for lead research.

        Raises:
            ConfigError: If required research configuration is missing.
        """
        if not self.FIRECRAWL_API_KEY:
            raise ConfigError("FIRECRAWL_API_KEY is required for web scraping")
        if not self.OPENAI_API_KEY:
            raise ConfigError("OPENAI_API_KEY is required for research analysis")

    def validate_for_voice(self) -> None:
        """Validate configuration required for voice agent assembly.

        Raises:
            ConfigError: If required voice configuration is missing.
        """
        if not self.OPENAI_API_KEY:
            raise ConfigError("OPENAI_API_KEY is required for voice agents")
        if not self.TWILIO_ACCOUNT_SID or not self.TWILIO_AUTH_TOKEN:
            raise ConfigError("Twilio credentials required for voice calls")

    def validate_for_deployment(self) -> None:
        """Validate configuration required for demo site deployment.

        Raises:
            ConfigError: If required deployment configuration is missing.
        """
        if not self.VERCEL_TOKEN:
            raise ConfigError("VERCEL_TOKEN is required for demo site deployment")

    def validate_for_email(self) -> None:
        """Validate configuration required for email delivery.

        Raises:
            ConfigError: If required email configuration is missing.
        """
        if not self.SENDGRID_API_KEY:
            raise ConfigError("SENDGRID_API_KEY is required for email delivery")
        if not self.SENDGRID_FROM_EMAIL:
            raise ConfigError("SENDGRID_FROM_EMAIL is required for email delivery")

    def validate_for_database(self) -> None:
        """Validate configuration required for database operations.

        Raises:
            ConfigError: If required database configuration is missing.
        """
        if not self.DATABASE_URL:
            raise ConfigError("DATABASE_URL is required for database operations")

    def validate_all(self) -> None:
        """Validate all required configuration for full pipeline.

        Raises:
            ConfigError: If any required configuration is missing.
        """
        self.validate_for_scraping()
        self.validate_for_research()
        self.validate_for_voice()
        self.validate_for_deployment()
        self.validate_for_email()
        self.validate_for_database()

    def get_database_connection_args(self) -> dict:
        """Get database connection arguments for SQLAlchemy.

        Returns:
            Dictionary of connection arguments.
        """
        return {
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_pre_ping": True,
        }

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if APP_ENV is 'prod' or 'production'.
        """
        return self.APP_ENV.lower() in ["prod", "production"]

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if APP_ENV is 'dev' or 'development'.
        """
        return self.APP_ENV.lower() in ["dev", "development"]

    def get_log_level(self) -> int:
        """Get logging level as integer.

        Returns:
            Logging level constant (e.g., logging.INFO).
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(self.LOG_LEVEL.upper(), logging.INFO)


# Create global singleton instance
config = Config()
