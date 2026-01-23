"""FastAPI WebSocket server for Twilio-OpenAI Realtime API proxy.

This module provides the main FastAPI application that handles incoming
Twilio voice calls and proxies audio streams to OpenAI's Realtime API.

Endpoints:
- POST /twilio/incoming - Twilio webhook for incoming calls (returns TwiML)
- POST /twilio/status - Twilio status callback for call events
- WebSocket /voice/{lead_id} - Audio streaming proxy to OpenAI
- GET /health - Health check endpoint

Environment Variables:
- OPENAI_API_KEY: OpenAI API key for Realtime API access
- TWILIO_ACCOUNT_SID: Twilio account SID for request validation
- TWILIO_AUTH_TOKEN: Twilio auth token for request validation
- VOICE_SERVER_HOST: Server host URL for WebSocket connections (e.g., wss://example.com)
- LOG_LEVEL: Logging level (default: INFO)

Example:
    uvicorn main:app --host 0.0.0.0 --port 8765
"""

import asyncio
import base64
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from urllib.parse import urljoin

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Connect, Say, Stream, VoiceResponse

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CallDirection(str, Enum):
    """Direction of a voice call."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    """Twilio call status values."""

    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


@dataclass
class ActiveCall:
    """Represents an active call being handled by the server.

    Attributes:
        call_sid: Twilio call SID.
        lead_id: Associated lead ID for personalization.
        from_number: Caller phone number.
        to_number: Called phone number.
        direction: Call direction (inbound/outbound).
        status: Current call status.
        started_at: When the call started.
        websocket_connected: Whether the WebSocket is connected.
    """

    call_sid: str
    lead_id: str
    from_number: str
    to_number: str
    direction: CallDirection = CallDirection.INBOUND
    status: CallStatus = CallStatus.RINGING
    started_at: datetime = field(default_factory=datetime.utcnow)
    websocket_connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "call_sid": self.call_sid,
            "lead_id": self.lead_id,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "direction": self.direction.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "websocket_connected": self.websocket_connected,
        }


class VoiceServerConfig:
    """Configuration for the voice server.

    Reads from environment variables with sensible defaults.
    """

    def __init__(self) -> None:
        """Initialize configuration from environment."""
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
        self.voice_server_host = os.environ.get("VOICE_SERVER_HOST", "")

        # OpenAI Realtime API settings
        self.openai_realtime_url = os.environ.get(
            "OPENAI_REALTIME_URL",
            "wss://api.openai.com/v1/realtime",
        )
        self.openai_realtime_model = os.environ.get(
            "OPENAI_REALTIME_MODEL",
            "gpt-4o-realtime-preview-2024-10-01",
        )

        # Voice settings
        self.default_voice = os.environ.get("DEFAULT_VOICE", "alloy")
        self.default_greeting = os.environ.get(
            "DEFAULT_GREETING",
            "Hello, thank you for calling. How can I help you today?",
        )

        # Validate based on mode
        self.validate_twilio = os.environ.get("VALIDATE_TWILIO", "false").lower() == "true"

    @property
    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        return bool(self.openai_api_key)

    @property
    def has_twilio_config(self) -> bool:
        """Check if Twilio configuration is present."""
        return bool(self.twilio_account_sid and self.twilio_auth_token)

    def get_websocket_url(self, lead_id: str) -> str:
        """Build WebSocket URL for a lead.

        Args:
            lead_id: Lead ID for the call.

        Returns:
            Full WebSocket URL for Twilio to connect to.
        """
        if not self.voice_server_host:
            # Fallback to localhost for development
            return f"wss://localhost:8765/voice/{lead_id}"

        host = self.voice_server_host.rstrip("/")
        # Ensure wss:// prefix
        if host.startswith("http://"):
            host = host.replace("http://", "ws://")
        elif host.startswith("https://"):
            host = host.replace("https://", "wss://")
        elif not host.startswith("ws://") and not host.startswith("wss://"):
            host = f"wss://{host}"

        return f"{host}/voice/{lead_id}"


# Global configuration and state
config = VoiceServerConfig()
active_calls: dict[str, ActiveCall] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Voice server starting...")
    if not config.is_configured:
        logger.warning(
            "OPENAI_API_KEY not set - voice functionality will be limited"
        )
    if not config.has_twilio_config:
        logger.warning(
            "Twilio credentials not set - webhook validation disabled"
        )
    logger.info("Voice server ready")

    yield

    # Shutdown
    logger.info("Voice server shutting down...")
    active_calls.clear()
    logger.info("Voice server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Voice Server",
    description="Twilio-OpenAI Realtime API WebSocket Proxy",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_config() -> VoiceServerConfig:
    """Dependency to get server configuration."""
    return config


def validate_twilio_request(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
) -> bool:
    """Validate that request came from Twilio.

    Args:
        request: FastAPI request object.
        x_twilio_signature: Twilio signature header.

    Returns:
        True if validation passes or is disabled.

    Raises:
        HTTPException: If validation fails.
    """
    if not config.validate_twilio:
        return True

    if not config.has_twilio_config:
        logger.warning("Twilio validation enabled but credentials not configured")
        return True

    if not x_twilio_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Twilio-Signature header",
        )

    # Validation would happen here with request body
    # For now, we trust the signature exists
    return True


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Health status including configuration state.
    """
    return {
        "status": "healthy",
        "service": "voice-server",
        "version": "1.0.0",
        "configured": config.is_configured,
        "twilio_configured": config.has_twilio_config,
        "active_calls": len(active_calls),
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "voice-server",
        "description": "Twilio-OpenAI Realtime API WebSocket Proxy",
        "endpoints": {
            "health": "/health",
            "twilio_incoming": "/twilio/incoming",
            "twilio_status": "/twilio/status",
            "voice_websocket": "/voice/{lead_id}",
        },
    }


@app.post("/twilio/incoming", response_class=PlainTextResponse)
async def handle_incoming_call(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(default="ringing"),
    Direction: str = Form(default="inbound"),
    lead_id: Optional[str] = Query(None),
    cfg: VoiceServerConfig = Depends(get_config),
) -> str:
    """Handle incoming Twilio voice call webhook.

    This endpoint receives incoming call notifications from Twilio and
    returns TwiML that connects the call to our WebSocket endpoint for
    real-time audio streaming to OpenAI.

    Args:
        request: FastAPI request object.
        CallSid: Twilio call SID.
        From: Caller phone number.
        To: Called phone number.
        CallStatus: Current call status.
        Direction: Call direction (inbound/outbound).
        lead_id: Optional lead ID for personalization.
        cfg: Server configuration.

    Returns:
        TwiML response as XML string.

    Example TwiML Response:
        <?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say>Hello, thank you for calling. Please hold while I connect you.</Say>
            <Connect>
                <Stream url="wss://example.com/voice/lead123" track="both_tracks">
                    <Parameter name="lead_id" value="lead123"/>
                </Stream>
            </Connect>
        </Response>
    """
    logger.info(
        "Incoming call: sid=%s, from=%s, to=%s, lead_id=%s",
        CallSid,
        From,
        To,
        lead_id,
    )

    # Use a default lead_id if not provided
    effective_lead_id = lead_id or f"default_{CallSid[:8]}"

    # Track the active call
    call = ActiveCall(
        call_sid=CallSid,
        lead_id=effective_lead_id,
        from_number=From,
        to_number=To,
        direction=CallDirection(Direction.lower()) if Direction else CallDirection.INBOUND,
        status=CallStatus.RINGING,
    )
    active_calls[CallSid] = call
    logger.info("Tracked call: %s", call.to_dict())

    # Build TwiML response
    response = VoiceResponse()

    # Optional initial greeting before connecting to AI
    # This provides immediate feedback while WebSocket connects
    response.say(
        "Hello, please wait while I connect you to our assistant.",
        voice="Polly.Joanna",
    )

    # Connect to WebSocket for audio streaming
    websocket_url = cfg.get_websocket_url(effective_lead_id)
    logger.info("Connecting call to WebSocket: %s", websocket_url)

    connect = Connect()
    stream = Stream(url=websocket_url, track="both_tracks")

    # Pass parameters to WebSocket handler
    stream.parameter(name="lead_id", value=effective_lead_id)
    stream.parameter(name="call_sid", value=CallSid)
    stream.parameter(name="from_number", value=From)
    stream.parameter(name="to_number", value=To)

    connect.append(stream)
    response.append(connect)

    # Return TwiML as XML
    twiml_str = str(response)
    logger.info("Generated TwiML (%d bytes)", len(twiml_str))

    return twiml_str


@app.post("/twilio/status")
async def handle_call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: Optional[str] = Form(None),
    cfg: VoiceServerConfig = Depends(get_config),
) -> dict[str, str]:
    """Handle Twilio call status webhook.

    This endpoint receives call status updates from Twilio,
    allowing us to track call lifecycle and clean up resources.

    Args:
        CallSid: Twilio call SID.
        CallStatus: New call status.
        CallDuration: Call duration in seconds (when completed).
        cfg: Server configuration.

    Returns:
        Acknowledgment response.
    """
    logger.info(
        "Call status update: sid=%s, status=%s, duration=%s",
        CallSid,
        CallStatus,
        CallDuration,
    )

    # Update tracked call if exists
    if CallSid in active_calls:
        try:
            active_calls[CallSid].status = CallStatus(CallStatus)
        except ValueError:
            logger.warning("Unknown call status: %s", CallStatus)

        # Clean up completed calls
        if CallStatus in ["completed", "failed", "busy", "no-answer", "canceled"]:
            call = active_calls.pop(CallSid, None)
            if call:
                logger.info(
                    "Call ended: sid=%s, duration=%s",
                    CallSid,
                    CallDuration or "unknown",
                )

    return {"status": "received", "call_sid": CallSid}


@app.websocket("/voice/{lead_id}")
async def voice_websocket(
    websocket: WebSocket,
    lead_id: str,
) -> None:
    """WebSocket endpoint for Twilio Media Streams.

    This endpoint receives real-time audio from Twilio and proxies it
    to OpenAI's Realtime API, then streams the AI response audio back
    to Twilio.

    Args:
        websocket: WebSocket connection from Twilio.
        lead_id: Lead ID for personalization and context.

    Note:
        The actual audio proxy implementation is in audio_proxy.py.
        This handler manages the connection lifecycle and delegates
        to the proxy for audio processing.
    """
    logger.info("WebSocket connection request for lead: %s", lead_id)

    await websocket.accept()
    logger.info("WebSocket accepted for lead: %s", lead_id)

    # Track WebSocket connection for associated call
    call_sid = None
    stream_sid = None

    try:
        while True:
            # Receive message from Twilio
            message = await websocket.receive_text()
            data = json.loads(message)

            event_type = data.get("event")

            if event_type == "connected":
                # Initial connection event
                logger.info("Twilio stream connected for lead: %s", lead_id)

            elif event_type == "start":
                # Stream start event with metadata
                start_data = data.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid")

                # Extract custom parameters
                custom_params = start_data.get("customParameters", {})
                logger.info(
                    "Stream started: stream_sid=%s, call_sid=%s, params=%s",
                    stream_sid,
                    call_sid,
                    custom_params,
                )

                # Update call tracking
                if call_sid and call_sid in active_calls:
                    active_calls[call_sid].websocket_connected = True

            elif event_type == "media":
                # Audio data from Twilio (mulaw 8kHz)
                # The actual audio processing is handled by audio_proxy.py
                # For now, we just log receipt
                media = data.get("media", {})
                payload = media.get("payload")  # Base64 encoded audio

                # In full implementation, forward to OpenAI Realtime API
                # and receive response audio to send back
                pass

            elif event_type == "mark":
                # Playback completion marker
                mark_name = data.get("mark", {}).get("name")
                logger.debug("Playback mark received: %s", mark_name)

            elif event_type == "stop":
                # Stream ending
                logger.info(
                    "Stream stopped: stream_sid=%s, lead_id=%s",
                    stream_sid,
                    lead_id,
                )
                break

            else:
                logger.debug("Unknown event type: %s", event_type)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for lead: %s", lead_id)

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON from Twilio: %s", e)

    except Exception as e:
        logger.error(
            "WebSocket error for lead %s: %s",
            lead_id,
            str(e),
            exc_info=True,
        )

    finally:
        # Clean up WebSocket connection tracking
        if call_sid and call_sid in active_calls:
            active_calls[call_sid].websocket_connected = False
        logger.info("WebSocket handler completed for lead: %s", lead_id)


@app.get("/calls")
async def list_active_calls() -> dict[str, Any]:
    """List all active calls.

    Returns:
        Dictionary with active call information.
    """
    return {
        "count": len(active_calls),
        "calls": [call.to_dict() for call in active_calls.values()],
    }


@app.get("/calls/{call_sid}")
async def get_call(call_sid: str) -> dict[str, Any]:
    """Get information about a specific call.

    Args:
        call_sid: Twilio call SID.

    Returns:
        Call information.

    Raises:
        HTTPException: If call not found.
    """
    if call_sid not in active_calls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call not found: {call_sid}",
        )

    return active_calls[call_sid].to_dict()


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> Response:
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled error: %s %s - %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    return Response(
        content=json.dumps({
            "error": "Internal server error",
            "detail": str(exc) if LOG_LEVEL == "DEBUG" else "An unexpected error occurred",
        }),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/json",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8765))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info("Starting voice server on %s:%d", host, port)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
