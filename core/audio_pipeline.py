"""
Audio Pipeline - Audio processing pipeline for OMNISOUND
"""

import asyncio
import contextlib
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np

from .config_manager import get_config_manager
from .event_bus import Events, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents a chunk of audio data."""

    samples: np.ndarray
    sample_rate: int
    timestamp: float
    duration: float
    rms: float = 0.0
    peak: float = 0.0


class AudioPipeline:
    """
    Audio processing pipeline.

    - Receives audio chunks from AudioSourcePlugin
    - Passes through active ProcessorPlugins
    - Outputs processed data for motor control
    - Broadcasts events for visualization
    """

    def __init__(self):
        self.config = get_config_manager()
        self.event_bus = get_event_bus()
        self.processors: list[Any] = []  # ProcessorPlugin instances
        self.is_running = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._process_task: Optional[asyncio.Task] = None

        # Audio settings from config
        self.sample_rate = self.config.get("audio.sample_rate", 44100)
        self.chunk_size = self.config.get("audio.chunk_size", 512)

        # State tracking
        self._last_chunk_time = 0.0
        self._chunk_count = 0
        self._audio_buffer: deque = deque(maxlen=10)  # Keep last 10 chunks for analysis

        # Noise gate
        self.noise_gate_threshold = 0.01  # Will be set from config

        # Callbacks
        self._on_audio_chunk_callbacks: list[Callable] = []
        self._on_processed_callbacks: list[Callable] = []

    async def start(self) -> None:
        """Start the audio pipeline."""
        if self.is_running:
            logger.warning("Audio pipeline already running")
            return

        self.is_running = True
        self._process_task = asyncio.create_task(self._process_loop())
        logger.info("Audio pipeline started")

        self.event_bus.publish(
            Events.AUDIO_STARTED,
            {"sample_rate": self.sample_rate, "chunk_size": self.chunk_size},
            source="audio_pipeline",
        )

    async def stop(self) -> None:
        """Stop the audio pipeline."""
        if not self.is_running:
            return

        self.is_running = False

        if self._process_task:
            self._process_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._process_task
            self._process_task = None

        logger.info("Audio pipeline stopped")

        self.event_bus.publish(Events.AUDIO_STOPPED, {}, source="audio_pipeline")

    async def push_audio(self, audio_chunk: AudioChunk) -> None:
        """
        Push audio data into the pipeline.

        Args:
            audio_chunk: Audio data to process
        """
        await self._audio_queue.put(audio_chunk)

    def add_processor(self, processor: Any) -> None:
        """
        Add a processor to the pipeline.

        Args:
            processor: ProcessorPlugin instance
        """
        self.processors.append(processor)
        logger.info(f"Added processor: {processor.plugin_id}")

    def remove_processor(self, processor_id: str) -> None:
        """Remove a processor by ID."""
        self.processors = [p for p in self.processors if p.plugin_id != processor_id]
        logger.info(f"Removed processor: {processor_id}")

    def clear_processors(self) -> None:
        """Remove all processors."""
        self.processors.clear()
        logger.info("Cleared all processors")

    def on_audio_chunk(self, callback: Callable) -> None:
        """Register a callback for raw audio chunks."""
        self._on_audio_chunk_callbacks.append(callback)

    def on_processed(self, callback: Callable) -> None:
        """Register a callback for processed audio data."""
        self._on_processed_callbacks.append(callback)

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self.is_running:
            try:
                # Get audio chunk with timeout
                try:
                    chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                # Store chunk
                self._audio_buffer.append(chunk)
                self._chunk_count += 1

                # Calculate basic metrics
                chunk.rms = float(np.sqrt(np.mean(chunk.samples**2)))
                chunk.peak = float(np.max(np.abs(chunk.samples)))

                # Apply noise gate
                if chunk.rms < self.noise_gate_threshold:
                    # Skip processing if below threshold
                    continue

                # Broadcast raw audio event
                self.event_bus.publish(
                    Events.AUDIO_DATA,
                    {
                        "samples": chunk.samples.tolist()[: min(1024, len(chunk.samples))],
                        "sample_rate": chunk.sample_rate,
                        "rms": chunk.rms,
                        "peak": chunk.peak,
                        "timestamp": chunk.timestamp,
                        "chunk_id": self._chunk_count,
                    },
                    source="audio_pipeline",
                )

                # Process through all processors
                processed_data = await self._process_chunk(chunk)

                # Broadcast processed data
                self.event_bus.publish("processed_data", processed_data, source="audio_pipeline")

                # Call registered callbacks
                for callback in self._on_processed_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(processed_data)
                        else:
                            callback(processed_data)
                    except Exception as e:
                        logger.error(f"Error in processed callback: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")

    async def _process_chunk(self, chunk: AudioChunk) -> dict[str, Any]:
        """
        Process a chunk through all active processors.

        Args:
            chunk: Audio chunk to process

        Returns:
            Dictionary of processed results
        """
        result = {
            "timestamp": chunk.timestamp,
            "sample_rate": chunk.sample_rate,
            "rms": chunk.rms,
            "peak": chunk.peak,
        }

        # Get active processors from config
        active_processors = self.config.get("processors.active", [])

        for processor in self.processors:
            if processor.plugin_id not in active_processors:
                continue

            try:
                processor_result = await processor.process(chunk.samples)
                result[processor.plugin_id] = processor_result
            except Exception as e:
                logger.error(f"Error in processor {processor.plugin_id}: {e}")

        return result

    def get_frequency_bands(
        self, processed_data: dict[str, Any], motor_configs: list[dict]
    ) -> dict[int, dict[str, float]]:
        """
        Extract frequency band data for motor control.

        Args:
            processed_data: Output from processors
            motor_configs: Motor configuration list

        Returns:
            Dictionary mapping motor ID to band data
        """
        bands_data = {}

        # Get FFT/band data from processors
        fft_data = processed_data.get("fft_analyzer", {})
        band_data = processed_data.get("band_splitter", {}).get("bands", [])

        for motor_config in motor_configs:
            motor_id = motor_config.get("id", 0)
            mode = motor_config.get("mode", "frequency_band")

            if mode == "frequency_band":
                # Get band index from frequency range
                freq_min = motor_config.get("freq_min_hz", 20)
                freq_max = motor_config.get("freq_max_hz", 20000)

                if band_data:
                    # Find matching band
                    for _i, band in enumerate(band_data):
                        band_min = band.get("freq_min", 0)
                        band_max = band.get("freq_max", 0)

                        if band_min <= freq_min <= band_max or band_min <= freq_max <= band_max:
                            bands_data[motor_id] = {
                                "rms": band.get("rms", 0.0),
                                "peak_freq": band.get("peak_freq", 0.0),
                                "centroid": band.get("centroid", 0.0),
                            }
                            break
                else:
                    # Fallback: compute from FFT data
                    if "magnitudes" in fft_data and "frequencies" in fft_data:
                        freqs = np.array(fft_data["frequencies"])
                        mags = np.array(fft_data["magnitudes"])

                        # Find frequency range
                        mask = (freqs >= freq_min) & (freqs <= freq_max)
                        if np.any(mask):
                            bands_data[motor_id] = {
                                "rms": float(np.sqrt(np.mean(mags[mask] ** 2))),
                                "peak_freq": float(freqs[mask][np.argmax(mags[mask])]),
                                "centroid": float(
                                    np.sum(freqs[mask] * mags[mask]) / np.sum(mags[mask])
                                ),
                            }

            elif mode == "beat":
                beat_data = processed_data.get("beat_detector", {})
                bands_data[motor_id] = {
                    "is_beat": beat_data.get("is_beat", False),
                    "bpm": beat_data.get("bpm", 0),
                    "confidence": beat_data.get("confidence", 0.0),
                }

            elif mode == "pitch_track":
                pitch_data = processed_data.get("pitch_tracker", {})
                bands_data[motor_id] = {
                    "frequency": pitch_data.get("frequency", 0.0),
                    "confidence": pitch_data.get("confidence", 0.0),
                    "note": pitch_data.get("note", ""),
                }

        return bands_data

    def get_audio_buffer(self) -> list[np.ndarray]:
        """Get the current audio buffer for visualization."""
        return list(self._audio_buffer)

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "is_running": self.is_running,
            "chunk_count": self._chunk_count,
            "sample_rate": self.sample_rate,
            "chunk_size": self.chunk_size,
            "processor_count": len(self.processors),
            "buffer_size": len(self._audio_buffer),
        }


# Global singleton
_audio_pipeline: Optional[AudioPipeline] = None


def get_audio_pipeline() -> AudioPipeline:
    """Get the global audio pipeline instance."""
    global _audio_pipeline
    if _audio_pipeline is None:
        _audio_pipeline = AudioPipeline()
    return _audio_pipeline


def reset_audio_pipeline() -> AudioPipeline:
    """Reset the global audio pipeline."""
    global _audio_pipeline
    _audio_pipeline = AudioPipeline()
    return _audio_pipeline
