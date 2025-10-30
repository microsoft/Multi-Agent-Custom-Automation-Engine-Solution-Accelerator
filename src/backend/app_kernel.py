# app_kernel.py
import asyncio
import logging
import os
import warnings
# Azure monitoring
import re
import uuid
from typing import Dict, List, Optional

from azure.monitor.opentelemetry import configure_azure_monitor
from common.config.app_config import config
from common.models.messages_kernel import UserLanguage
# FastAPI imports
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
# Local imports
from middleware.health_check import HealthCheckMiddleware
from v3.api.router import app_v3
# Semantic Kernel imports
from v3.orchestration.orchestration_manager import OrchestrationManager

# Configure logging FIRST before any Azure imports
logging.basicConfig(level=logging.INFO)

# Suppress Pydantic warnings about model_ namespace conflicts (from third-party libraries)
warnings.filterwarnings("ignore", message=".*Field.*has conflict with protected namespace.*model_.*")

# Suppress noisy Azure and OpenTelemetry loggers BEFORE configuring monitoring
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)
logging.getLogger("azure.identity._credentials.environment").setLevel(logging.WARNING)
logging.getLogger("azure.identity._credentials.managed_identity").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(logging.CRITICAL)
logging.getLogger("azure.monitor.opentelemetry.exporter.statsbeat._manager").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.resource.detector.azure.vm").setLevel(logging.ERROR)

# Check if the Application Insights Instrumentation Key is set in the environment variables
connection_string = config.APPLICATIONINSIGHTS_CONNECTION_STRING
if connection_string:
    # Configure Application Insights with resource detectors disabled for local development
    # This prevents the Azure VM metadata errors when running locally
    try:
        configure_azure_monitor(
            connection_string=connection_string,
            disable_offline_storage=True,  # Disable offline storage for cleaner local dev
        )
        logging.info("Application Insights configured successfully")
    except Exception as e:
        logging.warning(f"Application Insights configuration had warnings (expected for local dev): {e}")
else:
    # Log a warning if the Instrumentation Key is not found
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Initialize the FastAPI app
app = FastAPI()

frontend_url = config.FRONTEND_SITE_NAME

# Add CORS middleware FIRST to ensure it handles all responses including errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Configure health check
app.add_middleware(HealthCheckMiddleware, password="", checks={})
# v3 endpoints
app.include_router(app_v3)
logging.info("Added health check middleware")


# Custom exception handlers to ensure CORS headers are always present
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and ensure CORS headers are present."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions and ensure CORS headers are present."""
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


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

    uvicorn.run("app_kernel:app", host="127.0.0.1", port=8000, reload=True, log_level="info", access_log=False)
