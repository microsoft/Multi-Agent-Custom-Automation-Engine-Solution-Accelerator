# app.py
import logging
from contextlib import asynccontextmanager

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from common.config.app_config import config
from common.models.messages_af import UserLanguage
from middleware.health_check import HealthCheckMiddleware
from v4.api.router import app_v4
from v4.config.agent_registry import agent_registry

# Configure logging levels FIRST, before any logging calls
logging.basicConfig(
    level=getattr(logging, config.AZURE_BASIC_LOGGING_LEVEL.upper(), logging.INFO)
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage FastAPI application lifecycle - startup and shutdown."""
    logger = logging.getLogger(__name__)

    # Startup
    logger.info("🚀 Starting MACAE application...")
    # Work-event reconciler: the only path that transitions parked plans.
    # Pending events survive a restart; this task drains them.
    from v4.control.reconciler import Reconciler, get_reconciler, set_reconciler
    from v4.control.workspace_capability import RegistryProvider

    # Incremento 4: el loop origina trabajo (INC vencidos) en cuanto el registro
    # es alcanzable. Descubrirlo NO se resuelve en el arranque: el clon llega al
    # share cuando alguien lo crea desde la UI, así que el provider se reintenta
    # en cada barrido hasta vincular.
    registry_provider = RegistryProvider()
    # Carril reactivo: las alertas disparadas en Azure Monitor entran como
    # señales y se emparejan con las firmas de las INC. Sin suscripción/grupo
    # configurados la fuente es None y el loop sólo origina trabajo por
    # vencimiento (era el estado de prod: la fuente existía pero no se inyectaba).
    from v4.control.alert_source import AzureMonitorAlertSource

    alert_source = AzureMonitorAlertSource.from_config(config)
    set_reconciler(Reconciler(provider=registry_provider, alerts=alert_source))
    reconciler = get_reconciler()
    reconciler.start()
    yield

    # Shutdown
    logger.info("🛑 Shutting down MACAE application...")
    try:
        await reconciler.stop()
        await registry_provider.aclose()
        if alert_source is not None:
            await alert_source.aclose()
    except Exception as rec_e:
        logger.warning(f"Reconciler stop warning (non-fatal): {rec_e}")
    try:
        # Clean up all agents from Azure AI Foundry when container stops
        await agent_registry.cleanup_all_agents()
        logger.info("✅ Agent cleanup completed successfully")

        # Close process-scoped shared async resources (Managed Identity credential
        # and AIProjectClient). These are borrowed by agents but owned by the
        # process, so they are closed exactly once here — never on agent close().
        # Close the generated-file blob transport BEFORE the shared credential
        # it borrows is closed below.
        try:
            from v4.common.services.generated_file_store import GeneratedFileStore

            await GeneratedFileStore.aclose_instance()
        except Exception as gfs_e:
            logger.warning(f"GeneratedFileStore cleanup warning (non-fatal): {gfs_e}")

        try:
            from common.services.chat_cosmos_service import aclose_chat_cosmos_service
            from common.services.checkpoint_storage import close_checkpoint_storage
            from common.services.event_store import close_event_store

            await aclose_chat_cosmos_service()
            await close_checkpoint_storage()
            await close_event_store()
        except Exception as ckpt_e:
            logger.warning(f"Checkpoint storage cleanup warning (non-fatal): {ckpt_e}")
        try:
            await config.aclose_shared_resources()
            logger.info("✅ Shared async resources closed")
        except Exception as cfg_e:
            logger.warning(f"Shared resource cleanup warning (non-fatal): {cfg_e}")

        # Clean up global MCP resource service if it exists. Close-and-unbind:
        # closing the object while the module global kept pointing at it left
        # a dead client for any request after shutdown began.
        try:
            from v4.common.services.mcp_resource_service import (
                aclose_mcp_resource_service,
            )

            await aclose_mcp_resource_service()
            logger.info("✅ MCP Resource Service cleanup completed")
        except Exception as mcp_e:
            logger.warning(f"MCP cleanup warning (non-fatal): {mcp_e}")

        # Close the Inspector bridge's httpx client (same singleton pattern)
        try:
            from v4.common.services.mcp_inspector_bridge import aclose_inspector_bridge

            await aclose_inspector_bridge()
        except Exception as ib_e:
            logger.warning(f"Inspector bridge cleanup warning (non-fatal): {ib_e}")

        # Close the memory-store CosmosClient. close_all() (close + unbind)
        # existed all along — nothing ever called it, so the client's aiohttp
        # session died unclosed at GC (contract-suite ResourceWarning gate).
        try:
            from common.database.database_factory import DatabaseFactory

            await DatabaseFactory.close_all()
        except Exception as db_e:
            logger.warning(f"DatabaseFactory cleanup warning (non-fatal): {db_e}")

    except ImportError as ie:
        logger.error(f"❌ Could not import agent_registry: {ie}")
    except Exception as e:
        logger.error(f"❌ Error during shutdown cleanup: {e}")

    logger.info("👋 MACAE application shutdown complete")


# Configure logging levels from environment variables
# logging.basicConfig(level=getattr(logging, config.AZURE_BASIC_LOGGING_LEVEL.upper(), logging.INFO))

# Configure Azure package logging levels
azure_level = getattr(
    logging, config.AZURE_PACKAGE_LOGGING_LEVEL.upper(), logging.WARNING
)
# Parse comma-separated logging packages
if config.AZURE_LOGGING_PACKAGES:
    packages = [
        pkg.strip() for pkg in config.AZURE_LOGGING_PACKAGES.split(",") if pkg.strip()
    ]
    for logger_name in packages:
        logging.getLogger(logger_name).setLevel(azure_level)

logging.getLogger("opentelemetry.sdk").setLevel(logging.ERROR)

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)

# Suppress noisy Azure Monitor exporter "Transmission succeeded" logs
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)

# Initialize the FastAPI app
app = FastAPI(lifespan=lifespan)


@app.exception_handler(PermissionError)
async def _auth_required(request: Request, exc: PermissionError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=401, content={"detail": str(exc)})


frontend_url = config.FRONTEND_SITE_NAME
# Configure Azure Monitor and instrument FastAPI for OpenTelemetry
# This enables automatic request tracing, dependency tracking, and proper operation_id
if config.APPLICATIONINSIGHTS_CONNECTION_STRING:
    # Configure Application Insights telemetry with live metrics
    configure_azure_monitor(
        connection_string=config.APPLICATIONINSIGHTS_CONNECTION_STRING,
        enable_live_metrics=True,
    )

    FastAPIInstrumentor.instrument_app(
        app,
        exclude_spans=["receive", "send"],
    )
    logging.info(
        "Application Insights configured with live metrics and WebSocket filtering"
    )
else:
    logging.warning(
        "No Application Insights connection string found. Telemetry disabled."
    )

# CORS — restrict to frontend origin in production, allow all in dev
_cors_origins = (
    ["*"]
    if str(config.APP_ENV).lower() == "dev"
    else [origin.strip() for origin in frontend_url.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure health check
app.add_middleware(HealthCheckMiddleware, password="", checks={})
# v4 endpoints
app.include_router(app_v4)
logging.info("Added health check middleware")


@app.get("/config")
async def get_frontend_config():
    """Expose runtime frontend config for local/prod parity."""
    return {
        "API_URL": "/api",
        "ENABLE_AUTH": str(config.APP_ENV).lower() != "dev",
    }


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
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=False,
    )
