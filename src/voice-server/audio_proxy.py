"""WebSocket proxy for Twilio Media Streams to OpenAI Realtime API.

This module provides the TwilioOpenAIProxy class that handles bidirectional
audio streaming between Twilio's mulaw 8kHz format and OpenAI's PCM 16kHz format.

Audio Format Conversion:
- Twilio sends: mulaw 8-bit, 8kHz, mono, base64 encoded
- OpenAI expects: PCM 16-bit, 24kHz, mono, base64 encoded
- OpenAI sends: PCM 16-bit, 24kHz, mono, base64 encoded
- Twilio expects: mulaw 8-bit, 8kHz, mono, base64 encoded

Example:
    async with TwilioOpenAIProxy(config) as proxy:
        await proxy.connect(lead_id, twilio_websocket)
"""

import asyncio
import base64
import json
import logging
import struct
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)

# Audio format constants
TWILIO_SAMPLE_RATE = 8000  # 8 kHz
TWILIO_SAMPLE_WIDTH = 1  # 8-bit (mulaw)
OPENAI_SAMPLE_RATE = 24000  # 24 kHz for OpenAI Realtime API
OPENAI_SAMPLE_WIDTH = 2  # 16-bit PCM

# Mulaw decoding table (8-bit mulaw -> 16-bit linear PCM)
# Standard ITU-T G.711 mulaw decoding
MULAW_DECODE_TABLE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
    -876, -844, -812, -780, -748, -716, -684, -652,
    -620, -588, -556, -524, -492, -460, -428, -396,
    -372, -356, -340, -324, -308, -292, -276, -260,
    -244, -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
    7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
    3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
    2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
    1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
    1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
    876, 844, 812, 780, 748, 716, 684, 652,
    620, 588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276, 260,
    244, 228, 212, 196, 180, 164, 148, 132,
    120, 112, 104, 96, 88, 80, 72, 64,
    56, 48, 40, 32, 24, 16, 8, 0,
]

# Mulaw encoding bias
MULAW_BIAS = 0x84
MULAW_CLIP = 32635


def _linear_to_mulaw(sample: int) -> int:
    """Convert a 16-bit linear PCM sample to 8-bit mulaw.

    Args:
        sample: 16-bit signed linear PCM sample (-32768 to 32767).

    Returns:
        8-bit mulaw encoded value (0-255).
    """
    # Get sign and magnitude
    sign = (sample >> 8) & 0x80
    if sign != 0:
        sample = -sample
    if sample > MULAW_CLIP:
        sample = MULAW_CLIP

    # Add bias for linear encoding
    sample = sample + MULAW_BIAS

    # Find the segment number
    exponent = 7
    mask = 0x4000
    while exponent > 0 and (sample & mask) == 0:
        exponent -= 1
        mask >>= 1

    # Extract mantissa
    mantissa = (sample >> (exponent + 3)) & 0x0F

    # Combine into mulaw byte
    mulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF

    return mulaw_byte


def _mulaw_to_linear(mulaw_byte: int) -> int:
    """Convert an 8-bit mulaw sample to 16-bit linear PCM.

    Args:
        mulaw_byte: 8-bit mulaw encoded value (0-255).

    Returns:
        16-bit signed linear PCM sample.
    """
    return MULAW_DECODE_TABLE[mulaw_byte & 0xFF]


class ProxyState(str, Enum):
    """State of the audio proxy connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    CLOSING = "closing"
    ERROR = "error"


class OpenAIEventType(str, Enum):
    """OpenAI Realtime API event types."""

    # Client events (sent to OpenAI)
    SESSION_UPDATE = "session.update"
    INPUT_AUDIO_BUFFER_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_BUFFER_COMMIT = "input_audio_buffer.commit"
    INPUT_AUDIO_BUFFER_CLEAR = "input_audio_buffer.clear"
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    RESPONSE_CREATE = "response.create"
    RESPONSE_CANCEL = "response.cancel"

    # Server events (received from OpenAI)
    ERROR = "error"
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    CONVERSATION_CREATED = "conversation.created"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    INPUT_AUDIO_BUFFER_CLEARED = "input_audio_buffer.cleared"
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"
    RATE_LIMITS_UPDATED = "rate_limits.updated"


@dataclass
class ProxyConfig:
    """Configuration for the Twilio-OpenAI proxy.

    Attributes:
        openai_api_key: OpenAI API key for authentication.
        openai_realtime_url: OpenAI Realtime API WebSocket URL.
        openai_model: Model to use for realtime conversations.
        voice: Voice to use for responses (alloy, echo, shimmer, etc.).
        system_prompt: System instructions for the AI assistant.
        turn_detection: Enable automatic turn detection.
        temperature: Response temperature (0.0-2.0).
        max_response_tokens: Maximum tokens in response.
    """

    openai_api_key: str
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime"
    openai_model: str = "gpt-4o-realtime-preview-2024-10-01"
    voice: str = "alloy"
    system_prompt: str = "You are a helpful AI assistant."
    turn_detection: bool = True
    temperature: float = 0.8
    max_response_tokens: int = 4096


@dataclass
class ProxySession:
    """Represents an active proxy session.

    Attributes:
        lead_id: Lead ID for context.
        call_sid: Twilio call SID.
        stream_sid: Twilio stream SID.
        state: Current proxy state.
        created_at: When the session was created.
        openai_session_id: OpenAI session ID once connected.
        audio_chunks_received: Count of audio chunks from Twilio.
        audio_chunks_sent: Count of audio chunks to Twilio.
        transcript: Running conversation transcript.
    """

    lead_id: str
    call_sid: Optional[str] = None
    stream_sid: Optional[str] = None
    state: ProxyState = ProxyState.DISCONNECTED
    created_at: datetime = field(default_factory=datetime.utcnow)
    openai_session_id: Optional[str] = None
    audio_chunks_received: int = 0
    audio_chunks_sent: int = 0
    transcript: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "lead_id": self.lead_id,
            "call_sid": self.call_sid,
            "stream_sid": self.stream_sid,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "openai_session_id": self.openai_session_id,
            "audio_chunks_received": self.audio_chunks_received,
            "audio_chunks_sent": self.audio_chunks_sent,
            "transcript_length": len(self.transcript),
        }


class AudioConverter:
    """Handles audio format conversion between Twilio and OpenAI formats.

    This implementation uses pure Python for mulaw/PCM conversion and
    linear interpolation for resampling, avoiding deprecated audioop module.
    """

    @staticmethod
    def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
        """Convert mulaw 8kHz audio to PCM 16-bit 24kHz.

        Args:
            mulaw_data: Raw mulaw audio bytes (8-bit, 8kHz).

        Returns:
            PCM audio bytes (16-bit, 24kHz, little-endian).
        """
        # Step 1: Convert mulaw to linear PCM (16-bit)
        pcm_samples = [_mulaw_to_linear(b) for b in mulaw_data]

        # Step 2: Resample from 8kHz to 24kHz (3x upsampling)
        pcm_24k = AudioConverter._resample(pcm_samples, TWILIO_SAMPLE_RATE, OPENAI_SAMPLE_RATE)

        # Pack as 16-bit little-endian signed integers
        return struct.pack(f"<{len(pcm_24k)}h", *pcm_24k)

    @staticmethod
    def pcm_to_mulaw(pcm_data: bytes) -> bytes:
        """Convert PCM 16-bit 24kHz audio to mulaw 8kHz.

        Args:
            pcm_data: Raw PCM audio bytes (16-bit, 24kHz, little-endian).

        Returns:
            Mulaw audio bytes (8-bit, 8kHz).
        """
        # Unpack PCM samples (16-bit little-endian signed)
        num_samples = len(pcm_data) // 2
        pcm_samples = list(struct.unpack(f"<{num_samples}h", pcm_data))

        # Step 1: Resample from 24kHz to 8kHz (3x downsampling)
        pcm_8k = AudioConverter._resample(pcm_samples, OPENAI_SAMPLE_RATE, TWILIO_SAMPLE_RATE)

        # Step 2: Convert linear PCM to mulaw
        mulaw_bytes = bytes(_linear_to_mulaw(sample) for sample in pcm_8k)

        return mulaw_bytes

    @staticmethod
    def _resample(samples: list[int], from_rate: int, to_rate: int) -> list[int]:
        """Resample audio using linear interpolation.

        Args:
            samples: Input audio samples.
            from_rate: Source sample rate in Hz.
            to_rate: Target sample rate in Hz.

        Returns:
            Resampled audio samples.
        """
        if from_rate == to_rate or not samples:
            return samples

        ratio = to_rate / from_rate
        new_length = int(len(samples) * ratio)

        if new_length == 0:
            return []

        resampled = []
        for i in range(new_length):
            # Calculate the position in the original sample array
            pos = i / ratio
            idx = int(pos)
            frac = pos - idx

            # Linear interpolation between adjacent samples
            if idx + 1 < len(samples):
                sample = int(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
            else:
                sample = samples[idx] if idx < len(samples) else 0

            # Clamp to 16-bit range
            sample = max(-32768, min(32767, sample))
            resampled.append(sample)

        return resampled

    @staticmethod
    def base64_decode(b64_data: str) -> bytes:
        """Decode base64 audio data."""
        return base64.b64decode(b64_data)

    @staticmethod
    def base64_encode(raw_data: bytes) -> str:
        """Encode audio data to base64."""
        return base64.b64encode(raw_data).decode("utf-8")


class TwilioOpenAIProxy:
    """Proxy between Twilio Media Streams and OpenAI Realtime API.

    This class manages bidirectional audio streaming, handling format
    conversion and message routing between the two WebSocket connections.

    Example:
        config = ProxyConfig(openai_api_key="sk-...")
        proxy = TwilioOpenAIProxy(config)
        await proxy.connect(lead_id, twilio_ws)
    """

    def __init__(
        self,
        config: ProxyConfig,
        on_transcript: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Initialize the proxy.

        Args:
            config: Proxy configuration.
            on_transcript: Optional callback for transcript updates (role, text).
        """
        self.config = config
        self.on_transcript = on_transcript
        self._session: Optional[ProxySession] = None
        self._openai_ws: Optional[WebSocketClientProtocol] = None
        self._twilio_ws: Optional[Any] = None  # FastAPI WebSocket
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._running = False

    @property
    def session(self) -> Optional[ProxySession]:
        """Get the current session."""
        return self._session

    @property
    def is_connected(self) -> bool:
        """Check if proxy is connected to both endpoints."""
        return (
            self._session is not None
            and self._session.state == ProxyState.STREAMING
            and self._openai_ws is not None
        )

    async def connect(
        self,
        lead_id: str,
        twilio_websocket: Any,
        system_prompt: Optional[str] = None,
    ) -> None:
        """Connect to OpenAI and start proxying.

        Args:
            lead_id: Lead ID for context and personalization.
            twilio_websocket: FastAPI WebSocket connection from Twilio.
            system_prompt: Optional override for system prompt.

        Raises:
            ConnectionError: If unable to connect to OpenAI.
        """
        self._session = ProxySession(lead_id=lead_id)
        self._session.state = ProxyState.CONNECTING
        self._twilio_ws = twilio_websocket

        try:
            # Connect to OpenAI Realtime API
            logger.info("Connecting to OpenAI Realtime API for lead: %s", lead_id)
            url = f"{self.config.openai_realtime_url}?model={self.config.openai_model}"
            headers = {
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

            self._openai_ws = await websockets.connect(url, extra_headers=headers)
            self._session.state = ProxyState.CONNECTED
            logger.info("Connected to OpenAI Realtime API")

            # Configure the session
            await self._configure_session(system_prompt)

            # Start the bidirectional streaming
            self._running = True
            self._session.state = ProxyState.STREAMING

            # Run receive tasks concurrently
            await self._run_proxy_loop()

        except websockets.exceptions.WebSocketException as e:
            logger.error("WebSocket connection error: %s", e)
            self._session.state = ProxyState.ERROR
            raise ConnectionError(f"Failed to connect to OpenAI: {e}") from e

        except Exception as e:
            logger.error("Proxy connection error: %s", e, exc_info=True)
            self._session.state = ProxyState.ERROR
            raise

        finally:
            await self.close()

    async def _configure_session(self, system_prompt: Optional[str] = None) -> None:
        """Configure the OpenAI session with voice and instructions.

        Args:
            system_prompt: Optional override for system prompt.
        """
        if not self._openai_ws:
            return

        session_config = {
            "type": OpenAIEventType.SESSION_UPDATE.value,
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt or self.config.system_prompt,
                "voice": self.config.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                } if self.config.turn_detection else None,
                "tools": [],
                "tool_choice": "auto",
                "temperature": self.config.temperature,
                "max_response_output_tokens": self.config.max_response_tokens,
            },
        }

        await self._openai_ws.send(json.dumps(session_config))
        logger.info("Sent session configuration to OpenAI")

    async def _run_proxy_loop(self) -> None:
        """Run the main proxy loop handling both directions."""
        try:
            # Create tasks for both directions
            twilio_task = asyncio.create_task(self._handle_twilio_messages())
            openai_task = asyncio.create_task(self._handle_openai_messages())

            # Wait for either to complete (usually means disconnection)
            done, pending = await asyncio.wait(
                [twilio_task, openai_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Check for exceptions
            for task in done:
                if task.exception():
                    logger.error("Proxy task error: %s", task.exception())

        except Exception as e:
            logger.error("Proxy loop error: %s", e, exc_info=True)

    async def _handle_twilio_messages(self) -> None:
        """Handle incoming messages from Twilio."""
        if not self._twilio_ws:
            return

        try:
            while self._running:
                message = await self._twilio_ws.receive_text()
                data = json.loads(message)
                await self._process_twilio_event(data)

        except Exception as e:
            if self._running:
                logger.error("Twilio message handler error: %s", e)
            raise

    async def _handle_openai_messages(self) -> None:
        """Handle incoming messages from OpenAI."""
        if not self._openai_ws:
            return

        try:
            async for message in self._openai_ws:
                if not self._running:
                    break
                data = json.loads(message)
                await self._process_openai_event(data)

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI connection closed")

        except Exception as e:
            if self._running:
                logger.error("OpenAI message handler error: %s", e)
            raise

    async def _process_twilio_event(self, data: dict[str, Any]) -> None:
        """Process an event from Twilio.

        Args:
            data: Parsed JSON event from Twilio.
        """
        event_type = data.get("event")

        if event_type == "start":
            # Stream metadata
            start_data = data.get("start", {})
            if self._session:
                self._session.stream_sid = start_data.get("streamSid")
                self._session.call_sid = start_data.get("callSid")
            logger.info("Twilio stream started: %s", start_data.get("streamSid"))

        elif event_type == "media":
            # Audio data - convert and forward to OpenAI
            media = data.get("media", {})
            payload = media.get("payload")

            if payload and self._openai_ws:
                try:
                    # Decode and convert audio
                    mulaw_audio = AudioConverter.base64_decode(payload)
                    pcm_audio = AudioConverter.mulaw_to_pcm(mulaw_audio)
                    pcm_b64 = AudioConverter.base64_encode(pcm_audio)

                    # Send to OpenAI
                    audio_event = {
                        "type": OpenAIEventType.INPUT_AUDIO_BUFFER_APPEND.value,
                        "audio": pcm_b64,
                    }
                    await self._openai_ws.send(json.dumps(audio_event))

                    if self._session:
                        self._session.audio_chunks_received += 1

                except Exception as e:
                    logger.error("Audio conversion error: %s", e)

        elif event_type == "stop":
            # Stream ending
            logger.info("Twilio stream stopped")
            self._running = False

    async def _process_openai_event(self, data: dict[str, Any]) -> None:
        """Process an event from OpenAI.

        Args:
            data: Parsed JSON event from OpenAI.
        """
        event_type = data.get("type")

        if event_type == OpenAIEventType.SESSION_CREATED.value:
            session_data = data.get("session", {})
            if self._session:
                self._session.openai_session_id = session_data.get("id")
            logger.info("OpenAI session created: %s", session_data.get("id"))

        elif event_type == OpenAIEventType.SESSION_UPDATED.value:
            logger.debug("OpenAI session updated")

        elif event_type == OpenAIEventType.RESPONSE_AUDIO_DELTA.value:
            # Audio response from OpenAI - convert and forward to Twilio
            audio_b64 = data.get("delta")

            if audio_b64 and self._twilio_ws:
                try:
                    # Decode and convert audio
                    pcm_audio = AudioConverter.base64_decode(audio_b64)
                    mulaw_audio = AudioConverter.pcm_to_mulaw(pcm_audio)
                    mulaw_b64 = AudioConverter.base64_encode(mulaw_audio)

                    # Send to Twilio as media message
                    stream_sid = self._session.stream_sid if self._session else ""
                    media_message = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": mulaw_b64,
                        },
                    }
                    await self._twilio_ws.send_text(json.dumps(media_message))

                    if self._session:
                        self._session.audio_chunks_sent += 1

                except Exception as e:
                    logger.error("Audio send error: %s", e)

        elif event_type == OpenAIEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA.value:
            # Transcript of AI response
            delta = data.get("delta", "")
            if self._session:
                # Append to last assistant message or create new
                if (
                    self._session.transcript
                    and self._session.transcript[-1].get("role") == "assistant"
                ):
                    self._session.transcript[-1]["content"] += delta
                else:
                    self._session.transcript.append({
                        "role": "assistant",
                        "content": delta,
                    })

            if self.on_transcript:
                self.on_transcript("assistant", delta)

        elif event_type == OpenAIEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED.value:
            # User started speaking
            logger.debug("User speech started")

        elif event_type == OpenAIEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED.value:
            # User stopped speaking
            logger.debug("User speech stopped")

        elif event_type == OpenAIEventType.INPUT_AUDIO_BUFFER_COMMITTED.value:
            # Audio buffer was committed (end of user turn)
            logger.debug("Audio buffer committed")

        elif event_type == OpenAIEventType.RESPONSE_DONE.value:
            # Response complete
            logger.debug("OpenAI response complete")

            # Send a mark to Twilio to track playback
            if self._twilio_ws and self._session and self._session.stream_sid:
                mark_message = {
                    "event": "mark",
                    "streamSid": self._session.stream_sid,
                    "mark": {"name": "response_complete"},
                }
                try:
                    await self._twilio_ws.send_text(json.dumps(mark_message))
                except Exception:
                    pass

        elif event_type == OpenAIEventType.ERROR.value:
            error = data.get("error", {})
            logger.error("OpenAI error: %s", error.get("message", "Unknown error"))

        elif event_type == OpenAIEventType.RATE_LIMITS_UPDATED.value:
            # Rate limit info
            rate_limits = data.get("rate_limits", [])
            logger.debug("Rate limits: %s", rate_limits)

        else:
            logger.debug("Unhandled OpenAI event: %s", event_type)

    async def send_text(self, text: str) -> None:
        """Send a text message to OpenAI for the AI to speak.

        Args:
            text: Text to have the AI speak.
        """
        if not self._openai_ws or not self.is_connected:
            logger.warning("Cannot send text: not connected")
            return

        # Create a conversation item with the text
        item_event = {
            "type": OpenAIEventType.CONVERSATION_ITEM_CREATE.value,
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text,
                    }
                ],
            },
        }
        await self._openai_ws.send(json.dumps(item_event))

        # Request a response
        response_event = {
            "type": OpenAIEventType.RESPONSE_CREATE.value,
        }
        await self._openai_ws.send(json.dumps(response_event))

    async def close(self) -> None:
        """Close all connections and clean up."""
        self._running = False

        if self._session:
            self._session.state = ProxyState.CLOSING

        # Close OpenAI connection
        if self._openai_ws:
            try:
                await self._openai_ws.close()
            except Exception as e:
                logger.debug("Error closing OpenAI connection: %s", e)
            self._openai_ws = None

        # Don't close Twilio WebSocket here - it's managed by FastAPI
        self._twilio_ws = None

        if self._session:
            self._session.state = ProxyState.DISCONNECTED
            logger.info(
                "Proxy closed for lead %s: received=%d, sent=%d chunks",
                self._session.lead_id,
                self._session.audio_chunks_received,
                self._session.audio_chunks_sent,
            )

    async def __aenter__(self) -> "TwilioOpenAIProxy":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


def create_proxy_from_config(
    openai_api_key: str,
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime",
    model: str = "gpt-4o-realtime-preview-2024-10-01",
    voice: str = "alloy",
    system_prompt: Optional[str] = None,
) -> TwilioOpenAIProxy:
    """Factory function to create a proxy with common settings.

    Args:
        openai_api_key: OpenAI API key.
        openai_realtime_url: OpenAI Realtime API URL.
        model: Model to use.
        voice: Voice for responses.
        system_prompt: Optional system prompt.

    Returns:
        Configured TwilioOpenAIProxy instance.
    """
    config = ProxyConfig(
        openai_api_key=openai_api_key,
        openai_realtime_url=openai_realtime_url,
        openai_model=model,
        voice=voice,
        system_prompt=system_prompt or "You are a helpful AI assistant.",
    )
    return TwilioOpenAIProxy(config)
