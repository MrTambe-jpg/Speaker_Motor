"""
Raspberry Pi GPIO Plugin - Direct GPIO PWM control on Raspberry Pi
"""

import logging
from typing import Any

from core.event_bus import Events, get_event_bus
from core.plugin_registry import HardwarePlugin

logger = logging.getLogger(__name__)

# Try to import GPIO libraries
try:
    import RPi.GPIO as GPIO

    HAS_RPI_GPIO = True
except ImportError:
    HAS_RPI_GPIO = False
    GPIO = None

try:
    import pigpio

    HAS_PIGPIO = True
except ImportError:
    HAS_PIGPIO = False
    pigpio = None

import platform


class RaspberryPiGPIOPlugin(HardwarePlugin):
    """
    Direct GPIO PWM control on Raspberry Pi.

    Uses RPi.GPIO for software PWM or pigpio for hardware PWM.
    Requires running ON a Raspberry Pi.

    Supported Pi models: Pi 3, 4, 5, Zero 2W
    """

    plugin_id = "raspberry_pi_gpio"
    display_name = "Raspberry Pi GPIO"
    description = "Direct GPIO PWM motor control on Raspberry Pi"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["linux"]
    requires_pip = []
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "pins": {
                "type": "array",
                "items": {"type": "integer"},
                "default": [13, 14, 27, 26],
                "title": "GPIO Pins",
                "description": "GPIO pin numbers for each motor (BCM numbering)",
            },
            "pwm_frequency": {
                "type": "integer",
                "default": 50,
                "title": "PWM Frequency (Hz)",
                "description": "PWM frequency for servos (typically 50Hz)",
            },
            "use_pigpio": {
                "type": "boolean",
                "default": True,
                "title": "Use pigpio",
                "description": "Use pigpio for hardware PWM (more precise)",
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
        self.pins = [13, 14, 27, 26]
        self.pwm_frequency = 50
        self.use_pigpio = True
        self.angle_range = {"min": 0, "max": 180}

        self.motor_count = 4
        self.pwm_channels: dict[int, Any] = {}
        self.is_connected = False
        self.is_initialized = False
        self._pi = None  # pigpio instance
        self._gpio_mode = None

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        # Check if running on Raspberry Pi
        if platform.system() != "Linux":
            return False, "Not running on Linux (Raspberry Pi required)"

        # Check for Raspberry Pi hardware
        try:
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
                if "Raspberry Pi" not in cpuinfo and "BCM" not in cpuinfo:
                    return False, "Not running on Raspberry Pi hardware"
        except FileNotFoundError:
            return False, "Cannot detect hardware (not a Raspberry Pi)"

        # Check for GPIO library
        if self.use_pigpio and not HAS_PIGPIO:
            if HAS_RPI_GPIO:
                # Fall back to RPi.GPIO
                logger.info("pigpio not available, using RPi.GPIO")
                return True, ""
            return (
                False,
                "Neither pigpio nor RPi.GPIO installed. Run: pip install RPi.GPIO or install pigpio daemon",
            )

        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize GPIO."""
        self.pins = config.get("pins", [13, 14, 27, 26])
        self.pwm_frequency = config.get("pwm_frequency", 50)
        self.use_pigpio = config.get("use_pigpio", True)
        self.angle_range = config.get("angle_range", {"min": 0, "max": 180})
        self.motor_count = len(self.pins)

        try:
            if self.use_pigpio and HAS_PIGPIO:
                await self._init_pigpio()
            elif HAS_RPI_GPIO:
                await self._init_rpi_gpio()
            else:
                raise RuntimeError("No GPIO library available")

            self.is_initialized = True
            self.is_connected = True

            logger.info(
                f"Raspberry Pi GPIO initialized with {self.motor_count} motors on pins {self.pins}"
            )

            get_event_bus().publish(
                Events.HARDWARE_CONNECTED,
                {
                    "plugin": "raspberry_pi_gpio",
                    "pins": self.pins,
                    "pwm_frequency": self.pwm_frequency,
                    "mode": "pigpio" if self.use_pigpio else "RPi.GPIO",
                },
                source="raspberry_pi_gpio",
            )

        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            raise

    async def _init_pigpio(self) -> None:
        """Initialize pigpio for hardware PWM."""
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError("pigpio daemon not running. Run: sudo pigpiod")

        for i, pin in enumerate(self.pins):
            self._pi.set_mode(pin, pigpio.OUTPUT)
            # Start PWM at center position
            pulse_width = self._angle_to_pulsewidth(90)
            self._pi.set_PWM_frequency(pin, self.pwm_frequency)
            self._pi.set_PWM_range(pin, 20000)  # 1MHz / 50Hz = 20000
            self._pi.set_PWM_dutycycle(pin, pulse_width)
            self.pwm_channels[i] = pin

        self._gpio_mode = "pigpio"
        logger.info("Initialized pigpio for hardware PWM")

    async def _init_rpi_gpio(self) -> None:
        """Initialize RPi.GPIO for software PWM."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for i, pin in enumerate(self.pins):
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, self.pwm_frequency)
            pwm.start(self._angle_to_duty_cycle(90))
            self.pwm_channels[i] = pwm

        self._gpio_mode = "RPi.GPIO"
        logger.info("Initialized RPi.GPIO for software PWM")

    def _angle_to_pulsewidth(self, angle: float) -> int:
        """Convert angle to pulse width for pigpio (microseconds)."""
        # Standard servo: 500-2500us for 0-180 degrees at 50Hz
        angle = max(0, min(180, angle))
        return int(500 + (angle / 180.0) * 2000)

    def _angle_to_duty_cycle(self, angle: float) -> float:
        """Convert angle to duty cycle for RPi.GPIO (0-100)."""
        # Standard servo: 2.5% to 12.5% duty cycle for 0-180 degrees
        angle = max(0, min(180, angle))
        return 2.5 + (angle / 180.0) * 10.0

    async def shutdown(self) -> None:
        """Shutdown GPIO."""
        self.is_initialized = False
        self.is_connected = False

        if self._gpio_mode == "pigpio" and self._pi:
            for pin in self.pins:
                self._pi.set_PWM_dutycycle(pin, 0)
            self._pi.stop()

        elif self._gpio_mode == "RPi.GPIO" and GPIO:
            for pwm in self.pwm_channels.values():
                pwm.stop()
            GPIO.cleanup()

        get_event_bus().publish(
            Events.HARDWARE_DISCONNECTED,
            {"plugin": "raspberry_pi_gpio"},
            source="raspberry_pi_gpio",
        )

        logger.info("Raspberry Pi GPIO shutdown")

    async def send_motor_command(self, motor_id: int, frequency: float, amplitude: float) -> None:
        """Send motor command (frequency mode - not typically used for servos)."""
        # For frequency mode, oscillate the servo
        # This is less common for servos but included for compatibility
        angle = 90 + amplitude * 45 * (1 if frequency > 0 else 0)
        await self.set_motor_angle(motor_id, angle)

    async def get_motor_count(self) -> int:
        """Get number of motors."""
        return self.motor_count

    async def ping(self) -> bool:
        """Ping hardware (always succeeds if initialized)."""
        return self.is_initialized

    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """Set motor angle."""
        if motor_id not in self.pwm_channels:
            logger.warning(f"Unknown motor ID: {motor_id}")
            return

        angle = max(self.angle_range["min"], min(self.angle_range["max"], angle))

        if self._gpio_mode == "pigpio" and self._pi:
            pin = self.pwm_channels[motor_id]
            pulse_width = self._angle_to_pulsewidth(angle)
            self._pi.set_PWM_dutycycle(pin, pulse_width)

        elif self._gpio_mode == "RPi.GPIO":
            pwm = self.pwm_channels[motor_id]
            duty_cycle = self._angle_to_duty_cycle(angle)
            pwm.ChangeDutyCycle(duty_cycle)

        # Broadcast state
        get_event_bus().publish(
            Events.MOTOR_STATE, {"motor_id": motor_id, "angle": angle}, source="raspberry_pi_gpio"
        )
