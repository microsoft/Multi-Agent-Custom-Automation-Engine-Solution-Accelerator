# app_kernel.py
import logging

from contextlib import asynccontextmanager


from azure.monitor.opentelemetry import configure_azure_monitor
from common.config.app_config import config
from common.models.messages_kernel import UserLanguage

# FastAPI imports
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from middleware.health_check import HealthCheckMiddleware
from v3.api.router import app_v3

# Azure monitoring

# Semantic Kernel imports
from v3.config.agent_registry import agent_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage FastAPI application lifecycle - startup and shutdown."""
    logger = logging.getLogger(__name__)

    # Startup
    logger.info("🚀 Starting MACAE application...")
    yield

    # Shutdown
    logger.info("🛑 Shutting down MACAE application...")
    try:
        # Clean up all agents from Azure AI Foundry when container stops
        await agent_registry.cleanup_all_agents()
        logger.info("✅ Agent cleanup completed successfully")

    except ImportError as ie:
        logger.error(f"❌ Could not import agent_registry: {ie}")
    except Exception as e:
        logger.error(f"❌ Error during shutdown cleanup: {e}")

    logger.info("👋 MACAE application shutdown complete")


# Check if the Application Insights Instrumentation Key is set in the environment variables
connection_string = config.APPLICATIONINSIGHTS_CONNECTION_STRING
if connection_string:
    # Configure Application Insights if the Instrumentation Key is found
    configure_azure_monitor(connection_string=connection_string)
    logging.info(
        "Application Insights configured with the provided Instrumentation Key"
    )
else:
    # Log a warning if the Instrumentation Key is not found
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress INFO logs from 'azure.core.pipeline.policies.http_logging_policy'
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)

# # Suppress info logs from OpenTelemetry exporter
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)

# Initialize the FastAPI app
app = FastAPI(lifespan=lifespan)

frontend_url = config.FRONTEND_SITE_NAME

# Add this near the top of your app.py, after initializing the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure health check
app.add_middleware(HealthCheckMiddleware, password="", checks={})
# v3 endpoints
app.include_router(app_v3)
logging.info("Added health check middleware")


@app.post("/api/user_browser_language")
async def user_browser_language_endpoint(user_language: UserLanguage, request: Request):
    """
    Receive the user's browser language.

    ---
    tags:
      - User
    parameters:
      - name: language
        in: query
        type: string
        required: true
        description: The user's browser language
    responses:
      200:
        description: Language received successfully
        schema:
          type: object
          properties:
            status:
              type: string
              description: Confirmation message
    """
    config.set_user_local_browser_language(user_language.language)

    # Log the received language for the user
    logging.info(f"Received browser language '{user_language}' for user ")

    return {"status": "Language received successfully"}


# Run the app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_kernel:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=False,
    )
