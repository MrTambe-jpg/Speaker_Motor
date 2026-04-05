"""
Plugin Registry - Dynamic plugin loader for OMNISOUND
"""

import importlib
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins in the system."""

    HARDWARE = "hardware"
    AUDIO_SOURCE = "audio_source"
    PROCESSOR = "processor"
    VISUALIZER = "visualizer"


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""

    plugin_id: str
    plugin_type: PluginType
    display_name: str
    description: str
    version: str
    author: str
    requires_os: list[str]
    requires_pip: list[str]
    requires_system: list[str]
    config_schema: dict[str, Any]
    is_available: bool = False
    unavailable_reason: str = ""
    plugin_instance: Optional["OmniPlugin"] = None


class OmniPlugin(ABC):
    """
    Base class for all OMNISOUND plugins.

    Every plugin must implement this interface. The registry loads
    plugins dynamically and calls check_available() to determine
    if they can run on the current system.
    """

    # Plugin metadata - override in subclass
    plugin_type: PluginType = PluginType.HARDWARE
    plugin_id: str = "base_plugin"
    display_name: str = "Base Plugin"
    description: str = "Base plugin class"
    version: str = "1.0.0"
    author: str = "Unknown"

    # System requirements
    requires_os: list[str] = field(default_factory=lambda: ["any"])
    requires_pip: list[str] = field(default_factory=list)
    requires_system: list[str] = field(default_factory=list)

    # Configuration schema - JSON Schema format for GUI auto-generation
    config_schema: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def check_available(self) -> tuple[bool, str]:
        """
        Check if this plugin can run on the current system.

        Returns:
            Tuple of (is_available: bool, reason_if_not: str)
            If available, return (True, "")
            If not available, return (False, "reason why not")
        """
        pass

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize the plugin with the given configuration.

        Args:
            config: Plugin configuration dictionary
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up and shut down the plugin."""
        pass

    def get_config_schema(self) -> dict[str, Any]:
        """Return the JSON Schema for this plugin's configuration."""
        return self.config_schema

    def get_info(self) -> PluginInfo:
        """Return plugin information."""
        return PluginInfo(
            plugin_id=self.plugin_id,
            plugin_type=self.plugin_type,
            display_name=self.display_name,
            description=self.description,
            version=self.version,
            author=self.author,
            requires_os=self.requires_os,
            requires_pip=self.requires_pip,
            requires_system=self.requires_system,
            config_schema=self.config_schema,
        )


class HardwarePlugin(OmniPlugin):
    """Base class for hardware plugins."""

    plugin_type: PluginType = PluginType.HARDWARE

    @abstractmethod
    async def send_motor_command(self, motor_id: int, frequency: float, amplitude: float) -> None:
        """
        Send a command to a motor.

        Args:
            motor_id: Motor ID (0-indexed)
            frequency: Frequency in Hz (or angle for some modes)
            amplitude: Amplitude 0.0-1.0
        """
        pass

    @abstractmethod
    async def get_motor_count(self) -> int:
        """
        Get the number of motors connected.

        Returns:
            Number of motors
        """
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """
        Ping the hardware to check connectivity.

        Returns:
            True if hardware responds, False otherwise
        """
        pass

    @abstractmethod
    async def set_motor_angle(self, motor_id: int, angle: float) -> None:
        """
        Set a motor to a specific angle.

        Args:
            motor_id: Motor ID (0-indexed)
            angle: Angle in degrees (0-180)
        """
        pass


class AudioSourcePlugin(OmniPlugin):
    """Base class for audio source plugins."""

    plugin_type: PluginType = PluginType.AUDIO_SOURCE

    @abstractmethod
    async def start_stream(self) -> Any:
        """
        Start streaming audio.

        Returns:
            Async generator yielding numpy arrays of audio samples
        """
        pass

    @abstractmethod
    async def stop_stream(self) -> None:
        """Stop streaming audio."""
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """
        Get the sample rate of the audio stream.

        Returns:
            Sample rate in Hz
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the current audio.

        Returns:
            Dictionary with track name, artist, album art URL, etc.
        """
        pass

    @abstractmethod
    async def get_audio_chunk(self) -> Optional[Any]:
        """
        Get the next audio chunk.

        Returns:
            Numpy array of audio samples, or None if stream ended
        """
        pass


class ProcessorPlugin(OmniPlugin):
    """Base class for audio processor plugins."""

    plugin_type: PluginType = PluginType.PROCESSOR

    @abstractmethod
    async def process(self, audio_data: Any) -> dict[str, Any]:
        """
        Process audio data and return results.

        Args:
            audio_data: Numpy array of audio samples

        Returns:
            Dictionary of processed results
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the processor state."""
        pass


class VisualizerPlugin(OmniPlugin):
    """Base class for visualizer plugins."""

    plugin_type: PluginType = PluginType.VISUALIZER

    @abstractmethod
    def render(self, data: dict[str, Any]) -> Any:
        """
        Render visualization data.

        Args:
            data: Data to visualize

        Returns:
            Visualization output (format depends on implementation)
        """
        pass


class PluginRegistry:
    """
    Dynamic plugin registry.

    - Scans plugins/ directory for all Python files
    - Imports and registers all plugin classes
    - Calls check_available() to determine availability
    - Returns plugin lists to GUI
    - Auto-installs missing dependencies (with permission)
    """

    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = plugins_dir or self._get_default_plugins_dir()
        self.plugins: dict[str, PluginInfo] = {}
        self.plugins_by_type: dict[PluginType, list[str]] = {
            PluginType.HARDWARE: [],
            PluginType.AUDIO_SOURCE: [],
            PluginType.PROCESSOR: [],
            PluginType.VISUALIZER: [],
        }
        self.active_hardware: Optional[HardwarePlugin] = None
        self.active_audio_source: Optional[AudioSourcePlugin] = None
        self.active_processors: list[ProcessorPlugin] = []
        self.active_visualizers: list[VisualizerPlugin] = []

    def _get_default_plugins_dir(self) -> str:
        """Get the default plugins directory."""
        return os.path.join(os.path.dirname(__file__), "..", "plugins")

    def discover_plugins(self) -> dict[str, PluginInfo]:
        """
        Discover all plugins in the plugins directory.

        Returns:
            Dictionary mapping plugin_id to PluginInfo
        """
        logger.info(f"Scanning for plugins in: {self.plugins_dir}")

        # Scan each plugin type subdirectory
        plugin_subdirs = {
            PluginType.HARDWARE: "hardware",
            PluginType.AUDIO_SOURCE: "audio_sources",
            PluginType.PROCESSOR: "processors",
            PluginType.VISUALIZER: "visualizers",
        }

        for plugin_type, subdir in plugin_subdirs.items():
            subdir_path = os.path.join(self.plugins_dir, subdir)
            if not os.path.exists(subdir_path):
                logger.warning(f"Plugin directory not found: {subdir_path}")
                continue

            # Scan for Python files
            for filename in os.listdir(subdir_path):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = filename[:-3]  # Remove .py
                    module_path = f"plugins.{subdir}.{module_name}"

                    try:
                        # Import the module
                        if module_path not in sys.modules:
                            spec = importlib.util.spec_from_file_location(
                                module_path, os.path.join(subdir_path, filename)
                            )
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                sys.modules[module_path] = module
                                spec.loader.exec_module(module)
                        else:
                            module = sys.modules[module_path]

                        # Find all plugin classes in the module
                        for _name, obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, OmniPlugin)
                                and obj != OmniPlugin
                                and obj != HardwarePlugin
                                and obj != AudioSourcePlugin
                                and obj != ProcessorPlugin
                                and obj != VisualizerPlugin
                            ):

                                # Instantiate and register
                                plugin_instance = obj()
                                plugin_info = plugin_instance.get_info()

                                # Check availability
                                available, reason = plugin_instance.check_available()
                                plugin_info.is_available = available
                                plugin_info.unavailable_reason = reason
                                plugin_info.plugin_instance = plugin_instance

                                self.plugins[plugin_info.plugin_id] = plugin_info
                                self.plugins_by_type[plugin_type].append(plugin_info.plugin_id)

                                status = "available" if available else f"unavailable ({reason})"
                                logger.info(
                                    f"Discovered plugin: {plugin_info.plugin_id} ({status})"
                                )

                    except Exception as e:
                        logger.error(f"Error loading plugin {filename}: {e}")

        return self.plugins

    def get_plugin(self, plugin_id: str) -> Optional[OmniPlugin]:
        """
        Get a plugin instance by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin instance or None if not found
        """
        info = self.plugins.get(plugin_id)
        return info.plugin_instance if info else None

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[PluginInfo]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugin

        Returns:
            List of PluginInfo objects
        """
        return [
            self.plugins[pid]
            for pid in self.plugins_by_type.get(plugin_type, [])
            if pid in self.plugins
        ]

    def get_available_plugins(self, plugin_type: PluginType) -> list[PluginInfo]:
        """
        Get all available plugins of a specific type.

        Args:
            plugin_type: Type of plugin

        Returns:
            List of available PluginInfo objects
        """
        return [info for info in self.get_plugins_by_type(plugin_type) if info.is_available]

    def get_unavailable_plugins(self, plugin_type: PluginType) -> list[PluginInfo]:
        """
        Get all unavailable plugins of a specific type with reasons.

        Args:
            plugin_type: Type of plugin

        Returns:
            List of unavailable PluginInfo objects
        """
        return [info for info in self.get_plugins_by_type(plugin_type) if not info.is_available]

    async def initialize_plugin(self, plugin_id: str, config: dict[str, Any]) -> bool:
        """
        Initialize a plugin with configuration.

        Args:
            plugin_id: Plugin ID
            config: Plugin configuration

        Returns:
            True if successful, False otherwise
        """
        info = self.plugins.get(plugin_id)
        if not info or not info.plugin_instance:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        if not info.is_available:
            logger.error(f"Plugin not available: {plugin_id} - {info.unavailable_reason}")
            return False

        try:
            await info.plugin_instance.initialize(config)
            logger.info(f"Initialized plugin: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_id}: {e}")
            return False

    async def shutdown_plugin(self, plugin_id: str) -> bool:
        """
        Shut down a plugin.

        Args:
            plugin_id: Plugin ID

        Returns:
            True if successful, False otherwise
        """
        info = self.plugins.get(plugin_id)
        if not info or not info.plugin_instance:
            return False

        try:
            await info.plugin_instance.shutdown()
            logger.info(f"Shut down plugin: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_id}: {e}")
            return False

    def get_plugin_config_schema(self, plugin_id: str) -> dict[str, Any]:
        """
        Get the configuration schema for a plugin.

        Args:
            plugin_id: Plugin ID

        Returns:
            JSON Schema dictionary
        """
        info = self.plugins.get(plugin_id)
        return info.config_schema if info else {}

    def get_all_plugins_info(self) -> dict[str, list[dict[str, Any]]]:
        """
        Get information about all plugins for the GUI.

        Returns:
            Dictionary with plugin lists by type
        """
        result = {}
        for plugin_type in PluginType:
            plugins = []
            for plugin_id in self.plugins_by_type.get(plugin_type, []):
                info = self.plugins.get(plugin_id)
                if info:
                    plugins.append(
                        {
                            "id": info.plugin_id,
                            "type": info.plugin_type.value,
                            "name": info.display_name,
                            "description": info.description,
                            "version": info.version,
                            "author": info.author,
                            "available": info.is_available,
                            "unavailable_reason": info.unavailable_reason,
                            "requires_os": info.requires_os,
                            "requires_pip": info.requires_pip,
                            "requires_system": info.requires_system,
                            "config_schema": info.config_schema,
                        }
                    )
            result[plugin_type.value] = plugins
        return result

    async def set_active_hardware(self, plugin_id: str, config: dict[str, Any]) -> bool:
        """
        Set the active hardware plugin.

        Args:
            plugin_id: Plugin ID
            config: Plugin configuration

        Returns:
            True if successful
        """
        # Shutdown existing hardware plugin
        if self.active_hardware:
            await self.active_hardware.shutdown()
            self.active_hardware = None

        # Initialize new plugin
        if await self.initialize_plugin(plugin_id, config):
            plugin = self.get_plugin(plugin_id)
            if isinstance(plugin, HardwarePlugin):
                self.active_hardware = plugin
                return True
        return False

    async def set_active_audio_source(self, plugin_id: str, config: dict[str, Any]) -> bool:
        """
        Set the active audio source plugin.

        Args:
            plugin_id: Plugin ID
            config: Plugin configuration

        Returns:
            True if successful
        """
        # Shutdown existing audio source
        if self.active_audio_source:
            await self.active_audio_source.stop_stream()
            await self.active_audio_source.shutdown()
            self.active_audio_source = None

        # Initialize new plugin
        if await self.initialize_plugin(plugin_id, config):
            plugin = self.get_plugin(plugin_id)
            if isinstance(plugin, AudioSourcePlugin):
                self.active_audio_source = plugin
                return True
        return False


# Global singleton instance
_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry(plugins_dir: Optional[str] = None) -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry(plugins_dir)
    return _plugin_registry


def reset_plugin_registry(plugins_dir: Optional[str] = None) -> PluginRegistry:
    """Reset the global plugin registry (useful for testing)."""
    global _plugin_registry
    _plugin_registry = PluginRegistry(plugins_dir)
    return _plugin_registry
