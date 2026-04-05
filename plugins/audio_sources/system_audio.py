"""
System Audio Plugin - Capture system audio via loopback
"""

import asyncio
import logging
import platform
from collections.abc import AsyncGenerator
from typing import Any, Optional

import numpy as np

try:
    import sounddevice as sd

    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

import contextlib

from core.event_bus import Events, get_event_bus
from core.plugin_registry import AudioSourcePlugin

logger = logging.getLogger(__name__)


class SystemAudioPlugin(AudioSourcePlugin):
    """
    Capture system audio via loopback.

    Platform support:
    - Windows: WASAPI loopback (native)
    - macOS: Requires BlackHole or similar virtual audio device
    - Linux: PulseAudio monitor source / PipeWire

    This is the universal fallback for Spotify, Apple Music,
    Netflix, and any other audio source.
    """

    plugin_id = "system_audio"
    display_name = "System Audio (Loopback)"
    description = "Capture whatever is playing on your computer"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["sounddevice", "numpy"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "loopback_device": {
                "type": ["integer", "null"],
                "default": None,
                "title": "Loopback Device Index",
                "description": "Loopback device index (null for auto-detect)",
            },
            "loopback_device_name": {
                "type": "string",
                "default": "Default",
                "title": "Loopback Device Name",
            },
            "sample_rate": {"type": "integer", "default": 44100, "title": "Sample Rate (Hz)"},
            "chunk_size": {"type": "integer", "default": 512, "title": "Chunk Size"},
        },
    }

    def __init__(self):
        self.loopback_device = None
        self.loopback_device_name = "Default"
        self.sample_rate = 44100
        self.chunk_size = 512

        self._stream = None
        self._is_streaming = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._is_initialized = False

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        if not HAS_SOUNDDEVICE:
            return False, "sounddevice library not installed. Run: pip install sounddevice"

        current_os = platform.system()

        os_return_values = {
            "Windows": (True, ""),
            "Darwin": (
                True,
                "Note: Requires BlackHole or similar virtual audio device. Install with: brew install blackhole",
            ),
            "Linux": (True, ""),
        }
        return os_return_values.get(current_os, (True, ""))

    @staticmethod
    def get_loopback_devices() -> list[dict[str, Any]]:
        """Get available loopback devices."""
        if not HAS_SOUNDDEVICE:
            return []

        devices = []
        current_os = platform.system()

        try:
            all_devices = sd.query_devices()

            if current_os == "Windows":
                # On Windows, look for loopback devices
                for i, dev in enumerate(all_devices):
                    # WASAPI loopback devices have 0 input channels but are output devices
                    # that can be captured
                    if dev["max_output_channels"] > 0:
                        devices.append(
                            {
                                "index": i,
                                "name": dev["name"],
                                "type": "wasapi_loopback",
                                "channels": dev["max_output_channels"],
                                "sample_rate": dev["default_samplerate"],
                            }
                        )

            else:
                # On Mac/Linux, look for monitor/virtual devices
                for i, dev in enumerate(all_devices):
                    if "monitor" in dev["name"].lower() or "virtual" in dev["name"].lower():
                        devices.append(
                            {
                                "index": i,
                                "name": dev["name"],
                                "type": "monitor",
                                "channels": dev["max_input_channels"],
                                "sample_rate": dev["default_samplerate"],
                            }
                        )
                    elif dev["max_input_channels"] > 0:
                        devices.append(
                            {
                                "index": i,
                                "name": dev["name"],
                                "type": "input",
                                "channels": dev["max_input_channels"],
                                "sample_rate": dev["default_samplerate"],
                            }
                        )

        except Exception as e:
            logger.error(f"Error listing devices: {e}")

        return devices

    def get_setup_instructions(self) -> str:
        """Get platform-specific setup instructions."""
        current_os = platform.system()

        setup_instructions = {
            "Windows": """
Windows WASAPI Loopback Setup:
1. No additional software needed - Windows supports loopback natively
2. Select your speakers/output device as the loopback device
3. The system will capture whatever is playing
""",
            "Darwin": """
macOS Virtual Audio Setup:
1. Install BlackHole: brew install blackhole
2. Open Audio MIDI Setup (in Applications/Utilities)
3. Create a Multi-Output Device with both speakers and BlackHole
4. Select BlackHole as the loopback device
""",
            "Linux": """
Linux PulseAudio/PipeWire Setup:
1. PulseAudio: Select the "Monitor of" device for your output
2. PipeWire: Use pw-cli to list nodes and select monitor
3. Or install PulseAudio Volume Control: pavucontrol
""",
        }
        return setup_instructions.get(
            current_os, "No setup instructions available for this platform"
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize system audio capture."""
        self.loopback_device = config.get("loopback_device")
        self.loopback_device_name = config.get("loopback_device_name", "Default")
        self.sample_rate = config.get("sample_rate", 44100)
        self.chunk_size = config.get("chunk_size", 512)

        # Auto-detect loopback device if not specified
        if self.loopback_device is None:
            devices = self.get_loopback_devices()
            if devices:
                self.loopback_device = devices[0]["index"]
                self.loopback_device_name = devices[0]["name"]

        self._is_initialized = True
        logger.info(f"System audio initialized: {self.loopback_device_name}")

    async def shutdown(self) -> None:
        """Shutdown."""
        await self.stop_stream()
        self._is_initialized = False

    async def start_stream(self) -> AsyncGenerator[np.ndarray, None]:
        """Start capturing system audio."""
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("sounddevice not available")

        self._is_streaming = True
        current_os = platform.system()

        def audio_callback(indata, frames, time_info, status):
            """Callback for audio capture."""
            if status:
                logger.warning(f"Audio status: {status}")

            # Flatten to mono
            audio_data = indata.flatten()
            with contextlib.suppress(asyncio.QueueFull):
                self._audio_queue.put_nowait(audio_data)

        try:
            if current_os == "Windows":
                # Windows: Use WASAPI loopback
                # We capture from the default output device as input
                self._stream = sd.InputStream(
                    device=self.loopback_device,
                    samplerate=self.sample_rate,
                    blocksize=self.chunk_size,
                    channels=1,
                    callback=audio_callback,
                    dtype=np.float32,
                    extra_settings=sd.WasapiSettings(exclusive=False),
                )
            else:
                # Mac/Linux: Use standard input capture from monitor device
                self._stream = sd.InputStream(
                    device=self.loopback_device,
                    samplerate=self.sample_rate,
                    blocksize=self.chunk_size,
                    channels=1,
                    callback=audio_callback,
                    dtype=np.float32,
                )

            self._stream.start()
            logger.info(f"Started system audio capture: {self.loopback_device_name}")

            get_event_bus().publish(
                Events.AUDIO_STARTED,
                {"source": "system_audio", "device": self.loopback_device_name},
                source="system_audio",
            )

            while self._is_streaming:
                try:
                    audio_data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                    yield audio_data
                except asyncio.TimeoutError:
                    continue

        except Exception as e:
            logger.error(f"Error capturing system audio: {e}")
            raise
        finally:
            if self._stream:
                self._stream.stop()
                self._stream.close()

            self._is_streaming = False
            get_event_bus().publish(
                Events.AUDIO_STOPPED, {"source": "system_audio"}, source="system_audio"
            )

    async def stop_stream(self) -> None:
        """Stop capturing."""
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
            "source": "system_audio",
            "device": self.loopback_device_name,
            "sample_rate": self.sample_rate,
        }
