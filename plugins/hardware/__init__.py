# Hardware Plugins
from .esp32_wifi import ESP32WiFiPlugin
from .simulation import SimulationPlugin

try:
    from .arduino_serial import ArduinoSerialPlugin
except ImportError:
    ArduinoSerialPlugin = None  # type: ignore[misc,assignment]

try:
    from .raspberry_pi_gpio import RaspberryPiGPIOPlugin
except ImportError:
    RaspberryPiGPIOPlugin = None  # type: ignore[misc,assignment]

__all__ = [
    "SimulationPlugin",
    "ESP32WiFiPlugin",
    "ArduinoSerialPlugin",
    "RaspberryPiGPIOPlugin",
]
