"""Tests for the Beat Detector processor."""
import numpy as np
import pytest

from plugins.processors.beat_detector import BeatDetectorPlugin


@pytest.fixture
def detector():
    """Create a BeatDetectorPlugin with default settings."""
    return BeatDetectorPlugin()


class TestBeatDetector:
    """Test BeatDetector class."""

    def test_initialization(self, detector):
        """Test that detector initializes with correct defaults."""
        assert detector.plugin_id == "beat_detector"

    @pytest.mark.asyncio
    async def test_detect_silence(self, detector):
        """Test that silence does not trigger a beat."""
        signal = np.zeros(1024, dtype=np.float32)
        result = await detector.process(signal)

        assert result is not None
        assert result.get("is_beat", False) is False

    @pytest.mark.asyncio
    async def test_detect_impulse(self, detector):
        """Test that a strong impulse triggers a beat."""
        silence = np.zeros(1024, dtype=np.float32)
        impulse = np.zeros(1024, dtype=np.float32)
        impulse[0] = 1.0

        results = []
        for _ in range(10):
            result = await detector.process(silence)
            results.append(result.get("is_beat", False))

        result = await detector.process(impulse)
        results.append(result.get("is_beat", False))

        assert any(results)

    @pytest.mark.asyncio
    async def test_detect_returns_energy(self, detector):
        """Test that detection returns energy value."""
        signal = np.random.randn(1024).astype(np.float32)
        result = await detector.process(signal)

        assert "energy" in result

    def test_config_schema(self, detector):
        """Test that config schema is defined."""
        schema = detector.get_config_schema()
        assert isinstance(schema, dict)
