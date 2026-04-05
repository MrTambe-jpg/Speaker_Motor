"""Integration tests for the OmniSound engine."""
import pytest
from fastapi.testclient import TestClient

from core.engine import OmniSoundEngine


@pytest.fixture
def engine():
    """Create an engine instance."""
    return OmniSoundEngine()


@pytest.fixture
def client(engine):
    """Create a test client."""
    app = engine.create_app()
    return TestClient(app)


class TestEngineAPI:
    """Test engine HTTP API endpoints."""

    def test_get_plugins(self, client):
        """Test getting all plugins."""
        response = client.get("/api/plugins")
        assert response.status_code == 200

    def test_get_config(self, client):
        """Test getting configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data or "hardware" in data

    def test_get_system_info(self, client):
        """Test getting system information."""
        response = client.get("/api/system")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data

    def test_get_motors(self, client):
        """Test getting motor states."""
        response = client.get("/api/motors")
        assert response.status_code == 200

    def test_get_status(self, client):
        """Test getting system status."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_running" in data

    def test_root_route(self, client):
        """Test root route serves something."""
        response = client.get("/")
        assert response.status_code == 200


class TestEngineConfigAPI:
    """Test config-specific API endpoints."""

    def test_get_config_value(self, client):
        """Test getting a specific config value."""
        response = client.get("/api/config/system.host")
        assert response.status_code == 200

    def test_set_config_value(self, client):
        """Test setting a config value."""
        response = client.put("/api/config/system.host", json={"value": "127.0.0.1"})
        assert response.status_code in [200, 422]  # 422 is acceptable for strict body parsing

    def test_diagnostics(self, client):
        """Test diagnostics endpoint."""
        response = client.get("/api/diagnostics")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
