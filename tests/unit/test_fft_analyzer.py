"""Tests for the FFT Analyzer processor."""
import numpy as np
import pytest

from plugins.processors.fft_analyzer import FFTAnalyzerPlugin


@pytest.fixture
def analyzer():
    """Create an FFTAnalyzerPlugin with default settings."""
    return FFTAnalyzerPlugin()


class TestFFTAnalyzer:
    """Test FFTAnalyzer class."""

    def test_initialization(self, analyzer):
        """Test that analyzer initializes with correct defaults."""
        assert analyzer.plugin_id == "fft_analyzer"
        assert analyzer.sample_rate == 44100
        assert analyzer.size == 2048

    @pytest.mark.asyncio
    async def test_analyze_sine_wave(self, analyzer):
        """Test analyzing a pure sine wave."""
        freq = 440.0
        t = np.arange(analyzer.size) / analyzer.sample_rate
        signal = np.sin(2 * np.pi * freq * t).astype(np.float32)

        result = await analyzer.process(signal)

        assert result is not None
        assert "magnitudes" in result
        assert "peak_frequency" in result
        assert "rms" in result

    @pytest.mark.asyncio
    async def test_analyze_silence(self, analyzer):
        """Test analyzing silence."""
        signal = np.zeros(analyzer.size, dtype=np.float32)
        result = await analyzer.process(signal)

        assert result is not None
        assert result["rms"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_shape(self, analyzer):
        """Test that magnitudes array has correct shape."""
        signal = np.random.randn(analyzer.size).astype(np.float32)
        result = await analyzer.process(signal)

        expected_size = analyzer.size // 2 + 1
        assert len(result["magnitudes"]) == expected_size

    def test_config_schema(self, analyzer):
        """Test that config schema is defined."""
        schema = analyzer.get_config_schema()
        assert isinstance(schema, dict)

    @pytest.mark.asyncio
    async def test_initialize(self, analyzer):
        """Test analyzer initialization."""
        config = {"sample_rate": 48000, "size": 4096}
        await analyzer.initialize(config)
        assert analyzer.sample_rate == 48000
        assert analyzer.size == 4096
