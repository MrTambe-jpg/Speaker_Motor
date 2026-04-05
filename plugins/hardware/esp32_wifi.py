"""
ESP32 WiFi Plugin - Connect to ESP32 via WiFi/WebSocket
"""

import asyncio
import json
import logging
import socket
import time
from typing import Any, Optional

try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

try:
    from zeroconf import ServiceBrowser, Zeroconf

    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

import contextlib

from core.event_bus import Events, get_event_bus
from core.plugin_registry import HardwarePlugin

logger = logging.getLogger(__name__)


class ESP32WiFiPlugin(HardwarePlugin):
    """
    Connect to ESP32 motor controller via WiFi using WebSocket.

    Features:
    - WebSocket connection to ESP32
    - mDNS discovery (omnisound.local)
    - Auto-reconnect on disconnect
    - Low-latency motor commands
    """

    plugin_id = "esp32_wifi"
    display_name = "ESP32 WiFi"
    description = "Connect to ESP32 motor controller via WiFi/WebSocket"
    version = "1.0.0"
    author = "OMNISOUND Team"

    requires_os = ["any"]
    requires_pip = ["websockets"]
    requires_system = []

    config_schema = {
        "type": "object",
        "properties": {
            "ip": {
                "type": "string",
                "default": "192.168.1.100",
                "title": "IP Address",
                "description": "ESP32 IP address (or use mDNS)",
            },
            "port": {
                "type": "integer",
                "default": 81,
                "title": "Port",
                "description": "WebSocket port on ESP32",
            },
            "use_mdns": {
                "type": "boolean",
                "default": True,
                "title": "Use mDNS Discovery",
                "description": "Auto-discover ESP32 via mDNS (omnisound.local)",
            },
            "mdns_name": {
                "type": "string",
                "default": "omnisound.local",
                "title": "mDNS Name",
                "description": "mDNS hostname for discovery",
            },
            "reconnect_interval_ms": {
                "type": "integer",
                "default": 3000,
                "title": "Reconnect Interval (ms)",
                "description": "Time between reconnection attempts",
            },
            "command_timeout_ms": {
                "type": "integer",
                "default": 1000,
                "title": "Command Timeout (ms)",
                "description": "Timeout for motor commands",
            },
        },
    }

    def __init__(self):
        self.ip = "192.168.1.100"
        self.port = 81
        self.use_mdns = True
        self.mdns_name = "omnisound.local"
        self.reconnect_interval_ms = 3000
        self.command_timeout_ms = 1000

        self.websocket = None
        self.is_connected = False
        self.is_initialized = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self.motor_count = 4
        self._last_ping_time = 0.0
        self._latency_ms = 0.0

    def check_available(self) -> tuple[bool, str]:
        """Check if plugin can run."""
        if not HAS_WEBSOCKETS:
            return False, "websockets library not installed. Run: pip install websockets"
        return True, ""

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize ESP32 connection."""
        self.ip = config.get("ip", "192.168.1.100")
        self.port = config.get("port", 81)
        self.use_mdns = config.get("use_mdns", True)
        self.mdns_name = config.get("mdns_name", "omnisound.local")
        self.reconnect_interval_ms = config.get("reconnect_interval_ms", 3000)
        self.command_timeout_ms = config.get("command_timeout_ms", 1000)

        # Resolve mDNS if enabled
        if self.use_mdns:
            resolved_ip = await self._resolve_mdns()
            if resolved_ip:
                self.ip = resolved_ip
                logger.info(f"Resolved mDNS {self.mdns_name} to {self.ip}")

        # Start connection
        self.is_initialized = True
        self._reconnect_task = asyncio.create_task(self._connection_loop())

        logger.info(f"ESP32 WiFi plugin initialized (target: {self.ip}:{self.port})")

    async def _resolve_mdns(self) -> Optional[str]:
        """Resolve mDNS hostname to IP address."""
        if not HAS_ZEROCONF:
            logger.warning("zeroconf not installed, skipping mDNS resolution")
            return None

        try:
            # Try to resolve hostname
            import socket

            hostname = self.mdns_name.rstrip(".local")
            addr_info = socket.getaddrinfo(f"{hostname}.local", self.port)
            if addr_info:
                return addr_info[0][4][0]
        except Exception as e:
            logger.warning(f"Failed to resolve mDNS: {e}")

        return None

    async def _connection_loop(self) -> None:
        """Maintain connection to ESP32."""
        while self.is_initialized:
            try:
                if not self.is_connected:
                    await self._connect()

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.is_connected = False
                await asyncio.sleep(self.reconnect_interval_ms / 1000.0)

    async def _connect(self) -> None:
        """Connect to ESP32 WebSocket."""
        try:
            uri = f"ws://{self.ip}:{self.port}/ws"
            logger.info(f"Connecting to ESP32 at {uri}...")

            self.websocket = await asyncio.wait_for(websockets.connect(uri), timeout=5.0)

            self.is_connected = True
            logger.info(f"Connected to ESP32 at {self.ip}:{self.port}")

            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Request motor count
            await self._send_command({"cmd": "get_config"})

            get_event_bus().publish(
                Events.HARDWARE_CONNECTED,
                {"plugin": "esp32_wifi", "ip": self.ip, "port": self.port},
                source="esp32_wifi",
            )

        except asyncio.TimeoutError:
            logger.warning(f"Connection timeout to {self.ip}:{self.port}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.is_connected = False

    async def _receive_loop(self) -> None:
        """Receive messages from ESP32."""
        while self.is_connected and self.websocket:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)

                # Parse message
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from ESP32: {message}")

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await self._send_command({"cmd": "ping"})
            except websockets.ConnectionClosed:
                logger.warning("ESP32 connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle message from ESP32."""
        msg_type = data.get("type", "unknown")

        if msg_type == "status":
            self.motor_count = data.get("motor_count", 4)

        elif msg_type == "motor_state":
            # Broadcast motor state
            get_event_bus().publish(
                Events.MOTOR_STATE, {"motors": data.get("motors", [])}, source="esp32_wifi"
            )

        elif msg_type == "pong":
            # Calculate latency
            self._latency_ms = (time.time() - self._last_ping_time) * 1000

        elif msg_type == "config":
            self.motor_count = data.get("motor_count", 4)

        elif msg_type == "error":
            logger.error(f"ESP32 error: {data.get('message', 'Unknown error')}")

    async def _send_command(self, command: dict[str, Any]) -> bool:
        """Send command to ESP32."""
        if not self.is_connected or not self.websocket:
            return False

        try:
            message = json.dumps(command)
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown connection."""
        self.is_initialized = False
        self.is_connected = False

        if self._receive_task:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task

        if self._reconnect_task:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task

        if self.websocket:
            await self.websocket.close()

        get_event_bus().publish(
            Events.HARDWARE_DISCONNECTED, {"plugin": "esp32_wifi"}, source="esp32_wifi"
        )

        logger.info("ESP32 WiFi plugin shutdown")

    async def send_motor_command(self, motor_id: int, frequency: float, amplitude: float) -> None:
        """Send motor command."""
        command = {"m": motor_id, "f": round(frequency, 2), "a": round(amplitude, 4)}
        await self._send_command(command)

    async def get_motor_count(self) -> int:
        """Get number of motors."""
        return self.motor_count

    async def ping(self) -> bool:
        """Ping ESP32."""
        if not self.is_connected:
            return False

        self._last_ping_time = time.time()
        success = await self._send_command({"cmd": "ping"})
        return success

    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """Set motor angle."""
        # ESP32 expects angle in degrees (0-180)
        command = {"cmd": "set_angle", "m": motor_id, "a": round(angle, 2)}
        await self._send_command(command)

    @staticmethod
    async def scan_network() -> list[str]:
        """Scan network for ESP32 devices using mDNS."""
        if not HAS_ZEROCONF:
            return []

        found_devices = []

        def on_change(zeroconf, service_type, name, state_change):
            if "omnisound" in name.lower():
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                    found_devices.extend(addresses)

        try:
            zeroconf = Zeroconf()
            ServiceBrowser(zeroconf, "_http._tcp.local.", handlers=[on_change])
            await asyncio.sleep(5)  # Wait for discovery
            zeroconf.close()
        except Exception as e:
            logger.error(f"mDNS scan error: {e}")

        return found_devices
