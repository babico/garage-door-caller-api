import os
import pytest
from app.config import Settings, PhoneConfigLoader


class TestSettings:
    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("PHONE_NUMBER", "5551234")
        monkeypatch.setenv("DOOR_CODE", "4")
        monkeypatch.setenv("PHONE_SERIAL", "qwerty123456qwerty123456")
        s = Settings()
        assert s.PHONE_NUMBER == "5551234"
        assert s.DOOR_CODE == "4"
        assert s.PHONE_SERIAL == "qwerty123456qwerty123456"
        assert s.CONFIG_PATH == "config/phones.yaml"
        assert s.ADB_PATH == "adb"

    def test_missing_phone_number_raises(self, monkeypatch):
        monkeypatch.setenv("DOOR_CODE", "4")
        monkeypatch.setenv("PHONE_SERIAL", "qwerty123456qwerty123456")
        monkeypatch.delenv("PHONE_NUMBER", raising=False)
        with pytest.raises(ValueError, match="PHONE_NUMBER"):
            Settings()

    def test_missing_door_code_raises(self, monkeypatch):
        monkeypatch.setenv("PHONE_NUMBER", "5551234")
        monkeypatch.setenv("PHONE_SERIAL", "qwerty123456qwerty123456")
        monkeypatch.delenv("DOOR_CODE", raising=False)
        with pytest.raises(ValueError, match="DOOR_CODE"):
            Settings()

    def test_missing_phone_serial_raises(self, monkeypatch):
        monkeypatch.setenv("PHONE_NUMBER", "5551234")
        monkeypatch.setenv("DOOR_CODE", "4")
        monkeypatch.delenv("PHONE_SERIAL", raising=False)
        with pytest.raises(ValueError, match="PHONE_SERIAL"):
            Settings()

    def test_custom_adb_path(self, monkeypatch):
        monkeypatch.setenv("PHONE_NUMBER", "5551234")
        monkeypatch.setenv("DOOR_CODE", "4")
        monkeypatch.setenv("PHONE_SERIAL", "qwerty123456qwerty123456")
        monkeypatch.setenv("ADB_PATH", "/custom/adb")
        s = Settings()
        assert s.ADB_PATH == "/custom/adb"


class TestPhoneConfigLoader:
    def test_load_known_serial(self, phones_yaml_path):
        loader = PhoneConfigLoader(phones_yaml_path)
        cfg = loader.get("qwerty123456qwerty123456")
        assert cfg is not None
        assert cfg.manufacturer == "HUAWEI"
        assert cfg.keypad_tap["x"] == 228

    def test_unknown_serial_returns_none(self, phones_yaml_path):
        loader = PhoneConfigLoader(phones_yaml_path)
        cfg = loader.get("NONEXISTENT")
        assert cfg is None

    def test_all_serials_loaded(self, phones_yaml_path):
        loader = PhoneConfigLoader(phones_yaml_path)
        serials = loader.list_serials()
        assert "qwerty123456qwerty123456" in serials
        assert "R58M42AXXXXX" in serials
        assert len(serials) == 2

    def test_invalid_yaml_path_raises(self):
        with pytest.raises(FileNotFoundError):
            PhoneConfigLoader("/nonexistent/path.yaml")

    def test_empty_yaml_returns_no_serials(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("serials: {}\n")
        loader = PhoneConfigLoader(str(empty))
        assert loader.list_serials() == []

    def test_missing_serials_key_returns_no_serials(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("other_key: value\n")
        loader = PhoneConfigLoader(str(bad))
        assert loader.list_serials() == []
