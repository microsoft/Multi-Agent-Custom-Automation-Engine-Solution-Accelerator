"""Voice server for Twilio-OpenAI Realtime API proxy.

This module provides a FastAPI WebSocket server that proxies audio
between Twilio Media Streams and OpenAI's Realtime API for the
AI voice receptionist system.

Endpoints:
- POST /twilio/incoming - Twilio webhook for incoming calls
- WebSocket /voice/{lead_id} - Audio streaming proxy
- GET /health - Health check endpoint
"""

from .main import app

__all__ = ["app"]
