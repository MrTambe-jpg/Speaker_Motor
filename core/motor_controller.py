"""
Motor Controller - Abstract motor control interface for OMNISOUND
"""

import asyncio
import contextlib
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from .config_manager import get_config_manager
from .event_bus import Events, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class MotorState:
    """Represents the current state of a motor."""

    id: int
    name: str
    enabled: bool
    mode: str  # "frequency_band", "beat", "pitch_track", "manual", "off"
    angle: float = 90.0
    frequency: float = 0.0
    amplitude: float = 0.0
    target_angle: float = 90.0
    last_update: float = 0.0

    # Frequency band mode
    freq_min_hz: float = 20.0
    freq_max_hz: float = 20000.0
    angle_min: float = 45.0
    angle_max: float = 135.0
    center_angle: float = 90.0
    smoothing: float = 0.3
    invert: bool = False

    # Beat mode
    beat_kick_angle: float = 135.0
    beat_rest_angle: float = 90.0
    beat_hold_ms: float = 80.0


class MotorController:
    """
    Abstract motor control interface.

    - Manages motor states and configurations
    - Converts audio data to motor commands
    - Handles smoothing and interpolation
    - Sends commands to hardware plugins
    """

    def __init__(self):
        self.config = get_config_manager()
        self.event_bus = get_event_bus()
        self.motors: dict[int, MotorState] = {}
        self.hardware_plugin: Optional[Any] = None
        self.is_running = False
        self._update_task: Optional[asyncio.Task] = None

        # State tracking
        self._angle_history: dict[int, deque] = {}
        self._last_beat_time: float = 0.0
        self._beat_state: dict[int, bool] = {}

        # Load motor configurations
        self._load_motor_configs()

        # Subscribe to events
        self.event_bus.subscribe("processed_data", self._on_processed_data)

    def _load_motor_configs(self) -> None:
        """Load motor configurations from config."""
        motor_mappings = self.config.get("motors.mapping", [])

        for mapping in motor_mappings:
            motor_id = mapping.get("id", 0)
            self.motors[motor_id] = MotorState(
                id=motor_id,
                name=mapping.get("name", f"Motor {motor_id}"),
                enabled=mapping.get("enabled", True),
                mode=mapping.get("mode", "frequency_band"),
                freq_min_hz=mapping.get("freq_min_hz", 20.0),
                freq_max_hz=mapping.get("freq_max_hz", 20000.0),
                angle_min=mapping.get("angle_min", 45.0),
                angle_max=mapping.get("angle_max", 135.0),
                center_angle=mapping.get("center_angle", 90.0),
                smoothing=mapping.get("smoothing", 0.3),
                invert=mapping.get("invert", False),
                beat_kick_angle=mapping.get("beat_kick_angle", 135.0),
                beat_rest_angle=mapping.get("beat_rest_angle", 90.0),
                beat_hold_ms=mapping.get("beat_hold_ms", 80.0),
            )
            self._angle_history[motor_id] = deque(maxlen=10)
            self._beat_state[motor_id] = False

    def set_hardware_plugin(self, plugin: Any) -> None:
        """
        Set the hardware plugin for motor control.

        Args:
            plugin: HardwarePlugin instance
        """
        self.hardware_plugin = plugin
        logger.info(f"Set hardware plugin: {plugin.plugin_id if plugin else 'None'}")

    async def start(self) -> None:
        """Start the motor controller."""
        if self.is_running:
            return

        self.is_running = True
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info(f"Motor controller started with {len(self.motors)} motors")

    async def stop(self) -> None:
        """Stop the motor controller."""
        if not self.is_running:
            return

        self.is_running = False

        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
            self._update_task = None

        logger.info("Motor controller stopped")

    def _on_processed_data(self, event: Any) -> None:
        """Handle processed audio data event."""
        if not self.is_running:
            return

        data = event.data
        # Schedule async processing
        asyncio.create_task(self._process_audio_data(data))

    async def _process_audio_data(self, data: dict[str, Any]) -> None:
        """Process audio data and update motor states."""
        for motor_id, motor_state in self.motors.items():
            if not motor_state.enabled:
                continue

            mode = motor_state.mode

            if mode == "frequency_band":
                await self._update_frequency_band_motor(motor_id, motor_state, data)
            elif mode == "beat":
                await self._update_beat_motor(motor_id, motor_state, data)
            elif mode == "pitch_track":
                await self._update_pitch_track_motor(motor_id, motor_state, data)
            elif mode == "manual":
                # Manual mode: angle set directly via API
                pass

    async def _update_frequency_band_motor(
        self, motor_id: int, motor_state: MotorState, data: dict[str, Any]
    ) -> None:
        """Update a frequency band mode motor."""
        band_data = data.get("band_splitter", {}).get("bands", [])
        fft_data = data.get("fft_analyzer", {})

        # Find the band data for this motor's frequency range
        band_amplitude = 0.0

        if band_data:
            for band in band_data:
                freq_min = band.get("freq_min", 0)
                freq_max = band.get("freq_max", 0)

                # Check if this band overlaps with motor's frequency range
                if motor_state.freq_min_hz <= freq_max and motor_state.freq_max_hz >= freq_min:
                    # Weighted by overlap
                    overlap = min(motor_state.freq_max_hz, freq_max) - max(
                        motor_state.freq_min_hz, freq_min
                    )
                    overlap = max(0, overlap) / (motor_state.freq_max_hz - motor_state.freq_min_hz)
                    band_amplitude = max(band_amplitude, band.get("rms", 0.0) * overlap)

        else:
            # Calculate from FFT directly
            if "frequencies" in fft_data and "magnitudes" in fft_data:
                freqs = fft_data["frequencies"]
                mags = fft_data["magnitudes"]

                # Find frequency range
                mask = (freqs >= motor_state.freq_min_hz) & (freqs <= motor_state.freq_max_hz)
                if mask.any():
                    band_amplitude = float(np.sqrt(np.mean(np.array(mags)[mask] ** 2)))

        # Map amplitude to angle
        target_angle = self._map_amplitude_to_angle(
            band_amplitude,
            motor_state.angle_min,
            motor_state.angle_max,
            motor_state.center_angle,
            motor_state.invert,
        )

        # Apply smoothing
        smoothed_angle = self._apply_smoothing(
            motor_state.angle, target_angle, motor_state.smoothing
        )

        # Update state
        motor_state.angle = smoothed_angle
        motor_state.amplitude = band_amplitude
        motor_state.last_update = time.time()

        # Store in history
        self._angle_history[motor_id].append(smoothed_angle)

        # Send to hardware
        await self._send_motor_command(motor_id, smoothed_angle, band_amplitude)

    async def _update_beat_motor(
        self, motor_id: int, motor_state: MotorState, data: dict[str, Any]
    ) -> None:
        """Update a beat mode motor."""
        beat_data = data.get("beat_detector", {})
        is_beat = beat_data.get("is_beat", False)

        current_time = time.time()
        beat_hold_s = motor_state.beat_hold_ms / 1000.0

        if is_beat and not self._beat_state.get(motor_id, False):
            # New beat detected
            self._beat_state[motor_id] = True
            self._last_beat_time = current_time
            target_angle = motor_state.beat_kick_angle
        elif self._beat_state.get(motor_id, False):
            # Check if beat hold time has elapsed
            if current_time - self._last_beat_time > beat_hold_s:
                self._beat_state[motor_id] = False
                target_angle = motor_state.beat_rest_angle
            else:
                target_angle = motor_state.beat_kick_angle
        else:
            target_angle = motor_state.beat_rest_angle

        # Apply smoothing
        smoothed_angle = self._apply_smoothing(
            motor_state.angle, target_angle, motor_state.smoothing
        )

        # Update state
        motor_state.angle = smoothed_angle
        motor_state.amplitude = 1.0 if is_beat else 0.0
        motor_state.last_update = current_time

        # Send to hardware
        await self._send_motor_command(motor_id, smoothed_angle, motor_state.amplitude)

    async def _update_pitch_track_motor(
        self, motor_id: int, motor_state: MotorState, data: dict[str, Any]
    ) -> None:
        """Update a pitch track mode motor."""
        pitch_data = data.get("pitch_tracker", {})
        frequency = pitch_data.get("frequency", 0.0)
        confidence = pitch_data.get("confidence", 0.0)

        if confidence < 0.5:
            return  # Low confidence, don't update

        # Map frequency to angle
        # Use log scale for frequency mapping
        import numpy as np

        log_freq_min = np.log10(max(motor_state.freq_min_hz, 20))
        log_freq_max = np.log10(max(motor_state.freq_max_hz, 20000))
        log_freq = np.log10(max(frequency, 20))

        # Normalize to 0-1 range
        normalized = (log_freq - log_freq_min) / (log_freq_max - log_freq_min)
        normalized = max(0, min(1, normalized))

        # Map to angle
        target_angle = motor_state.angle_min + normalized * (
            motor_state.angle_max - motor_state.angle_min
        )

        if motor_state.invert:
            target_angle = motor_state.angle_max - (target_angle - motor_state.angle_min)

        # Apply smoothing
        smoothed_angle = self._apply_smoothing(
            motor_state.angle, target_angle, motor_state.smoothing
        )

        # Update state
        motor_state.angle = smoothed_angle
        motor_state.frequency = frequency
        motor_state.amplitude = confidence
        motor_state.last_update = time.time()

        # Send to hardware
        await self._send_motor_command(motor_id, smoothed_angle, confidence)

    def _map_amplitude_to_angle(
        self, amplitude: float, angle_min: float, angle_max: float, center: float, invert: bool
    ) -> float:
        """Map amplitude (0-1) to angle range."""
        # Clamp amplitude
        amplitude = max(0.0, min(1.0, amplitude))

        # Map to angle
        if invert:
            angle = angle_max - amplitude * (angle_max - angle_min)
        else:
            angle = angle_min + amplitude * (angle_max - angle_min)

        return angle

    def _apply_smoothing(self, current: float, target: float, smoothing: float) -> float:
        """Apply exponential smoothing to angle."""
        if smoothing <= 0:
            return target
        return current + (target - current) * (1.0 - smoothing)

    async def _send_motor_command(self, motor_id: int, angle: float, amplitude: float) -> None:
        """Send motor command to hardware plugin."""
        if not self.hardware_plugin:
            return

        try:
            await self.hardware_plugin.set_motor_angle(motor_id, angle)

            # Broadcast motor state
            self.event_bus.publish(
                Events.MOTOR_STATE,
                {
                    "motor_id": motor_id,
                    "angle": angle,
                    "amplitude": amplitude,
                    "timestamp": time.time(),
                },
                source="motor_controller",
            )

        except Exception as e:
            logger.error(f"Error sending motor command: {e}")

    async def _update_loop(self) -> None:
        """Main update loop for motor controller."""
        while self.is_running:
            try:
                # Broadcast motor states periodically
                states = []
                for motor_id, motor_state in self.motors.items():
                    states.append(
                        {
                            "id": motor_id,
                            "name": motor_state.name,
                            "angle": motor_state.angle,
                            "frequency": motor_state.frequency,
                            "amplitude": motor_state.amplitude,
                            "enabled": motor_state.enabled,
                            "mode": motor_state.mode,
                        }
                    )

                self.event_bus.publish(
                    Events.MOTOR_STATE,
                    {"motors": states, "timestamp": time.time()},
                    source="motor_controller",
                )

                await asyncio.sleep(0.05)  # 20Hz update rate

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in motor update loop: {e}")

    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """
        Set a motor to a specific angle (manual mode).

        Args:
            motor_id: Motor ID
            angle: Angle in degrees (0-180)
        """
        if motor_id not in self.motors:
            logger.warning(f"Unknown motor ID: {motor_id}")
            return

        motor_state = self.motors[motor_id]
        motor_state.angle = max(motor_state.angle_min, min(motor_state.angle_max, angle))
        motor_state.mode = "manual"

        if self.hardware_plugin:
            await self.hardware_plugin.set_motor_angle(motor_id, motor_state.angle)

    async def test_motor(self, motor_id: int) -> None:
        """
        Test a motor by sweeping through its range.

        Args:
            motor_id: Motor ID to test
        """
        if motor_id not in self.motors:
            return

        motor_state = self.motors[motor_id]

        if not self.hardware_plugin:
            logger.warning("No hardware plugin set")
            return

        # Sweep from min to max
        for angle in range(int(motor_state.angle_min), int(motor_state.angle_max) + 1, 5):
            await self.hardware_plugin.set_motor_angle(motor_id, angle)
            await asyncio.sleep(0.05)

        # Sweep back
        for angle in range(int(motor_state.angle_max), int(motor_state.angle_min) - 1, -5):
            await self.hardware_plugin.set_motor_angle(motor_id, angle)
            await asyncio.sleep(0.05)

        # Return to center
        await self.hardware_plugin.set_motor_angle(motor_id, motor_state.center_angle)
        motor_state.angle = motor_state.center_angle

    def update_motor_config(self, motor_id: int, config: dict[str, Any]) -> None:
        """
        Update configuration for a motor.

        Args:
            motor_id: Motor ID
            config: New configuration values
        """
        if motor_id not in self.motors:
            return

        motor_state = self.motors[motor_id]

        # Update allowed fields
        for key, value in config.items():
            if hasattr(motor_state, key):
                setattr(motor_state, key, value)

        # Update config file
        self.config.set_motor_config(motor_id, config)

    def get_motor_state(self, motor_id: int) -> Optional[MotorState]:
        """Get current state of a motor."""
        return self.motors.get(motor_id)

    def get_all_states(self) -> list[dict[str, Any]]:
        """Get current states of all motors."""
        return [
            {
                "id": m.id,
                "name": m.name,
                "angle": m.angle,
                "frequency": m.frequency,
                "amplitude": m.amplitude,
                "enabled": m.enabled,
                "mode": m.mode,
                "freq_min_hz": m.freq_min_hz,
                "freq_max_hz": m.freq_max_hz,
                "angle_min": m.angle_min,
                "angle_max": m.angle_max,
            }
            for m in self.motors.values()
        ]


# Global singleton
_motor_controller: Optional[MotorController] = None


def get_motor_controller() -> MotorController:
    """Get the global motor controller instance."""
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller


def reset_motor_controller() -> MotorController:
    """Reset the global motor controller."""
    global _motor_controller
    _motor_controller = MotorController()
    return _motor_controller
