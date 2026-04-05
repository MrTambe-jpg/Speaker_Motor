"""
FFT Analyzer Plugin - Real-time FFT frequency extraction
"""

import logging
from typing import Any

import numpy as np

from core.plugin_registry import ProcessorPlugin

logger = logging.getLogger(__name__)


class FFTAnalyzerPlugin(ProcessorPlugin):
    """
    Real-time FFT frequency analysis.

    Features:
    - Configurable FFT size (512, 1024, 2048, 4096)
    - Multiple window functions (Hann, Hamming, Blackman, Rectangular)
    - Outputs: frequency bins, magnitude spectrum, peak frequency, RMS
    """

    plugin_id = "fft_analyzer"
    display_name = "FFT Analyzer"
    description = "Real-time FFT frequency analysis"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["numpy", "scipy"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "window": {
                "type": "string",
                "default": "hann",
                "enum": ["hann", "hamming", "blackman", "rectangular", "flattop"],
                "title": "Window Function",
            },
            "size": {
                "type": "integer",
                "default": 2048,
                "enum": [512, 1024, 2048, 4096, 8192],
                "title": "FFT Size",
            },
            "overlap": {
                "type": "number",
                "default": 0.5,
                "minimum": 0,
                "maximum": 0.9,
                "title": "Overlap",
            },
            "enabled": {"type": "boolean", "default": True, "title": "Enabled"},
        },
    }

    def __init__(self):
        self.window = "hann"
        self.size = 2048
        self.overlap = 0.5
        self.sample_rate = 44100
        self.enabled = True

        self._window_func = self._get_window(self.window, self.size)
        self._buffer = np.zeros(4096)
        self._buffer_pos = 0
        self._last_fft = None

    def check_available(self) -> tuple[bool, str]:
        """Always available."""
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize FFT analyzer."""
        self.window = config.get("window", "hann")
        self.size = config.get("size", 2048)
        self.overlap = config.get("overlap", 0.5)
        self.sample_rate = config.get("sample_rate", 44100)
        self.enabled = config.get("enabled", True)

        self._window_func = self._get_window(self.window, self.size)
        self._buffer = np.zeros(self.size * 2)

        logger.info(
            f"FFT Analyzer initialized: size={self.size}, window={self.window}, sample_rate={self.sample_rate}"
        )

    def _get_window(self, window_type: str, size: int) -> np.ndarray:
        """Get window function."""
        if window_type == "hann":
            return np.hanning(size)
        elif window_type == "hamming":
            return np.hamming(size)
        elif window_type == "blackman":
            return np.blackman(size)
        elif window_type == "rectangular":
            return np.ones(size)
        elif window_type == "flattop":
            # Flattop window
            n = np.arange(size)
            a0 = 0.21557895
            a1 = 0.41663158
            a2 = 0.277263158
            a3 = 0.083578947
            a4 = 0.006947368
            return (
                a0
                - a1 * np.cos(2 * np.pi * n / (size - 1))
                + a2 * np.cos(4 * np.pi * n / (size - 1))
                - a3 * np.cos(6 * np.pi * n / (size - 1))
                + a4 * np.cos(8 * np.pi * n / (size - 1))
            )
        else:
            return np.hanning(size)

    async def shutdown(self) -> None:
        """Shutdown."""
        pass

    async def process(self, audio_data: np.ndarray) -> dict[str, Any]:
        """Process audio data with FFT."""
        if not self.enabled:
            return {}

        # Ensure float32
        audio_data = audio_data.astype(np.float32)

        # Pad if needed
        if len(audio_data) < self.size:
            audio_data = np.pad(audio_data, (0, self.size - len(audio_data)))

        # Apply window
        windowed = audio_data[: self.size] * self._window_func

        # Compute FFT
        fft = np.fft.rfft(windowed, n=self.size)
        magnitudes = np.abs(fft)

        # Frequency bins
        freqs = np.fft.rfftfreq(self.size, d=1.0 / self.sample_rate)

        # Find peak frequency
        peak_idx = np.argmax(magnitudes)
        peak_freq = freqs[peak_idx]

        # RMS
        rms = float(np.sqrt(np.mean(audio_data**2)))

        # Normalize magnitudes
        max_mag = np.max(magnitudes) if np.max(magnitudes) > 0 else 1
        normalized_mags = magnitudes / max_mag

        self._last_fft = {
            "frequencies": freqs.tolist(),
            "magnitudes": normalized_mags.tolist(),
            "peak_frequency": float(peak_freq),
            "peak_magnitude": float(magnitudes[peak_idx]),
            "rms": rms,
            "size": self.size,
            "window": self.window,
        }

        return self._last_fft

    def reset(self) -> None:
        """Reset state."""
        self._buffer = np.zeros(self.size * 2)
        self._buffer_pos = 0
        self._last_fft = None


# Window function constants for flattop window
FLATTOP_COEFFS = [0.21557895, 0.41663158, 0.277263158, 0.083578947, 0.006947368]
