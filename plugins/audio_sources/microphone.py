"""
Microphone Plugin - Capture audio from system microphone
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

import numpy as np

try:
    import sounddevice as sd

    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None

import contextlib

from core.event_bus import Events, get_event_bus
from core.plugin_registry import AudioSourcePlugin

logger = logging.getLogger(__name__)


class MicrophonePlugin(AudioSourcePlugin):
    """
    Capture audio from system microphone/input device.

    Features:
    - Lists all available input devices
    - Configurable sample rate, buffer size, channels
    - Gain control and monitoring
    - Cross-platform support (Windows/Mac/Linux)
    """

    plugin_id = "microphone"
    display_name = "Microphone"
    description = "Capture audio from system microphone or input device"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["sounddevice", "numpy"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "device_index": {
                "type": ["integer", "null"],
                "default": None,
                "title": "Device Index",
                "description": "Input device index (null for default)",
            },
            "device_name": {
                "type": "string",
                "default": "Default",
                "title": "Device Name",
                "description": "Input device name",
            },
            "sample_rate": {
                "type": "integer",
                "default": 44100,
                "enum": [8000, 16000, 22050, 44100, 48000, 96000],
                "title": "Sample Rate (Hz)",
            },
            "chunk_size": {
                "type": "integer",
                "default": 512,
                "enum": [128, 256, 512, 1024, 2048],
                "title": "Chunk Size (samples)",
            },
            "channels": {
                "type": "integer",
                "default": 1,
                "enum": [1, 2],
                "title": "Channels (1=Mono, 2=Stereo)",
            },
            "gain": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.1,
                "maximum": 10.0,
                "title": "Gain",
                "description": "Input gain multiplier",
            },
        },
    }

    def __init__(self):
        self.device_index = None
        self.device_name = "Default"
        self.sample_rate = 44100
        self.chunk_size = 512
        self.channels = 1
        self.gain = 1.0

        self._stream = None
        self._is_streaming = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._is_initialized = False

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        if not HAS_SOUNDDEVICE:
            return False, "sounddevice library not installed. Run: pip install sounddevice"

        try:
            # Check if any input devices are available
            devices = sd.query_devices()
            input_devices = [d for d in devices if d["max_input_channels"] > 0]
            if not input_devices:
                return False, "No input devices found"
        except Exception as e:
            return False, f"Error checking input devices: {e}"

        return True, ""

    @staticmethod
    def list_input_devices() -> list[dict[str, Any]]:
        """List all available input devices."""
        if not HAS_SOUNDDEVICE:
            return []

        devices = []
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": dev["name"],
                            "max_channels": dev["max_input_channels"],
                            "default_samplerate": dev["default_samplerate"],
                            "is_default": i == sd.query_devices(None)["index"],
                        }
                    )
        except Exception as e:
            logger.error(f"Error listing devices: {e}")

        return devices

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize microphone."""
        self.device_index = config.get("device_index")
        self.device_name = config.get("device_name", "Default")
        self.sample_rate = config.get("sample_rate", 44100)
        self.chunk_size = config.get("chunk_size", 512)
        self.channels = config.get("channels", 1)
        self.gain = config.get("gain", 1.0)

        # Validate device
        try:
            devices = sd.query_devices()
            if self.device_index is not None:
                if self.device_index >= len(devices):
                    logger.warning(f"Device index {self.device_index} out of range, using default")
                    self.device_index = None
            else:
                # Use default input device
                self.device_index = sd.query_devices(kind="input")["index"]
        except Exception as e:
            logger.warning(f"Error checking devices: {e}")

        self._is_initialized = True
        logger.info(f"Microphone initialized: {self.device_name} @ {self.sample_rate}Hz")

    async def shutdown(self) -> None:
        """Shutdown microphone."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_initialized = False
        self._is_streaming = False

        logger.info("Microphone shutdown")

    async def start_stream(self) -> AsyncGenerator[np.ndarray, None]:
        """Start streaming audio from microphone."""
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("sounddevice not available")

        self._is_streaming = True

        def audio_callback(indata, frames, time_info, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"Audio stream status: {status}")

            # Apply gain
            audio_data = indata[:, : self.channels].flatten() * self.gain

            # Put in queue (non-blocking)
            with contextlib.suppress(asyncio.QueueFull):
                self._audio_queue.put_nowait(audio_data)

        # Create input stream
        try:
            self._stream = sd.InputStream(
                device=self.device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype=np.float32,
            )

            self._stream.start()
            logger.info(
                f"Started microphone stream: {self.sample_rate}Hz, {self.channels} channels"
            )

            get_event_bus().publish(
                Events.AUDIO_STARTED,
                {
                    "source": "microphone",
                    "sample_rate": self.sample_rate,
                    "channels": self.channels,
                },
                source="microphone",
            )

            # Yield audio chunks
            while self._is_streaming:
                try:
                    audio_data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                    yield audio_data
                except asyncio.TimeoutError:
                    continue

        except Exception as e:
            logger.error(f"Error starting microphone stream: {e}")
            raise
        finally:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._is_streaming = False

            get_event_bus().publish(
                Events.AUDIO_STOPPED, {"source": "microphone"}, source="microphone"
            )

    async def stop_stream(self) -> None:
        """Stop streaming."""
        self._is_streaming = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    async def get_audio_chunk(self) -> Optional[np.ndarray]:
        """Get next audio chunk."""
        if not self._is_streaming:
            return None

        try:
            audio_data = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
            return audio_data
        except asyncio.TimeoutError:
            return None

    def get_sample_rate(self) -> int:
        """Get sample rate."""
        return self.sample_rate

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata."""
        return {
            "source": "microphone",
            "device_name": self.device_name,
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "gain": self.gain,
        }
