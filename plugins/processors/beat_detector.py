"""
Beat Detector Plugin - BPM and transient detection
"""

import logging
import time
from collections import deque
from typing import Any

import numpy as np

try:
    import librosa

    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

from core.event_bus import Events, get_event_bus
from core.plugin_registry import ProcessorPlugin

logger = logging.getLogger(__name__)


class BeatDetectorPlugin(ProcessorPlugin):
    """
    Real-time beat detection and BPM estimation.

    Uses onset detection to find beats and tempo estimation for BPM.
    """

    plugin_id = "beat_detector"
    display_name = "Beat Detector"
    description = "Detect beats and estimate BPM in real-time"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["numpy", "librosa"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "sensitivity": {
                "type": "number",
                "default": 0.7,
                "minimum": 0.1,
                "maximum": 1.0,
                "title": "Sensitivity",
                "description": "Beat detection sensitivity (0.1 - 1.0)",
            },
            "min_bpm": {
                "type": "integer",
                "default": 60,
                "minimum": 40,
                "maximum": 200,
                "title": "Minimum BPM",
            },
            "max_bpm": {
                "type": "integer",
                "default": 200,
                "minimum": 100,
                "maximum": 300,
                "title": "Maximum BPM",
            },
            "hold_time_ms": {
                "type": "integer",
                "default": 100,
                "title": "Hold Time (ms)",
                "description": "Minimum time between detected beats",
            },
            "enabled": {"type": "boolean", "default": True, "title": "Enabled"},
        },
    }

    def __init__(self):
        self.sensitivity = 0.7
        self.min_bpm = 60
        self.max_bpm = 200
        self.hold_time_ms = 100
        self.enabled = True

        self._last_beat_time = 0.0
        self._beat_times: deque = deque(maxlen=100)
        self._onset_threshold = 0.5
        self._energy_buffer: deque = deque(maxlen=10)
        self._last_onset = 0.0
        self._estimated_bpm = 120.0
        self._bpm_confidence = 0.0

        # For simple onset detection
        self._sample_rate = 44100
        self._hop_length = 512

    def check_available(self) -> tuple[bool, str]:
        """Check if librosa is available."""
        if not HAS_LIBROSA:
            return (
                True,
                "librosa not installed. Using simple beat detection. Run: pip install librosa",
            )
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize beat detector."""
        self.sensitivity = config.get("sensitivity", 0.7)
        self.min_bpm = config.get("min_bpm", 60)
        self.max_bpm = config.get("max_bpm", 200)
        self.hold_time_ms = config.get("hold_time_ms", 100)
        self.enabled = config.get("enabled", True)

        # Calculate threshold from sensitivity
        self._onset_threshold = 1.0 - self.sensitivity

        logger.info(
            f"Beat Detector initialized: sensitivity={self.sensitivity}, BPM range={self.min_bpm}-{self.max_bpm}"
        )

    async def shutdown(self) -> None:
        """Shutdown."""
        pass

    async def process(self, audio_data: np.ndarray) -> dict[str, Any]:
        """Process audio for beat detection."""
        if not self.enabled:
            return {}

        current_time = time.time()

        # Simple energy-based onset detection
        energy = np.sum(audio_data**2)
        self._energy_buffer.append(energy)

        # Calculate average energy
        if len(self._energy_buffer) < 3:
            avg_energy = energy
        else:
            avg_energy = np.mean(list(self._energy_buffer)[:-1])

        # Detect onset (beat) when energy exceeds threshold
        is_beat = False
        if energy > avg_energy * (1.0 + self._onset_threshold):
            time_since_last = current_time - self._last_beat_time
            min_time = self.hold_time_ms / 1000.0

            if time_since_last > min_time:
                is_beat = True
                self._last_beat_time = current_time
                self._beat_times.append(current_time)

                # Broadcast beat event
                get_event_bus().publish(
                    Events.BEAT,
                    {"time": current_time, "energy": float(energy), "bpm": self._estimated_bpm},
                    source="beat_detector",
                )

        # Estimate BPM from beat times
        if len(self._beat_times) >= 2:
            intervals = []
            beat_list = list(self._beat_times)
            for i in range(1, len(beat_list)):
                interval = beat_list[i] - beat_list[i - 1]
                if 0.2 < interval < 2.0:  # Valid interval (30-300 BPM)
                    intervals.append(interval)

            if intervals:
                avg_interval = np.mean(intervals)
                estimated_bpm = 60.0 / avg_interval

                # Clamp to valid range
                estimated_bpm = max(self.min_bpm, min(self.max_bpm, estimated_bpm))

                # Smooth BPM estimate
                self._estimated_bpm = 0.9 * self._estimated_bpm + 0.1 * estimated_bpm

                # Calculate confidence based on interval variance
                if len(intervals) > 2:
                    variance = np.var(intervals)
                    self._bpm_confidence = max(0, 1.0 - variance * 10)

        # Use librosa for more accurate detection if available
        if HAS_LIBROSA and len(audio_data) >= 2048:
            try:
                # Compute onset strength
                onset_env = librosa.onset.onset_strength(y=audio_data, sr=self._sample_rate)

                # Get tempo estimate
                tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=self._sample_rate)

                if len(tempo) > 0 and tempo[0] > 0:
                    # Use librosa's estimate if confident
                    if self._bpm_confidence < 0.5:
                        self._estimated_bpm = float(tempo[0])
                        self._bpm_confidence = 0.8

            except Exception as e:
                logger.debug(f"Librosa beat detection error: {e}")

        return {
            "is_beat": is_beat,
            "bpm": float(self._estimated_bpm),
            "confidence": float(self._bpm_confidence),
            "energy": float(energy),
            "beat_count": len(self._beat_times),
        }

    def reset(self) -> None:
        """Reset state."""
        self._beat_times.clear()
        self._energy_buffer.clear()
        self._last_beat_time = 0.0
        self._estimated_bpm = 120.0
        self._bpm_confidence = 0.0

    def get_bpm(self) -> float:
        """Get estimated BPM."""
        return self._estimated_bpm

    def get_confidence(self) -> float:
        """Get BPM confidence."""
        return self._bpm_confidence
