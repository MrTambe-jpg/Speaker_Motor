"""
Arduino Serial Plugin - Connect to Arduino via Serial/USB
"""

import asyncio
import logging
from typing import Any, Optional

try:
    import serial
    import serial.tools.list_ports

    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    serial = None

import contextlib

from core.event_bus import Events, get_event_bus
from core.plugin_registry import HardwarePlugin

logger = logging.getLogger(__name__)


class ArduinoSerialPlugin(HardwarePlugin):
    """
    Connect to Arduino motor controller via serial/USB.

    Supports Arduino Uno, Mega, Nano, Leonardo, Due, Micro.
    Protocol: "M{motor} F{frequency} A{amplitude}\n"
    """

    plugin_id = "arduino_serial"
    display_name = "Arduino Serial"
    description = "Connect to Arduino motor controller via USB/Serial"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["pyserial"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "default": "COM3",
                "title": "Serial Port",
                "description": "Serial port (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)",
            },
            "baud_rate": {
                "type": "integer",
                "default": 115200,
                "title": "Baud Rate",
                "enum": [9600, 19200, 38400, 57600, 115200, 230400],
            },
            "auto_detect_port": {
                "type": "boolean",
                "default": True,
                "title": "Auto-detect Port",
                "description": "Automatically detect Arduino port",
            },
            "timeout_ms": {
                "type": "integer",
                "default": 1000,
                "title": "Timeout (ms)",
                "description": "Serial communication timeout",
            },
            "motor_count": {
                "type": "integer",
                "default": 4,
                "minimum": 1,
                "maximum": 8,
                "title": "Motor Count",
                "description": "Number of motors connected to Arduino",
            },
        },
    }

    def __init__(self):
        self.port = "COM3"
        self.baud_rate = 115200
        self.auto_detect_port = True
        self.timeout_ms = 1000
        self.motor_count = 4

        self.serial = None
        self.is_connected = False
        self.is_initialized = False
        self._read_task: Optional[asyncio.Task] = None
        self._write_lock = asyncio.Lock()

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        try:
            import serial  # noqa: F401

            return True, ""
        except ImportError:
            return False, "pyserial library not installed. Run: pip install pyserial"

    @staticmethod
    def list_ports() -> list[dict[str, str]]:
        """List all available serial ports."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(
                {
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid or "",
                    "manufacturer": port.manufacturer or "",
                    "product": port.product or "",
                }
            )
        return ports

    @staticmethod
    def auto_detect_arduino() -> Optional[str]:
        """Auto-detect Arduino port."""
        arduino_identifiers = ["Arduino", "CH340", "CP210", "FT232", "USB Serial", "USB2.0 Serial"]

        for port_info in serial.tools.list_ports.comports():
            description = (port_info.description or "").lower()
            manufacturer = (port_info.manufacturer or "").lower()
            product = (port_info.product or "").lower()
            hwid = (port_info.hwid or "").lower()

            combined = f"{description} {manufacturer} {product} {hwid}"

            for identifier in arduino_identifiers:
                if identifier.lower() in combined:
                    return port_info.device

        return None

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize Arduino connection."""
        self.port = config.get("port", "COM3")
        self.baud_rate = config.get("baud_rate", 115200)
        self.auto_detect_port = config.get("auto_detect_port", True)
        self.timeout_ms = config.get("timeout_ms", 1000)
        self.motor_count = config.get("motor_count", 4)

        # Auto-detect port if enabled
        if self.auto_detect_port:
            detected_port = self.auto_detect_arduino()
            if detected_port:
                self.port = detected_port
                logger.info(f"Auto-detected Arduino on {self.port}")
            else:
                logger.warning(f"Could not auto-detect Arduino, using {self.port}")

        # Connect to serial port
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout_ms / 1000.0,
                write_timeout=self.timeout_ms / 1000.0,
            )

            # Wait for Arduino to reset
            await asyncio.sleep(2)

            # Read initial config from Arduino
            await self._send_command("?")  # Query config

            self.is_connected = True
            self.is_initialized = True

            # Start read task
            self._read_task = asyncio.create_task(self._read_loop())

            logger.info(f"Connected to Arduino on {self.port} at {self.baud_rate} baud")

            get_event_bus().publish(
                Events.HARDWARE_CONNECTED,
                {"plugin": "arduino_serial", "port": self.port, "baud_rate": self.baud_rate},
                source="arduino_serial",
            )

        except serial.SerialException as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            self.is_connected = False
            raise

    async def _read_loop(self) -> None:
        """Read messages from Arduino."""
        while self.is_connected and self.serial:
            try:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        await self._handle_message(line)
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Read error: {e}")
                self.is_connected = False
                break

    async def _handle_message(self, message: str) -> None:
        """Handle message from Arduino."""
        if message.startswith("OK"):
            # Acknowledgment
            pass
        elif message.startswith("ERROR"):
            logger.error(f"Arduino error: {message}")
        elif message.startswith("CONFIG:"):
            # Configuration response
            try:
                config_str = message[7:]
                parts = config_str.split(",")
                for part in parts:
                    if part.startswith("M"):
                        self.motor_count = int(part[1:])
            except Exception:
                pass
        elif message.startswith("STATE:"):
            # Motor state update
            try:
                state_str = message[6:]
                parts = state_str.split(",")
                motors = []
                for part in parts:
                    if ":" in part:
                        motor_id, angle = part.split(":")
                        motors.append({"id": int(motor_id), "angle": float(angle)})

                get_event_bus().publish(
                    Events.MOTOR_STATE, {"motors": motors}, source="arduino_serial"
                )
            except Exception:
                pass

    async def _send_command(self, command: str) -> bool:
        """Send command to Arduino."""
        async with self._write_lock:
            if not self.is_connected or not self.serial:
                return False

            try:
                self.serial.write((command + "\n").encode("utf-8"))
                return True
            except Exception as e:
                logger.error(f"Write error: {e}")
                return False

    async def shutdown(self) -> None:
        """Shutdown connection."""
        self.is_initialized = False
        self.is_connected = False

        if self._read_task:
            self._read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_task

        if self.serial:
            self.serial.close()
            self.serial = None

        get_event_bus().publish(
            Events.HARDWARE_DISCONNECTED, {"plugin": "arduino_serial"}, source="arduino_serial"
        )

        logger.info("Arduino serial plugin shutdown")

    async def send_motor_command(self, motor_id: int, frequency: float, amplitude: float) -> None:
        """Send motor command (frequency mode)."""
        # Protocol: M{id} F{frequency} A{amplitude}
        # Amplitude is percentage (0-100)
        amp_percent = int(amplitude * 100)
        command = f"M{motor_id} F{frequency:.1f} A{amp_percent}"
        await self._send_command(command)

    async def get_motor_count(self) -> int:
        """Get number of motors."""
        return self.motor_count

    async def ping(self) -> bool:
        """Ping Arduino."""
        if not self.is_connected:
            return False

        # Send ping and wait for response
        success = await self._send_command("PING")
        return success

    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """Set motor angle."""
        # Protocol: A{id} {angle}
        command = f"A{motor_id} {angle:.1f}"
        await self._send_command(command)
