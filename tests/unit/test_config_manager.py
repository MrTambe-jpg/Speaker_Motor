"""Tests for the ConfigManager class."""
import json
import os
import tempfile
import pytest

from core.config_manager import ConfigManager


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""
    data = {
        "system": {
            "host": "0.0.0.0",
            "port": 8000,
            "auto_start": False,
            "auto_open_browser": True,
        },
        "hardware": {
            "active_plugin": "simulation",
            "simulation": {
                "motor_count": 4,
                "response_delay_ms": 10,
            },
        },
        "audio": {
            "active_source": "microphone",
            "sample_rate": 44100,
            "chunk_size": 1024,
        },
        "motors": {
            "count": 4,
            "mapping": [
                {
                    "id": 0,
                    "name": "Bass",
                    "enabled": True,
                    "mode": "frequency_band",
                    "freq_min_hz": 20,
                    "freq_max_hz": 200,
                    "angle_min": 45,
                    "angle_max": 135,
                },
                {
                    "id": 1,
                    "name": "Mid",
                    "enabled": True,
                    "mode": "frequency_band",
                    "freq_min_hz": 200,
                    "freq_max_hz": 800,
                    "angle_min": 45,
                    "angle_max": 135,
                },
            ],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def config(temp_config_file):
    """Create a ConfigManager instance."""
    return ConfigManager(config_path=temp_config_file)


class TestConfigManagerGet:
    """Test config value retrieval."""

    def test_get_simple_key(self, config):
        """Test getting a simple key."""
        assert config.get("system.host") == "0.0.0.0"
        assert config.get("system.port") == 8000

    def test_get_nested_key(self, config):
        """Test getting a nested key."""
        assert config.get("hardware.simulation.motor_count") == 4

    def test_get_default_value(self, config):
        """Test getting a key with default value."""
        assert config.get("nonexistent.key", "default") == "default"

    def test_get_returns_none_for_missing(self, config):
        """Test that missing keys return None."""
        assert config.get("nonexistent.key") is None

    def test_get_list(self, config):
        """Test getting a list value."""
        motors = config.get("motors.mapping")
        assert isinstance(motors, list)
        assert len(motors) == 2

    def test_get_motor_by_index(self, config):
        """Test getting a motor config by index."""
        motors = config.get("motors.mapping")
        assert motors[0]["name"] == "Bass"


class TestConfigManagerSet:
    """Test config value setting."""

    def test_set_simple_key(self, config):
        """Test setting a simple key."""
        config.set("system.host", "127.0.0.1")
        assert config.get("system.host") == "127.0.0.1"

    def test_set_nested_key(self, config):
        """Test setting a nested key."""
        config.set("hardware.simulation.motor_count", 8)
        assert config.get("hardware.simulation.motor_count") == 8

    def test_set_creates_missing_keys(self, config):
        """Test that set creates missing intermediate keys."""
        config.set("new.section.value", 42)
        assert config.get("new.section.value") == 42


class TestConfigManagerSave:
    """Test config saving."""

    def test_save_and_reload(self, temp_config_file):
        """Test that saved config can be reloaded."""
        config = ConfigManager(config_path=temp_config_file)
        config.set("system.port", 9000)
        config.save()

        config2 = ConfigManager(config_path=temp_config_file)
        assert config2.get("system.port") == 9000

    def test_save_immediately(self, temp_config_file):
        """Test save_immediately flag."""
        config = ConfigManager(config_path=temp_config_file)
        config.set("system.port", 9000, save_immediately=True)
        assert config.get("system.port") == 9000


class TestConfigManagerDefaults:
    """Test default configuration."""

    def test_default_config_has_system(self):
        """Test that default config has system section."""
        config = ConfigManager()
        assert config.get("system.host") is not None
        assert config.get("system.port") is not None

    def test_default_config_has_hardware(self):
        """Test that default config has hardware section."""
        config = ConfigManager()
        assert config.get("hardware.active_plugin") is not None

    def test_default_config_has_motors(self):
        """Test that default config has motor definitions."""
        config = ConfigManager()
        motors = config.get("motors.mapping")
        assert isinstance(motors, list)
        assert len(motors) > 0


class TestConfigManagerExport:
    """Test config export/import."""

    def test_export_config(self, config):
        """Test exporting config to file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.export_config(path)
            with open(path) as f:
                data = json.load(f)
            assert "system" in data
            assert "hardware" in data
        finally:
            os.unlink(path)

    def test_import_config(self, config):
        """Test importing config from file."""
        new_data = {"system": {"host": "1.2.3.4", "port": 9999}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(new_data, f)
            path = f.name
        try:
            config.import_config(path)
            assert config.get("system.host") == "1.2.3.4"
            assert config.get("system.port") == 9999
        finally:
            os.unlink(path)


class TestConfigManagerReset:
    """Test config reset."""

    def test_reset_to_defaults(self, config):
        """Test resetting to defaults."""
        config.set("system.host", "changed")
        config.reset_to_defaults()
        defaults = ConfigManager()
        assert config.get("system.host") == defaults.get("system.host")
