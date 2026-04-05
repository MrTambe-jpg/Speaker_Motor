"""
Config Manager - Single source of truth for OMNISOUND configuration
"""

import copy
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from .event_bus import Events, get_event_bus

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "version": "1.0",
    "system": {
        "host": "0.0.0.0",
        "port": 8000,
        "auto_open_browser": True,
        "auto_start": False,
        "theme": "dark",
        "language": "en",
        "log_level": "info",
    },
    "hardware": {
        "active_plugin": "simulation",
        "plugins": {
            "esp32_wifi": {
                "ip": "192.168.1.100",
                "port": 81,
                "use_mdns": True,
                "mdns_name": "omnisound.local",
                "reconnect_interval_ms": 3000,
            },
            "esp32_bluetooth": {"device_name": "OmnisoundESP32", "reconnect_interval_ms": 3000},
            "arduino_serial": {"port": "COM3", "baud_rate": 115200, "auto_detect_port": True},
            "raspberry_pi_gpio": {"pins": [13, 14, 27, 26], "pwm_frequency": 50},
            "raspberry_pi_pwm": {
                "pins": [13, 14, 27, 26],
                "pwm_frequency": 50,
                "use_hardware_pwm": True,
            },
            "teensy_usb": {"port": "auto", "baud_rate": 115200},
            "stm32_serial": {"port": "COM4", "baud_rate": 115200},
            "pico_usb": {"port": "auto", "baud_rate": 115200},
            "simulation": {"motor_count": 4, "response_latency_ms": 5},
            "generic_serial": {
                "port": "COM5",
                "baud_rate": 115200,
                "command_format": "MOTOR:{motor} FREQ:{frequency} AMP:{amplitude}\n",
            },
        },
    },
    "audio": {
        "active_source": "microphone",
        "sample_rate": 44100,
        "chunk_size": 512,
        "plugins": {
            "microphone": {
                "device_index": None,
                "device_name": "Default",
                "channels": 1,
                "gain": 1.0,
            },
            "file_player": {
                "file_path": "",
                "playlist": [],
                "shuffle": False,
                "repeat": False,
                "supported_formats": ["wav", "mp3", "flac", "ogg", "aac", "aiff", "m4a"],
                "last_directory": "",
            },
            "spotify": {
                "client_id": "",
                "redirect_uri": "http://localhost:8000/auth/spotify/callback",
                "scopes": [
                    "user-read-playback-state",
                    "user-modify-playback-state",
                    "user-read-currently-playing",
                ],
                "access_token": "",
                "refresh_token": "",
                "token_expiry": None,
                "capture_mode": "system_loopback",
            },
            "apple_music": {"developer_token": "", "capture_mode": "system_loopback"},
            "youtube": {
                "url": "",
                "quality": "bestaudio",
                "cookies_file": "",
                "cache_directory": "./youtube_cache",
            },
            "soundcloud": {"url": "", "quality": "high"},
            "system_audio": {"loopback_device": None, "loopback_device_name": "Default"},
            "bluetooth_audio": {"device_name": "", "auto_connect": True},
            "airplay": {"service_name": "Omnisound", "port": 7000},
            "rtsp_stream": {"url": "", "buffer_size": 4096},
            "webrtc_audio": {"enabled": False, "stun_server": "stun:stun.l.google.com:19302"},
            "midi_input": {
                "device_name": "",
                "channel": "all",
                "note_range": [21, 108],
                "velocity_to_amplitude": True,
            },
        },
    },
    "motors": {
        "count": 4,
        "mapping": [
            {
                "id": 0,
                "name": "Bass",
                "freq_min_hz": 20,
                "freq_max_hz": 200,
                "angle_min": 45,
                "angle_max": 135,
                "center_angle": 90,
                "enabled": True,
                "invert": False,
                "smoothing": 0.3,
                "mode": "frequency_band",
            },
            {
                "id": 1,
                "name": "Mid",
                "freq_min_hz": 200,
                "freq_max_hz": 800,
                "angle_min": 45,
                "angle_max": 135,
                "center_angle": 90,
                "enabled": True,
                "invert": False,
                "smoothing": 0.3,
                "mode": "frequency_band",
            },
            {
                "id": 2,
                "name": "High",
                "freq_min_hz": 800,
                "freq_max_hz": 8000,
                "angle_min": 45,
                "angle_max": 135,
                "center_angle": 90,
                "enabled": True,
                "invert": False,
                "smoothing": 0.3,
                "mode": "frequency_band",
            },
            {
                "id": 3,
                "name": "Beat",
                "mode": "beat",
                "beat_kick_angle": 135,
                "beat_rest_angle": 90,
                "beat_hold_ms": 80,
                "enabled": True,
                "smoothing": 0.1,
            },
        ],
    },
    "processors": {
        "active": ["fft_analyzer", "beat_detector", "band_splitter"],
        "fft_analyzer": {"window": "hann", "size": 2048, "enabled": True},
        "beat_detector": {"sensitivity": 0.7, "min_bpm": 60, "max_bpm": 200, "enabled": True},
        "band_splitter": {"bands": 4, "scale": "logarithmic", "enabled": True},
        "envelope_follower": {"attack_ms": 10, "release_ms": 100, "enabled": False},
        "pitch_tracker": {"algorithm": "yin", "confidence_threshold": 0.8, "enabled": False},
        "noise_gate": {"threshold_db": -60, "enabled": False},
    },
    "sequences": {"save_directory": "./sequences", "saved": []},
}


class ConfigManager:
    """
    Manages the omnisound_config.json file.

    - Single source of truth for all configuration
    - Validates against schema
    - Broadcasts changes via EventBus
    - Supports dot-notation access: config.get("motors.count")
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.event_bus = get_event_bus()
        self._last_saved = None

        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        # Load existing config or create default
        self.load()

    def _get_default_config_path(self) -> str:
        """Get the default config file path."""
        # Store in project root
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "omnisound_config.json"
        )

    def load(self) -> dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            The loaded configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    loaded_config = json.load(f)

                # Merge with defaults (preserves new keys in defaults)
                self.config = self._merge_configs(copy.deepcopy(DEFAULT_CONFIG), loaded_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config: {e}. Using defaults.")
                self.config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            logger.info("No config file found. Creating default configuration.")
            self.config = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

        return self.config

    def _merge_configs(self, base: dict, override: dict) -> dict:
        """
        Recursively merge two configs, preserving structure.

        Args:
            base: Base configuration (defaults)
            override: Override configuration (loaded)

        Returns:
            Merged configuration
        """
        result = base.copy()
        for key, value in override.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._merge_configs(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def save(self) -> None:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            self._last_saved = datetime.now()
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a config value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "motors.count")
            default: Default value if key not found

        Returns:
            The config value or default
        """
        keys = key_path.split(".")
        value = self.config

        try:
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any, save_immediately: bool = True) -> None:
        """
        Set a config value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "motors.count")
            value: The value to set
            save_immediately: Whether to save to file immediately
        """
        keys = key_path.split(".")
        config = self.config

        # Navigate to parent
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set value
        config[keys[-1]] = value

        # Broadcast change
        self.event_bus.publish(
            Events.CONFIG_CHANGED, {"path": key_path, "value": value}, source="config_manager"
        )

        if save_immediately:
            self.save()

    def get_section(self, section: str) -> dict[str, Any]:
        """
        Get an entire config section.

        Args:
            section: Section name (e.g., "hardware", "audio")

        Returns:
            The section dictionary
        """
        return self.config.get(section, {})

    def set_section(
        self, section: str, value: dict[str, Any], save_immediately: bool = True
    ) -> None:
        """
        Set an entire config section.

        Args:
            section: Section name
            value: The section dictionary
            save_immediately: Whether to save to file immediately
        """
        self.config[section] = value

        self.event_bus.publish(
            Events.CONFIG_CHANGED, {"path": section, "value": value}, source="config_manager"
        )

        if save_immediately:
            self.save()

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.save()
        logger.info("Reset configuration to defaults")

    def export_config(self, path: str) -> None:
        """
        Export configuration to a file.

        Args:
            path: Export file path
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported configuration to {path}")
        except Exception as e:
            logger.error(f"Error exporting config: {e}")
            raise

    def import_config(self, path: str) -> None:
        """
        Import configuration from a file.

        Args:
            path: Import file path
        """
        try:
            with open(path, encoding="utf-8") as f:
                imported = json.load(f)

            self.config = self._merge_configs(copy.deepcopy(DEFAULT_CONFIG), imported)
            self.save()

            self.event_bus.publish(
                Events.CONFIG_CHANGED,
                {"path": "all", "value": self.config},
                source="config_manager",
            )

            logger.info(f"Imported configuration from {path}")
        except Exception as e:
            logger.error(f"Error importing config: {e}")
            raise

    def get_motor_config(self, motor_id: int) -> Optional[dict[str, Any]]:
        """
        Get configuration for a specific motor.

        Args:
            motor_id: Motor ID (0-indexed)

        Returns:
            Motor configuration dictionary or None if not found
        """
        mappings = self.config.get("motors", {}).get("mapping", [])
        for motor in mappings:
            if motor.get("id") == motor_id:
                return motor
        return None

    def set_motor_config(self, motor_id: int, config: dict[str, Any]) -> None:
        """
        Set configuration for a specific motor.

        Args:
            motor_id: Motor ID (0-indexed)
            config: Motor configuration dictionary
        """
        mappings = self.config.get("motors", {}).get("mapping", [])
        for i, motor in enumerate(mappings):
            if motor.get("id") == motor_id:
                mappings[i] = {**motor, **config}
                self.set("motors.mapping", mappings)
                return

        # Motor not found, add it
        config["id"] = motor_id
        mappings.append(config)
        self.set("motors.mapping", mappings)

    def get_active_hardware_plugin(self) -> str:
        """Get the currently active hardware plugin ID."""
        return self.config.get("hardware", {}).get("active_plugin", "simulation")

    def get_active_audio_source(self) -> str:
        """Get the currently active audio source plugin ID."""
        return self.config.get("audio", {}).get("active_source", "microphone")

    def get_plugin_config(self, plugin_type: str, plugin_id: str) -> dict[str, Any]:
        """
        Get configuration for a specific plugin.

        Args:
            plugin_type: "hardware" or "audio" or "processors"
            plugin_id: Plugin ID

        Returns:
            Plugin configuration dictionary
        """
        return self.config.get(plugin_type, {}).get("plugins", {}).get(plugin_id, {})

    def set_plugin_config(self, plugin_type: str, plugin_id: str, config: dict[str, Any]) -> None:
        """
        Set configuration for a specific plugin.

        Args:
            plugin_type: "hardware" or "audio" or "processors"
            plugin_id: Plugin ID
            config: Plugin configuration dictionary
        """
        if plugin_type not in self.config:
            self.config[plugin_type] = {"plugins": {}}
        if "plugins" not in self.config[plugin_type]:
            self.config[plugin_type]["plugins"] = {}

        self.config[plugin_type]["plugins"][plugin_id] = config
        self.save()

    def get_last_saved(self) -> Optional[datetime]:
        """Get the timestamp of the last save."""
        return self._last_saved

    def get_config_file_path(self) -> str:
        """Get the current config file path."""
        return self.config_path

    def to_dict(self) -> dict[str, Any]:
        """Get a copy of the entire configuration."""
        return copy.deepcopy(self.config)


# Global singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def reset_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Reset the global config manager (useful for testing)."""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
