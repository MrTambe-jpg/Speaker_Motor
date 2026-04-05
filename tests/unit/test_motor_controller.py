"""Tests for the MotorController class."""
import pytest

from core.motor_controller import MotorController, MotorState


@pytest.fixture
def controller():
    """Create a MotorController with default config."""
    return MotorController()


class TestMotorState:
    """Test MotorState dataclass."""

    def test_default_values(self):
        """Test MotorState default values."""
        state = MotorState(id=0, name="Test", enabled=True, mode="off")

        assert state.angle == 90.0
        assert state.frequency == 0.0
        assert state.amplitude == 0.0
        assert state.target_angle == 90.0


class TestMotorController:
    """Test MotorController class."""

    def test_default_motors(self, controller):
        """Test that controller has default motors."""
        states = controller.get_all_states()
        assert isinstance(states, list)
        assert len(states) > 0

    def test_get_motor_state(self, controller):
        """Test getting a specific motor state."""
        state = controller.get_motor_state(0)
        assert state is not None
        assert state.id == 0

    def test_get_nonexistent_motor(self, controller):
        """Test getting a motor that doesn't exist."""
        state = controller.get_motor_state(999)
        assert state is None

    @pytest.mark.asyncio
    async def test_start_stop(self, controller):
        """Test starting and stopping the controller."""
        await controller.start()
        assert controller.is_running
        await controller.stop()
        assert not controller.is_running

    @pytest.mark.asyncio
    async def test_set_motor_angle(self, controller):
        """Test setting a motor angle."""
        await controller.set_motor_angle(0, 45.0)
        state = controller.get_motor_state(0)
        assert state is not None

    @pytest.mark.asyncio
    async def test_set_motor_angle_out_of_range(self, controller):
        """Test setting a motor angle out of range."""
        await controller.set_motor_angle(0, -10.0)
        state = controller.get_motor_state(0)
        assert state.angle >= 0.0

        await controller.set_motor_angle(0, 200.0)
        state = controller.get_motor_state(0)
        assert state.angle <= 180.0

    @pytest.mark.asyncio
    async def test_set_hardware_plugin(self, controller):
        """Test setting the hardware plugin."""
        mock_hardware = MockHardware()
        controller.set_hardware_plugin(mock_hardware)
        assert controller.hardware_plugin == mock_hardware

    @pytest.mark.asyncio
    async def test_get_all_states(self, controller):
        """Test getting all motor states."""
        states = controller.get_all_states()
        assert isinstance(states, list)
        for state in states:
            assert "id" in state
            assert "name" in state
            assert "angle" in state

    def test_get_motor_config(self, controller):
        """Test getting motor configuration."""
        configs = controller.config.get("motors.mapping", [])
        assert isinstance(configs, list)
        assert len(configs) > 0


class MockHardware:
    """Mock hardware plugin for testing."""

    def __init__(self):
        self.plugin_id = "mock_hardware"
        self.is_available = True

    async def send_command(self, command):
        pass

    async def ping(self):
        return True
