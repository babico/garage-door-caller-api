import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_env(monkeypatch):
    monkeypatch.setenv("PHONE_NUMBER", "5551234")
    monkeypatch.setenv("DOOR_CODE", "4")
    monkeypatch.setenv("PHONE_SERIAL", "qwerty123456qwerty123456")
    import importlib
    import app.main
    importlib.reload(app.main)
    return app.main.app


class TestMainApp:
    def test_root_redirects_to_docs(self, app_with_env):
        with TestClient(app_with_env) as client:
            resp = client.get("/", follow_redirects=False)
            assert resp.status_code in (200, 307)
            if resp.status_code == 307:
                assert "/docs" in resp.headers.get("location", "")

    def test_health_endpoint_loaded(self, app_with_env):
        with TestClient(app_with_env) as client:
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_call_endpoint_loaded(self, app_with_env, monkeypatch):
        from app.adb_service import AdbService
        monkeypatch.setattr(AdbService, "get_devices", lambda self: {})
        with TestClient(app_with_env) as client:
            resp = client.post("/call")
            assert resp.status_code == 503

    def test_app_title_and_version(self, app_with_env):
        assert app_with_env.title == "Garage Door Caller API"

    def test_missing_env_raises_on_startup(self, monkeypatch):
        monkeypatch.delenv("PHONE_NUMBER", raising=False)
        monkeypatch.delenv("DOOR_CODE", raising=False)
        monkeypatch.delenv("PHONE_SERIAL", raising=False)
        monkeypatch.setenv("CONFIG_PATH", "nonexistent.yaml")
        with pytest.raises(ValueError, match="PHONE_NUMBER"):
            from app.config import Settings
            Settings()
