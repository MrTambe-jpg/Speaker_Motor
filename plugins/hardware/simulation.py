"""
Simulation Plugin - Virtual motor driver (no hardware required)
"""

import asyncio
import contextlib
import logging
from typing import Any, Optional

from core.plugin_registry import HardwarePlugin

logger = logging.getLogger(__name__)


class SimulationPlugin(HardwarePlugin):
    """
    Virtual motors for development and testing.

    No hardware required - simulates motor response with configurable latency.
    Perfect for testing the system without physical motors.
    """

    plugin_id = "simulation"
    display_name = "Simulation (Virtual Motors)"
    description = "Virtual motor driver for development and testing. No hardware required."
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = []
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "motor_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 16,
                "default": 4,
                "title": "Number of Motors",
                "description": "Number of virtual motors to simulate",
            },
            "response_latency_ms": {
                "type": "integer",
                "minimum": 0,
                "maximum": 500,
                "default": 5,
                "title": "Response Latency (ms)",
                "description": "Simulated motor response latency in milliseconds",
            },
            "jitter_percent": {
                "type": "number",
                "minimum": 0,
                "maximum": 20,
                "default": 2,
                "title": "Jitter (%)",
                "description": "Random position jitter percentage",
            },
            "angle_range": {
                "type": "object",
                "properties": {
                    "min": {"type": "number", "default": 0},
                    "max": {"type": "number", "default": 180},
                },
                "default": {"min": 0, "max": 180},
            },
        },
    }

    def __init__(self):
        self.motor_count = 4
        self.response_latency_ms = 5
        self.jitter_percent = 2
        self.motor_angles: dict[int, float] = {}
        self.motor_targets: dict[int, float] = {}
        self.motor_velocities: dict[int, float] = {}
        self.is_initialized = False
        self._update_task: Optional[asyncio.Task] = None

    def check_available(self) -> tuple[bool, str]:
        """Simulation is always available."""
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize simulation."""
        self.motor_count = config.get("motor_count", 4)
        self.response_latency_ms = config.get("response_latency_ms", 5)
        self.jitter_percent = config.get("jitter_percent", 2)

        # Initialize all motors to center position
        for i in range(self.motor_count):
            self.motor_angles[i] = 90.0
            self.motor_targets[i] = 90.0
            self.motor_velocities[i] = 0.0

        self.is_initialized = True
        self._update_task = asyncio.create_task(self._update_loop())

        logger.info(f"Simulation initialized with {self.motor_count} virtual motors")

    async def shutdown(self) -> None:
        """Shutdown simulation."""
        self.is_initialized = False

        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
            self._update_task = None

        logger.info("Simulation shutdown")

    async def send_motor_command(self, motor_id: int, frequency: float, amplitude: float) -> None:
        """Send command to virtual motor."""
        if motor_id not in self.motor_angles:
            logger.warning(f"Unknown motor ID: {motor_id}")
            return

        # Simulate frequency-to-angle conversion (for demo purposes)
        # In real usage, use set_motor_angle instead
        angle = 90 + amplitude * 45 * (1 if frequency > 0 else 0)
        self.motor_targets[motor_id] = angle

    async def get_motor_count(self) -> int:
        """Get number of motors."""
        return self.motor_count

    async def ping(self) -> bool:
        """Ping virtual hardware (always succeeds)."""
        return self.is_initialized

    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """Set motor angle."""
        if motor_id not in self.motor_angles:
            logger.warning(f"Unknown motor ID: {motor_id}")
            return

        # Clamp angle to valid range
        angle = max(0, min(180, angle))
        self.motor_targets[motor_id] = angle

        # Simulate response latency
        await asyncio.sleep(self.response_latency_ms / 1000.0)

    async def _update_loop(self) -> None:
        """Update motor positions smoothly."""
        import random

        while self.is_initialized:
            try:
                for motor_id in self.motor_angles:
                    target = self.motor_targets[motor_id]
                    current = self.motor_angles[motor_id]

                    # Smooth movement towards target
                    diff = target - current
                    move = diff * 0.3  # Smoothing factor
                    new_angle = current + move

                    # Add jitter
                    if self.jitter_percent > 0:
                        jitter = random.uniform(-self.jitter_percent, self.jitter_percent)
                        new_angle += jitter * 0.1

                    self.motor_angles[motor_id] = max(0, min(180, new_angle))

                await asyncio.sleep(0.02)  # 50Hz update

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation update loop: {e}")

    def get_motor_state(self) -> dict[str, Any]:
        """Get current motor states."""
        return {
            "motor_count": self.motor_count,
            "angles": {str(k): v for k, v in self.motor_angles.items()},
            "targets": {str(k): v for k, v in self.motor_targets.items()},
            "is_initialized": self.is_initialized,
        }
