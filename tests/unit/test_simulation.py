"""Tests for the Simulation hardware plugin."""
import pytest

from plugins.hardware.simulation import SimulationPlugin


@pytest.fixture
def simulation():
    """Create a SimulationPlugin instance."""
    return SimulationPlugin()


class TestSimulationHardware:
    """Test SimulationHardware class."""

    def test_plugin_id(self, simulation):
        """Test that plugin has correct ID."""
        assert simulation.plugin_id == "simulation"

    def test_is_available(self, simulation):
        """Test that simulation is always available."""
        available, reason = simulation.check_available()
        assert available is True

    @pytest.mark.asyncio
    async def test_send_command(self, simulation):
        """Test sending a command to simulation."""
        await simulation.initialize({})
        await simulation.send_motor_command(0, 440.0, 0.5)
        state = simulation.get_motor_state()
        assert state["is_initialized"] is True

    @pytest.mark.asyncio
    async def test_ping(self, simulation):
        """Test that ping returns True after initialization."""
        await simulation.initialize({})
        result = await simulation.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_status(self, simulation):
        """Test getting simulation status."""
        await simulation.initialize({})
        status = simulation.get_motor_state()
        assert isinstance(status, dict)
        assert "motor_count" in status

    @pytest.mark.asyncio
    async def test_shutdown(self, simulation):
        """Test clean shutdown."""
        await simulation.initialize({})
        await simulation.shutdown()

    def test_config_schema(self, simulation):
        """Test that config schema is defined."""
        schema = simulation.get_config_schema()
        assert isinstance(schema, dict)
