"""Tests for the PluginRegistry class."""
import pytest

from core.plugin_registry import PluginRegistry, PluginType


@pytest.fixture
def registry():
    """Create a fresh PluginRegistry instance."""
    return PluginRegistry()


class TestPluginRegistry:
    """Test PluginRegistry class."""

    def test_discover_plugins(self, registry):
        """Test that plugins are discovered."""
        registry.discover_plugins()
        plugins = registry.get_all_plugins_info()
        assert len(plugins) > 0

    def test_get_plugins_by_type(self, registry):
        """Test getting plugins by type."""
        registry.discover_plugins()
        hardware_plugins = registry.get_plugins_by_type(PluginType.HARDWARE)
        assert isinstance(hardware_plugins, list)

    def test_get_available_plugins(self, registry):
        """Test getting available plugins."""
        registry.discover_plugins()
        available = registry.get_available_plugins(PluginType.HARDWARE)
        assert isinstance(available, list)

    def test_simulation_is_available(self, registry):
        """Test that simulation plugin is always available."""
        registry.discover_plugins()
        available = registry.get_available_plugins(PluginType.HARDWARE)
        plugin_ids = [p.plugin_id for p in available]
        assert "simulation" in plugin_ids

    def test_get_plugin_by_id(self, registry):
        """Test getting a plugin by its ID."""
        registry.discover_plugins()
        plugin = registry.get_plugin("simulation")
        assert plugin is not None
        assert plugin.plugin_id == "simulation"

    def test_get_nonexistent_plugin(self, registry):
        """Test getting a plugin that doesn't exist."""
        registry.discover_plugins()
        plugin = registry.get_plugin("nonexistent")
        assert plugin is None


class TestPluginType:
    """Test PluginType enum."""

    def test_plugin_types_exist(self):
        """Test that all expected plugin types exist."""
        assert hasattr(PluginType, "HARDWARE")
        assert hasattr(PluginType, "AUDIO_SOURCE")
        assert hasattr(PluginType, "PROCESSOR")
