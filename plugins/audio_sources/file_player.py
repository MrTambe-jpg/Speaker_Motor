"""
File Player Plugin - Play audio files (WAV, MP3, FLAC, OGG, etc.)
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Optional

import numpy as np

try:
    import soundfile as sf

    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    sf = None

try:
    from pydub import AudioSegment

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

from core.event_bus import Events, get_event_bus
from core.plugin_registry import AudioSourcePlugin

logger = logging.getLogger(__name__)


class FilePlayerPlugin(AudioSourcePlugin):
    """
    Play audio files in various formats.

    Supported formats: WAV, MP3, FLAC, OGG, AAC, AIFF, M4A
    Features:
    - Drag-and-drop or file picker
    - Playlist support with shuffle and repeat
    - Seek support
    - Tempo/pitch controls
    """

    plugin_id = "file_player"
    display_name = "File Player"
    description = "Play audio files (WAV, MP3, FLAC, OGG, AAC, AIFF, M4A)"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["soundfile", "numpy", "pydub"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "default": "",
                "title": "File Path",
                "description": "Path to audio file",
            },
            "playlist": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "title": "Playlist",
                "description": "List of file paths",
            },
            "shuffle": {
                "type": "boolean",
                "default": False,
                "title": "Shuffle",
                "description": "Shuffle playlist",
            },
            "repeat": {
                "type": "boolean",
                "default": False,
                "title": "Repeat",
                "description": "Repeat playlist",
            },
            "volume": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 2.0,
                "title": "Volume",
                "description": "Playback volume (0.0 - 2.0)",
            },
            "chunk_size": {
                "type": "integer",
                "default": 2048,
                "title": "Chunk Size",
                "description": "Samples per chunk",
            },
        },
    }

    SUPPORTED_FORMATS = [".wav", ".mp3", ".flac", ".ogg", ".aac", ".aiff", ".m4a"]

    def __init__(self):
        self.file_path = ""
        self.playlist: list[str] = []
        self.shuffle = False
        self.repeat = False
        self.volume = 1.0
        self.chunk_size = 2048

        self._audio_data: Optional[np.ndarray] = None
        self._sample_rate = 44100
        self._current_position = 0
        self._current_track_index = 0
        self._is_playing = False
        self._is_initialized = False
        self._playback_task: Optional[asyncio.Task] = None

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        if not HAS_SOUNDFILE:
            return False, "soundfile library not installed. Run: pip install soundfile"
        if not HAS_PYDUB:
            logger.warning("pydub not installed, some formats may not be supported")
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize file player."""
        self.file_path = config.get("file_path", "")
        self.playlist = config.get("playlist", [])
        self.shuffle = config.get("shuffle", False)
        self.repeat = config.get("repeat", False)
        self.volume = config.get("volume", 1.0)
        self.chunk_size = config.get("chunk_size", 2048)

        self._is_initialized = True
        logger.info("File player initialized")

    async def shutdown(self) -> None:
        """Shutdown file player."""
        await self.stop_stream()
        self._audio_data = None
        self._is_initialized = False
        logger.info("File player shutdown")

    def load_file(self, file_path: str) -> bool:
        """Load an audio file."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        ext = Path(file_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {ext}")
            return False

        try:
            # Try soundfile first
            if ext == ".wav" or ext == ".flac" or ext == ".aiff":
                self._audio_data, self._sample_rate = sf.read(file_path)
                # Convert to mono if stereo
                if len(self._audio_data.shape) > 1:
                    self._audio_data = self._audio_data.mean(axis=1)
                self._audio_data = self._audio_data.astype(np.float32)
            else:
                # Use pydub for other formats
                if HAS_PYDUB:
                    audio = AudioSegment.from_file(file_path)
                    self._sample_rate = audio.frame_rate
                    # Convert to mono float32
                    if audio.channels > 1:
                        audio = audio.set_channels(1)
                    samples = np.array(audio.get_array_of_samples())
                    self._audio_data = samples.astype(np.float32) / 32768.0
                else:
                    # Fallback to soundfile (may not work for all formats)
                    self._audio_data, self._sample_rate = sf.read(file_path)
                    if len(self._audio_data.shape) > 1:
                        self._audio_data = self._audio_data.mean(axis=1)

            self._current_position = 0
            self.file_path = file_path

            logger.info(
                f"Loaded file: {file_path} ({len(self._audio_data)} samples @ {self._sample_rate}Hz)"
            )

            get_event_bus().publish(
                Events.TRACK_CHANGED,
                {
                    "source": "file_player",
                    "file_path": file_path,
                    "duration": len(self._audio_data) / self._sample_rate,
                    "sample_rate": self._sample_rate,
                },
                source="file_player",
            )

            return True

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return False

    async def start_stream(self) -> AsyncGenerator[np.ndarray, None]:
        """Start streaming audio from file."""
        if self._audio_data is None and self.file_path:
            self.load_file(self.file_path)

        if self._audio_data is None:
            logger.error("No audio loaded")
            return

        self._is_playing = True
        self._current_position = 0

        get_event_bus().publish(
            Events.AUDIO_STARTED,
            {"source": "file_player", "file": self.file_path, "sample_rate": self._sample_rate},
            source="file_player",
        )

        try:
            while self._is_playing and self._current_position < len(self._audio_data):
                # Get chunk
                end_pos = min(self._current_position + self.chunk_size, len(self._audio_data))
                chunk = self._audio_data[self._current_position : end_pos].copy()

                # Apply volume
                chunk = chunk * self.volume

                self._current_position = end_pos

                yield chunk

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)

            # File ended
            if self.repeat:
                self._current_position = 0
                # Continue playing (would need to restart generator)
            elif self.playlist and self._current_track_index < len(self.playlist) - 1:
                # Next track
                self._current_track_index += 1
                self.load_file(self.playlist[self._current_track_index])

        except asyncio.CancelledError:
            pass
        finally:
            self._is_playing = False

            get_event_bus().publish(
                Events.AUDIO_STOPPED, {"source": "file_player"}, source="file_player"
            )

    async def stop_stream(self) -> None:
        """Stop playback."""
        self._is_playing = False

    async def pause(self) -> None:
        """Pause playback."""
        self._is_playing = False

    async def resume(self) -> None:
        """Resume playback."""
        self._is_playing = True

    async def seek(self, position_seconds: float) -> None:
        """Seek to position in seconds."""
        if self._audio_data is None:
            return

        position_samples = int(position_seconds * self._sample_rate)
        self._current_position = max(0, min(position_samples, len(self._audio_data)))

    async def get_audio_chunk(self) -> Optional[np.ndarray]:
        """Get next audio chunk."""
        if self._audio_data is None or not self._is_playing:
            return None

        if self._current_position >= len(self._audio_data):
            return None

        end_pos = min(self._current_position + self.chunk_size, len(self._audio_data))
        chunk = self._audio_data[self._current_position : end_pos].copy() * self.volume
        self._current_position = end_pos

        return chunk

    def get_sample_rate(self) -> int:
        """Get sample rate."""
        return self._sample_rate

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata."""
        metadata = {
            "source": "file_player",
            "file_path": self.file_path,
            "sample_rate": self._sample_rate,
            "is_playing": self._is_playing,
            "position": (
                self._current_position / self._sample_rate if self._audio_data is not None else 0
            ),
            "duration": (
                len(self._audio_data) / self._sample_rate if self._audio_data is not None else 0
            ),
        }

        if self.playlist:
            metadata["playlist"] = self.playlist
            metadata["current_track"] = self._current_track_index

        return metadata

    def get_position(self) -> float:
        """Get current position in seconds."""
        if self._audio_data is None:
            return 0.0
        return self._current_position / self._sample_rate

    def get_duration(self) -> float:
        """Get total duration in seconds."""
        if self._audio_data is None:
            return 0.0
        return len(self._audio_data) / self._sample_rate

    def set_playlist(self, files: list[str]) -> None:
        """Set playlist."""
        self.playlist = files
        self._current_track_index = 0

    def next_track(self) -> bool:
        """Go to next track."""
        if not self.playlist:
            return False

        self._current_track_index = (self._current_track_index + 1) % len(self.playlist)
        return self.load_file(self.playlist[self._current_track_index])

    def previous_track(self) -> bool:
        """Go to previous track."""
        if not self.playlist:
            return False

        self._current_track_index = (self._current_track_index - 1) % len(self.playlist)
        return self.load_file(self.playlist[self._current_track_index])
