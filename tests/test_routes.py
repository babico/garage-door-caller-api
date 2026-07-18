import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.models import PhoneConfig, AdbDevice
from app.config import Settings, PhoneConfigLoader


SAMPLE_CFG = PhoneConfig(
    manufacturer="HUAWEI",
    screen={"width": 1080, "height": 2340},
    keypad_tap={"x": 228, "y": 1937},
)


@pytest.fixture
def mock_settings():
    s = MagicMock(spec=Settings)
    s.PHONE_NUMBER = "5551234"
    s.DOOR_CODE = "4"
    s.PHONE_SERIAL = "qwerty123456qwerty123456"
    s.CONFIG_PATH = "config/phones.yaml"
    s.ADB_PATH = "adb"
    s.WAIT_AFTER_DIAL_S = 0
    s.ADB_DEVICE = "auto"
    return s


@pytest.fixture
def mock_loader():
    loader = MagicMock(spec=PhoneConfigLoader)
    loader.get.return_value = SAMPLE_CFG
    loader.list_serials.return_value = ["qwerty123456qwerty123456"]
    return loader


@pytest.fixture
def mock_adb():
    adb = MagicMock()
    adb.get_devices.return_value = {"HVY": "device"}
    adb.detect_model.return_value = "SNE-LX1"
    return adb


def _make_app(mock_settings, mock_loader, mock_adb):
    app = FastAPI()
    app.state.settings = mock_settings
    app.state.phone_config_loader = mock_loader
    app.state.adb_service = mock_adb
    from app.routes import health, call
    app.include_router(health.router)
    app.include_router(call.router)
    return app


class TestHealthEndpoint:
    def test_health_ok(self, mock_settings, mock_loader, mock_adb):
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["adb"]["available"] is True
        assert data["config"]["phone_serial"] == "qwerty123456qwerty123456"

    def test_health_no_device(self, mock_settings, mock_loader, mock_adb):
        mock_adb.get_devices.return_value = {}
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"

    def test_health_adb_unavailable(self, mock_settings, mock_loader, mock_adb):
        from app.adb_service import ADBNotFoundError
        mock_adb.ensure_daemon.side_effect = ADBNotFoundError("not found")
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert data["adb"]["available"] is False

    def test_health_unknown_model(self, mock_settings, mock_loader, mock_adb):
        mock_loader.get.return_value = None
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["config"]["config_loaded"] is False


class TestCallEndpoint:
    def test_call_success(self, mock_settings, mock_loader, mock_adb):
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.post("/call")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["door_code"] == "4"

    def test_call_device_not_found(self, mock_settings, mock_loader, mock_adb):
        from app.adb_service import DeviceNotFoundError
        mock_adb.execute_workflow.side_effect = DeviceNotFoundError("no device")
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.post("/call")
        assert resp.status_code == 503
        data = resp.json()
        assert data["error"] == "DEVICE_NOT_FOUND"

    def test_call_device_unauthorized(self, mock_settings, mock_loader, mock_adb):
        from app.adb_service import DeviceUnauthorizedError
        mock_adb.execute_workflow.side_effect = DeviceUnauthorizedError("unauthorized")
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.post("/call")
        assert resp.status_code == 503
        data = resp.json()
        assert data["error"] == "DEVICE_UNAUTHORIZED"

    def test_call_unknown_phone_serial(self, mock_settings, mock_loader, mock_adb):
        mock_loader.get.return_value = None
        app = _make_app(mock_settings, mock_loader, mock_adb)
        client = TestClient(app)
        resp = client.post("/call")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "PHONE_SERIAL_UNKNOWN"
