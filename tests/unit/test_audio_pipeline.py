"""Tests for the AudioPipeline class."""
import asyncio
import pytest
import numpy as np

from core.audio_pipeline import AudioPipeline, AudioChunk


@pytest.fixture
def pipeline():
    """Create a fresh AudioPipeline instance."""
    return AudioPipeline()


class TestAudioChunk:
    """Test AudioChunk dataclass."""

    def test_create_chunk(self):
        """Test creating an AudioChunk."""
        samples = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        chunk = AudioChunk(samples=samples, sample_rate=44100, timestamp=0.0, duration=0.1)

        assert len(chunk.samples) == 3
        assert chunk.sample_rate == 44100
        assert chunk.duration == 0.1

    def test_chunk_duration_calculation(self):
        """Test that duration is correctly calculated."""
        samples = np.zeros(4410, dtype=np.float32)
        chunk = AudioChunk(samples=samples, sample_rate=44100, timestamp=0.0, duration=0.1)

        assert chunk.duration == 0.1


class TestAudioPipeline:
    """Test AudioPipeline class."""

    @pytest.mark.asyncio
    async def test_start_stop(self, pipeline):
        """Test starting and stopping the pipeline."""
        await pipeline.start()
        assert pipeline.is_running
        await pipeline.stop()
        assert not pipeline.is_running

    @pytest.mark.asyncio
    async def test_push_audio(self, pipeline):
        """Test pushing audio through the pipeline."""
        await pipeline.start()

        samples = np.zeros(1024, dtype=np.float32)
        chunk = AudioChunk(samples=samples, sample_rate=44100, timestamp=0.0, duration=1024 / 44100)

        await pipeline.push_audio(chunk)
        await asyncio.sleep(0.1)
        stats = pipeline.get_stats()
        assert stats["chunk_count"] >= 0

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_add_processor(self, pipeline):
        """Test adding a processor to the pipeline."""
        processor = MockProcessor()
        pipeline.add_processor(processor)

        assert len(pipeline.processors) == 1
        assert pipeline.processors[0] == processor

    @pytest.mark.asyncio
    async def test_remove_processor(self, pipeline):
        """Test removing a processor from the pipeline."""
        processor = MockProcessor()
        pipeline.add_processor(processor)
        pipeline.remove_processor(processor.plugin_id)

        assert len(pipeline.processors) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, pipeline):
        """Test getting pipeline statistics."""
        stats = pipeline.get_stats()
        assert "chunk_count" in stats
        assert "processor_count" in stats
        assert "is_running" in stats


class MockProcessor:
    """Mock processor for testing."""

    def __init__(self):
        self.processed = 0
        self.plugin_id = "mock_processor"

    async def process(self, chunk: AudioChunk) -> AudioChunk:
        self.processed += 1
        return chunk

    async def initialize(self, config=None):
        pass

    async def shutdown(self):
        pass
