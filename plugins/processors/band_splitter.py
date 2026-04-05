"""
Band Splitter Plugin - Split audio into frequency bands
"""

import logging
import math
from typing import Any

import numpy as np

from core.plugin_registry import ProcessorPlugin

logger = logging.getLogger(__name__)


class BandSplitterPlugin(ProcessorPlugin):
    """
    Split audio spectrum into N frequency bands.

    Features:
    - Configurable number of bands (1-16)
    - Linear or logarithmic scale
    - Outputs RMS amplitude, peak frequency, and centroid per band
    """

    plugin_id = "band_splitter"
    display_name = "Band Splitter"
    description = "Split audio into frequency bands"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["numpy"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "bands": {
                "type": "integer",
                "default": 4,
                "minimum": 1,
                "maximum": 16,
                "title": "Number of Bands",
            },
            "scale": {
                "type": "string",
                "default": "logarithmic",
                "enum": ["linear", "logarithmic", "octave"],
                "title": "Band Scale",
                "description": "How to divide the frequency range",
            },
            "min_freq": {"type": "number", "default": 20, "title": "Minimum Frequency (Hz)"},
            "max_freq": {"type": "number", "default": 20000, "title": "Maximum Frequency (Hz)"},
            "sample_rate": {"type": "integer", "default": 44100, "title": "Sample Rate"},
            "enabled": {"type": "boolean", "default": True, "title": "Enabled"},
        },
    }

    # Standard frequency bands for common configurations
    STANDARD_BANDS = {
        3: [(20, 200), (200, 2000), (2000, 20000)],  # Bass, Mid, High
        4: [(20, 200), (200, 800), (800, 4000), (4000, 20000)],  # Bass, Low-Mid, High-Mid, High
        5: [(20, 100), (100, 400), (400, 1600), (1600, 6400), (6400, 20000)],
        8: [  # Octave bands
            (20, 40),
            (40, 80),
            (80, 160),
            (160, 320),
            (320, 640),
            (640, 1280),
            (1280, 2560),
            (2560, 20000),
        ],
    }

    def __init__(self):
        self.bands = 4
        self.scale = "logarithmic"
        self.min_freq = 20
        self.max_freq = 20000
        self.sample_rate = 44100
        self.enabled = True

        self._band_boundaries: list[tuple[float, float]] = []
        self._last_result = {}

    def check_available(self) -> tuple[bool, str]:
        """Always available."""
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize band splitter."""
        self.bands = config.get("bands", 4)
        self.scale = config.get("scale", "logarithmic")
        self.min_freq = config.get("min_freq", 20)
        self.max_freq = config.get("max_freq", 20000)
        self.sample_rate = config.get("sample_rate", 44100)
        self.enabled = config.get("enabled", True)

        # Calculate band boundaries
        self._calculate_bands()

        logger.info(f"Band Splitter initialized: {self.bands} bands, {self.scale} scale")

    def _calculate_bands(self) -> None:
        """Calculate frequency boundaries for each band."""
        self._band_boundaries = []

        if self.bands in self.STANDARD_BANDS and self.scale == "logarithmic":
            # Use standard bands
            self._band_boundaries = self.STANDARD_BANDS[self.bands]
        else:
            # Calculate custom bands
            if self.scale == "linear":
                # Linear spacing
                band_width = (self.max_freq - self.min_freq) / self.bands
                for i in range(self.bands):
                    low = self.min_freq + i * band_width
                    high = low + band_width
                    self._band_boundaries.append((low, high))

            elif self.scale == "logarithmic":
                # Logarithmic spacing
                log_min = math.log10(self.min_freq)
                log_max = math.log10(self.max_freq)
                log_width = (log_max - log_min) / self.bands

                for i in range(self.bands):
                    log_low = log_min + i * log_width
                    log_high = log_low + log_width
                    low = 10**log_low
                    high = 10**log_high
                    self._band_boundaries.append((low, high))

            elif self.scale == "octave":
                # Octave spacing
                # Start from ~20Hz
                start_freq = 20
                for i in range(self.bands):
                    low = start_freq * (2**i)
                    high = low * 2
                    self._band_boundaries.append((low, min(high, self.max_freq)))

    async def shutdown(self) -> None:
        """Shutdown."""
        pass

    async def process(self, audio_data: np.ndarray) -> dict[str, Any]:
        """Split audio into frequency bands."""
        if not self.enabled:
            return {}

        # Compute FFT
        n = len(audio_data)
        fft = np.fft.rfft(audio_data)
        magnitudes = np.abs(fft)
        frequencies = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)

        # Calculate band data
        bands_data = []
        for i, (low_freq, high_freq) in enumerate(self._band_boundaries):
            # Find indices for this band
            mask = (frequencies >= low_freq) & (frequencies < high_freq)

            if np.any(mask):
                band_mags = magnitudes[mask]

                # RMS amplitude
                rms = float(np.sqrt(np.mean(band_mags**2)))

                # Peak frequency
                peak_idx = np.argmax(band_mags)
                peak_freq = float(frequencies[mask][peak_idx])

                # Spectral centroid
                if np.sum(band_mags) > 0:
                    centroid = float(np.sum(frequencies[mask] * band_mags) / np.sum(band_mags))
                else:
                    centroid = (low_freq + high_freq) / 2

            else:
                rms = 0.0
                peak_freq = 0.0
                centroid = (low_freq + high_freq) / 2

            bands_data.append(
                {
                    "band_id": i,
                    "freq_min": low_freq,
                    "freq_max": high_freq,
                    "rms": rms,
                    "peak_freq": peak_freq,
                    "centroid": centroid,
                }
            )

        self._last_result = {"bands": bands_data, "band_count": self.bands, "scale": self.scale}

        return self._last_result

    def reset(self) -> None:
        """Reset state."""
        self._last_result = {}

    def get_band_boundaries(self) -> list[tuple[float, float]]:
        """Get current band boundaries."""
        return self._band_boundaries

    def get_band_for_frequency(self, freq: float) -> int:
        """Get band index for a given frequency."""
        for i, (low, high) in enumerate(self._band_boundaries):
            if low <= freq < high:
                return i
        return self.bands - 1  # Return highest band if out of range
