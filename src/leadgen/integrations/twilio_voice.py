"""Twilio voice webhook configuration utilities.

This module provides utilities for configuring Twilio voice webhooks,
generating TwiML responses, and managing phone number configurations
for the AI voice receptionist system.

Features:
- Phone number webhook configuration
- TwiML generation for WebSocket streaming
- Call routing to OpenAI Realtime API via WebSocket proxy
- Incoming call handling with customizable greetings
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from urllib.parse import urljoin

from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_VOICE = "Polly.Joanna"  # AWS Polly voice for Say verb
SUPPORTED_VOICES = [
    "alice", "man", "woman",
    "Polly.Joanna", "Polly.Matthew", "Polly.Amy", "Polly.Brian",
    "Polly.Ivy", "Polly.Kendra", "Polly.Kimberly", "Polly.Salli",
]


class WebhookMethod(str, Enum):
    """HTTP methods for webhook configuration."""

    POST = "POST"
    GET = "GET"


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


class TwilioVoiceError(Exception):
    """Base exception for Twilio voice errors."""

    pass


class TwilioAuthError(TwilioVoiceError):
    """Raised when Twilio authentication fails."""

    pass


class TwilioConfigError(TwilioVoiceError):
    """Raised when configuration is invalid."""

    pass


class TwilioPhoneNumberError(TwilioVoiceError):
    """Raised when phone number operations fail."""

    pass


class TwilioCallError(TwilioVoiceError):
    """Raised when call operations fail."""

    pass


@dataclass
class PhoneNumberInfo:
    """Represents information about a Twilio phone number.

    Attributes:
        sid: Phone number SID.
        phone_number: E.164 formatted phone number.
        friendly_name: Human-readable name.
        voice_url: URL for incoming voice calls.
        voice_method: HTTP method for voice webhook.
        status_callback: URL for call status updates.
        capabilities: Dict of capabilities (voice, sms, mms).
        success: Whether the operation was successful.
        error: Error message if operation failed.
    """

    sid: str
    phone_number: str
    friendly_name: Optional[str] = None
    voice_url: Optional[str] = None
    voice_method: str = "POST"
    status_callback: Optional[str] = None
    capabilities: dict[str, bool] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sid": self.sid,
            "phone_number": self.phone_number,
            "friendly_name": self.friendly_name,
            "voice_url": self.voice_url,
            "voice_method": self.voice_method,
            "status_callback": self.status_callback,
            "capabilities": self.capabilities,
            "success": self.success,
            "error": self.error,
        }

    @property
    def has_voice(self) -> bool:
        """Check if phone number has voice capability."""
        return self.capabilities.get("voice", False)

    @property
    def is_configured(self) -> bool:
        """Check if phone number has voice webhook configured."""
        return bool(self.voice_url)


@dataclass
class CallInfo:
    """Represents information about a Twilio call.

    Attributes:
        sid: Call SID.
        from_number: Caller phone number.
        to_number: Called phone number.
        status: Call status.
        direction: Call direction (inbound/outbound).
        duration: Call duration in seconds.
        start_time: Call start timestamp.
        end_time: Call end timestamp.
        success: Whether the operation was successful.
        error: Error message if operation failed.
    """

    sid: str
    from_number: str
    to_number: str
    status: Optional[str] = None
    direction: Optional[str] = None
    duration: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sid": self.sid,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "status": self.status,
            "direction": self.direction,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success": self.success,
            "error": self.error,
        }

    @property
    def is_active(self) -> bool:
        """Check if call is currently active."""
        return self.status in [CallStatus.QUEUED, CallStatus.RINGING, CallStatus.IN_PROGRESS]

    @property
    def is_completed(self) -> bool:
        """Check if call has completed."""
        return self.status == CallStatus.COMPLETED


@dataclass
class TwiMLResponse:
    """Represents a generated TwiML response.

    Attributes:
        content: Raw TwiML XML string.
        content_type: MIME type for response.
        success: Whether generation was successful.
        error: Error message if generation failed.
    """

    content: str
    content_type: str = "application/xml"
    success: bool = True
    error: Optional[str] = None

    def __str__(self) -> str:
        """Return TwiML content."""
        return self.content


class TwilioVoiceClient:
    """Client for Twilio voice webhook configuration.

    Provides methods for configuring phone numbers, generating TwiML,
    and managing call routing for the AI voice receptionist system.

    Attributes:
        account_sid: Twilio account SID.
        auth_token: Twilio auth token.
        phone_number: Default Twilio phone number for outbound calls.

    Example:
        >>> client = TwilioVoiceClient()
        >>> await client.configure_phone_number(
        ...     phone_number="+15551234567",
        ...     voice_url="https://example.com/twilio/incoming",
        ... )
        >>> twiml = client.generate_stream_twiml(
        ...     websocket_url="wss://example.com/voice/lead123",
        ...     greeting="Hello, this is Acme Dental. How can I help you?",
        ... )
        >>> print(twiml)
        <?xml version="1.0" encoding="UTF-8"?>...
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        phone_number: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize Twilio voice client.

        Args:
            account_sid: Twilio account SID. Defaults to TWILIO_ACCOUNT_SID env var.
            auth_token: Twilio auth token. Defaults to TWILIO_AUTH_TOKEN env var.
            phone_number: Default phone number. Defaults to TWILIO_PHONE_NUMBER env var.
            timeout_seconds: Request timeout in seconds. Defaults to 30.

        Raises:
            ValueError: If required credentials are not provided.
        """
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        self.phone_number = phone_number or os.environ.get("TWILIO_PHONE_NUMBER")

        if not self.account_sid or not self.auth_token:
            raise ValueError(
                "Twilio credentials required. Set TWILIO_ACCOUNT_SID and "
                "TWILIO_AUTH_TOKEN environment variables or pass them as parameters."
            )

        self.timeout_seconds = timeout_seconds
        self._client = TwilioClient(self.account_sid, self.auth_token)
        logger.info(
            "TwilioVoiceClient initialized (account=%s...)",
            self.account_sid[:8] if self.account_sid else "none",
        )

    def _parse_phone_number(self, pn: Any) -> PhoneNumberInfo:
        """Parse raw API response into PhoneNumberInfo.

        Args:
            pn: Phone number object from API response.

        Returns:
            Parsed PhoneNumberInfo object.
        """
        capabilities = {}
        if hasattr(pn, "capabilities"):
            caps = pn.capabilities
            if isinstance(caps, dict):
                capabilities = caps
            else:
                capabilities = {
                    "voice": getattr(caps, "voice", False),
                    "sms": getattr(caps, "sms", False),
                    "mms": getattr(caps, "mms", False),
                }

        return PhoneNumberInfo(
            sid=pn.sid,
            phone_number=pn.phone_number,
            friendly_name=getattr(pn, "friendly_name", None),
            voice_url=getattr(pn, "voice_url", None),
            voice_method=getattr(pn, "voice_method", "POST"),
            status_callback=getattr(pn, "status_callback", None),
            capabilities=capabilities,
            success=True,
            error=None,
        )

    def _parse_call(self, call: Any) -> CallInfo:
        """Parse raw API response into CallInfo.

        Args:
            call: Call object from API response.

        Returns:
            Parsed CallInfo object.
        """
        return CallInfo(
            sid=call.sid,
            from_number=getattr(call, "from_", "") or getattr(call, "from_formatted", ""),
            to_number=getattr(call, "to", "") or getattr(call, "to_formatted", ""),
            status=getattr(call, "status", None),
            direction=getattr(call, "direction", None),
            duration=int(call.duration) if getattr(call, "duration", None) else None,
            start_time=str(call.start_time) if getattr(call, "start_time", None) else None,
            end_time=str(call.end_time) if getattr(call, "end_time", None) else None,
            success=True,
            error=None,
        )

    async def get_phone_number(self, phone_number: str) -> PhoneNumberInfo:
        """Get information about a Twilio phone number.

        Args:
            phone_number: E.164 formatted phone number (e.g., +15551234567).

        Returns:
            PhoneNumberInfo with current configuration.

        Raises:
            TwilioPhoneNumberError: If phone number not found or lookup fails.
        """
        logger.info("Getting phone number info: %s", phone_number)

        loop = asyncio.get_event_loop()

        try:
            numbers = await loop.run_in_executor(
                None,
                lambda: self._client.incoming_phone_numbers.list(
                    phone_number=phone_number
                ),
            )

            if not numbers:
                raise TwilioPhoneNumberError(
                    f"Phone number not found in account: {phone_number}"
                )

            result = self._parse_phone_number(numbers[0])
            logger.info(
                "Retrieved phone number: %s (voice_url=%s)",
                result.phone_number,
                result.voice_url,
            )
            return result

        except TwilioPhoneNumberError:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to get phone number: %s", error_msg)

            if "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioPhoneNumberError(
                    f"Failed to get phone number: {error_msg}"
                ) from e

    async def configure_phone_number(
        self,
        phone_number: str,
        voice_url: str,
        voice_method: WebhookMethod = WebhookMethod.POST,
        voice_fallback_url: Optional[str] = None,
        status_callback: Optional[str] = None,
        status_callback_method: WebhookMethod = WebhookMethod.POST,
        friendly_name: Optional[str] = None,
    ) -> PhoneNumberInfo:
        """Configure a phone number for voice webhooks.

        Sets up the voice webhook URL that Twilio calls when an incoming
        call is received on this phone number.

        Args:
            phone_number: E.164 formatted phone number to configure.
            voice_url: URL Twilio should request for incoming calls.
            voice_method: HTTP method for voice webhook. Defaults to POST.
            voice_fallback_url: Fallback URL if primary fails.
            status_callback: URL for call status updates.
            status_callback_method: HTTP method for status callback.
            friendly_name: Human-readable name for the number.

        Returns:
            PhoneNumberInfo with updated configuration.

        Raises:
            TwilioPhoneNumberError: If configuration fails.
        """
        logger.info(
            "Configuring phone number %s with voice_url=%s",
            phone_number,
            voice_url,
        )

        loop = asyncio.get_event_loop()

        try:
            # Find the phone number SID
            numbers = await loop.run_in_executor(
                None,
                lambda: self._client.incoming_phone_numbers.list(
                    phone_number=phone_number
                ),
            )

            if not numbers:
                raise TwilioPhoneNumberError(
                    f"Phone number not found in account: {phone_number}"
                )

            pn_sid = numbers[0].sid

            # Build update kwargs
            update_kwargs: dict[str, Any] = {
                "voice_url": voice_url,
                "voice_method": voice_method.value,
            }

            if voice_fallback_url:
                update_kwargs["voice_fallback_url"] = voice_fallback_url
                update_kwargs["voice_fallback_method"] = voice_method.value

            if status_callback:
                update_kwargs["status_callback"] = status_callback
                update_kwargs["status_callback_method"] = status_callback_method.value

            if friendly_name:
                update_kwargs["friendly_name"] = friendly_name

            # Update the phone number
            updated_pn = await loop.run_in_executor(
                None,
                lambda: self._client.incoming_phone_numbers(pn_sid).update(
                    **update_kwargs
                ),
            )

            result = self._parse_phone_number(updated_pn)
            logger.info(
                "Configured phone number: %s (voice_url=%s)",
                result.phone_number,
                result.voice_url,
            )
            return result

        except TwilioPhoneNumberError:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to configure phone number: %s", error_msg)

            if "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioPhoneNumberError(
                    f"Failed to configure phone number: {error_msg}"
                ) from e

    async def list_phone_numbers(
        self,
        voice_enabled: bool = True,
        limit: int = 100,
    ) -> list[PhoneNumberInfo]:
        """List phone numbers in the Twilio account.

        Args:
            voice_enabled: Filter to voice-enabled numbers only.
            limit: Maximum number of results.

        Returns:
            List of PhoneNumberInfo objects.

        Raises:
            TwilioVoiceError: If listing fails.
        """
        logger.info("Listing phone numbers (voice_enabled=%s, limit=%d)", voice_enabled, limit)

        loop = asyncio.get_event_loop()

        try:
            numbers = await loop.run_in_executor(
                None,
                lambda: self._client.incoming_phone_numbers.list(limit=limit),
            )

            result = []
            for pn in numbers:
                info = self._parse_phone_number(pn)
                if voice_enabled and not info.has_voice:
                    continue
                result.append(info)

            logger.info("Listed %d phone numbers", len(result))
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to list phone numbers: %s", error_msg)

            if "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioVoiceError(f"Failed to list phone numbers: {error_msg}") from e

    def generate_stream_twiml(
        self,
        websocket_url: str,
        greeting: Optional[str] = None,
        greeting_voice: str = DEFAULT_VOICE,
        track: str = "both_tracks",
        parameters: Optional[dict[str, str]] = None,
    ) -> TwiMLResponse:
        """Generate TwiML for streaming audio to WebSocket.

        Creates TwiML that optionally plays a greeting then connects
        the call audio to a WebSocket for real-time processing with
        OpenAI Realtime API.

        Args:
            websocket_url: WebSocket URL to stream audio to (wss://).
            greeting: Optional greeting message to play before streaming.
            greeting_voice: Voice to use for greeting. Defaults to Polly.Joanna.
            track: Audio track to stream (inbound_track, outbound_track, both_tracks).
            parameters: Custom parameters to pass to WebSocket.

        Returns:
            TwiMLResponse with generated XML.

        Example:
            >>> twiml = client.generate_stream_twiml(
            ...     websocket_url="wss://example.com/voice/lead123",
            ...     greeting="Hello! How can I help you today?",
            ... )
            >>> print(twiml)
            <?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="Polly.Joanna">Hello! How can I help you today?</Say>
                <Connect>
                    <Stream url="wss://example.com/voice/lead123" track="both_tracks"/>
                </Connect>
            </Response>
        """
        logger.info("Generating stream TwiML for WebSocket: %s", websocket_url)

        try:
            response = VoiceResponse()

            # Add greeting if provided
            if greeting:
                response.say(greeting, voice=greeting_voice)

            # Create Connect verb with Stream
            connect = Connect()
            stream = Stream(url=websocket_url, track=track)

            # Add custom parameters if provided
            if parameters:
                for key, value in parameters.items():
                    stream.parameter(name=key, value=value)

            connect.append(stream)
            response.append(connect)

            twiml_content = str(response)
            logger.info("Generated TwiML (%d bytes)", len(twiml_content))

            return TwiMLResponse(
                content=twiml_content,
                content_type="application/xml",
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to generate TwiML: %s", error_msg)
            return TwiMLResponse(
                content="",
                success=False,
                error=f"Failed to generate TwiML: {error_msg}",
            )

    def generate_redirect_twiml(
        self,
        url: str,
        method: WebhookMethod = WebhookMethod.POST,
    ) -> TwiMLResponse:
        """Generate TwiML that redirects to another URL.

        Useful for dynamic routing based on caller or lead ID.

        Args:
            url: URL to redirect the call to.
            method: HTTP method for redirect request.

        Returns:
            TwiMLResponse with redirect XML.
        """
        logger.info("Generating redirect TwiML to: %s", url)

        try:
            response = VoiceResponse()
            response.redirect(url, method=method.value)

            return TwiMLResponse(
                content=str(response),
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to generate redirect TwiML: %s", error_msg)
            return TwiMLResponse(
                content="",
                success=False,
                error=f"Failed to generate redirect TwiML: {error_msg}",
            )

    def generate_say_twiml(
        self,
        message: str,
        voice: str = DEFAULT_VOICE,
        loop: int = 1,
    ) -> TwiMLResponse:
        """Generate TwiML that speaks a message.

        Args:
            message: Text to speak.
            voice: Voice to use.
            loop: Number of times to repeat.

        Returns:
            TwiMLResponse with say XML.
        """
        logger.info("Generating say TwiML: %s...", message[:50])

        try:
            response = VoiceResponse()
            response.say(message, voice=voice, loop=loop)

            return TwiMLResponse(
                content=str(response),
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to generate say TwiML: %s", error_msg)
            return TwiMLResponse(
                content="",
                success=False,
                error=f"Failed to generate say TwiML: {error_msg}",
            )

    def generate_hangup_twiml(
        self,
        message: Optional[str] = None,
        voice: str = DEFAULT_VOICE,
    ) -> TwiMLResponse:
        """Generate TwiML that optionally speaks then hangs up.

        Args:
            message: Optional message to speak before hanging up.
            voice: Voice to use for message.

        Returns:
            TwiMLResponse with hangup XML.
        """
        logger.info("Generating hangup TwiML")

        try:
            response = VoiceResponse()

            if message:
                response.say(message, voice=voice)

            response.hangup()

            return TwiMLResponse(
                content=str(response),
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to generate hangup TwiML: %s", error_msg)
            return TwiMLResponse(
                content="",
                success=False,
                error=f"Failed to generate hangup TwiML: {error_msg}",
            )

    async def get_call(self, call_sid: str) -> CallInfo:
        """Get information about a call.

        Args:
            call_sid: Twilio call SID.

        Returns:
            CallInfo with call details.

        Raises:
            TwilioCallError: If call lookup fails.
        """
        logger.info("Getting call info: %s", call_sid)

        loop = asyncio.get_event_loop()

        try:
            call = await loop.run_in_executor(
                None,
                lambda: self._client.calls(call_sid).fetch(),
            )

            result = self._parse_call(call)
            logger.info(
                "Retrieved call: %s (status=%s, duration=%s)",
                result.sid,
                result.status,
                result.duration,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to get call: %s", error_msg)

            if "404" in error_msg or "not found" in error_msg.lower():
                raise TwilioCallError(f"Call not found: {call_sid}") from e
            elif "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioCallError(f"Failed to get call: {error_msg}") from e

    async def end_call(self, call_sid: str) -> CallInfo:
        """End an active call.

        Args:
            call_sid: Twilio call SID.

        Returns:
            CallInfo with updated status.

        Raises:
            TwilioCallError: If ending call fails.
        """
        logger.info("Ending call: %s", call_sid)

        loop = asyncio.get_event_loop()

        try:
            call = await loop.run_in_executor(
                None,
                lambda: self._client.calls(call_sid).update(status="completed"),
            )

            result = self._parse_call(call)
            logger.info("Ended call: %s (status=%s)", result.sid, result.status)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to end call: %s", error_msg)

            if "404" in error_msg or "not found" in error_msg.lower():
                raise TwilioCallError(f"Call not found: {call_sid}") from e
            elif "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioCallError(f"Failed to end call: {error_msg}") from e

    async def make_call(
        self,
        to_number: str,
        from_number: Optional[str] = None,
        twiml_url: Optional[str] = None,
        twiml: Optional[str] = None,
        status_callback: Optional[str] = None,
    ) -> CallInfo:
        """Initiate an outbound call.

        Args:
            to_number: Phone number to call (E.164 format).
            from_number: Caller ID number. Defaults to configured phone number.
            twiml_url: URL returning TwiML for call handling.
            twiml: Raw TwiML string (used if twiml_url not provided).
            status_callback: URL for call status updates.

        Returns:
            CallInfo for initiated call.

        Raises:
            TwilioConfigError: If neither twiml_url nor twiml provided.
            TwilioCallError: If call initiation fails.
        """
        from_number = from_number or self.phone_number

        if not from_number:
            raise TwilioConfigError(
                "From number required. Set TWILIO_PHONE_NUMBER or pass from_number."
            )

        if not twiml_url and not twiml:
            raise TwilioConfigError(
                "Either twiml_url or twiml must be provided."
            )

        logger.info("Making call from %s to %s", from_number, to_number)

        loop = asyncio.get_event_loop()

        try:
            call_kwargs: dict[str, Any] = {
                "to": to_number,
                "from_": from_number,
            }

            if twiml_url:
                call_kwargs["url"] = twiml_url
            else:
                call_kwargs["twiml"] = twiml

            if status_callback:
                call_kwargs["status_callback"] = status_callback
                call_kwargs["status_callback_method"] = "POST"

            call = await loop.run_in_executor(
                None,
                lambda: self._client.calls.create(**call_kwargs),
            )

            result = self._parse_call(call)
            logger.info(
                "Initiated call: %s (status=%s)",
                result.sid,
                result.status,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to make call: %s", error_msg)

            if "401" in error_msg or "authenticate" in error_msg.lower():
                raise TwilioAuthError(f"Authentication failed: {error_msg}") from e
            else:
                raise TwilioCallError(f"Failed to make call: {error_msg}") from e

    def build_webhook_url(
        self,
        base_url: str,
        lead_id: str,
        endpoint: str = "/twilio/incoming",
    ) -> str:
        """Build a webhook URL for a specific lead.

        Constructs the full URL that Twilio should request when
        a call comes in for a specific lead's demo.

        Args:
            base_url: Base URL of the voice server (e.g., https://example.com).
            lead_id: Lead ID to include in the URL.
            endpoint: Webhook endpoint path.

        Returns:
            Full webhook URL with lead_id parameter.

        Example:
            >>> url = client.build_webhook_url(
            ...     base_url="https://voice.example.com",
            ...     lead_id="lead123",
            ... )
            >>> print(url)
            https://voice.example.com/twilio/incoming?lead_id=lead123
        """
        base_url = base_url.rstrip("/")
        endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base_url}{endpoint}?lead_id={lead_id}"

    def build_websocket_url(
        self,
        base_url: str,
        lead_id: str,
        path: str = "/voice",
    ) -> str:
        """Build a WebSocket URL for a specific lead.

        Constructs the WebSocket URL for streaming call audio
        to the OpenAI Realtime API proxy.

        Args:
            base_url: Base URL of the voice server (e.g., wss://example.com).
            lead_id: Lead ID to include in the path.
            path: WebSocket endpoint base path.

        Returns:
            Full WebSocket URL with lead_id in path.

        Example:
            >>> url = client.build_websocket_url(
            ...     base_url="wss://voice.example.com",
            ...     lead_id="lead123",
            ... )
            >>> print(url)
            wss://voice.example.com/voice/lead123
        """
        base_url = base_url.rstrip("/")
        path = path.rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}/{lead_id}"

    def close(self) -> None:
        """Clean up client resources."""
        # Twilio client doesn't require explicit cleanup,
        # but we provide this method for consistency
        logger.info("TwilioVoiceClient closed")

    async def __aenter__(self) -> "TwilioVoiceClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
