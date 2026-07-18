import pytest
from pydantic import ValidationError
from app.models import PhoneConfig, HealthResponse, CallResponse, AdbDevice


class TestPhoneConfig:
    def test_valid_phone_config(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            keypad_tap={"x": 228, "y": 1937},
        )
        assert cfg.manufacturer == "HUAWEI"
        assert cfg.screen["width"] == 1080
        assert cfg.keypad_tap["x"] == 228

    def test_with_wake_and_swipe(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
            keypad_tap={"x": 228, "y": 1937},
        )
        assert cfg.wake_up is True
        assert cfg.swipe_unlock["start_x"] == 540
        assert cfg.swipe_unlock["duration_ms"] == 300

    def test_screen_negative_dimensions_rejected(self):
        with pytest.raises(ValidationError):
            PhoneConfig(
                manufacturer="HUAWEI",
                screen={"width": -1, "height": 2340},
                keypad_tap={"x": 228, "y": 1937},
            )

    def test_phone_pin_defaults_empty(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            keypad_tap={"x": 228, "y": 1937},
        )
        assert cfg.phone_pin == ""

    def test_phone_pin_set(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        assert cfg.phone_pin == "123456"

    def test_manufacturer_empty_rejected(self):
        with pytest.raises(ValidationError):
            PhoneConfig(
                manufacturer="",
                screen={"width": 1080, "height": 2340},
                keypad_tap={"x": 228, "y": 1937},
            )


class TestAdbDevice:
    def test_valid_adb_device(self):
        d = AdbDevice(serial="qwerty123456qwerty123456", state="device", model="SNE-LX1")
        assert d.serial == "qwerty123456qwerty123456"
        assert d.state == "device"
        assert d.model == "SNE-LX1"

    def test_serial_empty_rejected(self):
        with pytest.raises(ValidationError):
            AdbDevice(serial="", state="device", model="SNE-LX1")

    def test_model_optional(self):
        d = AdbDevice(serial="qwerty123456qwerty123456", state="device")
        assert d.model is None


class TestHealthResponse:
    def test_ok_status_valid(self):
        r = HealthResponse(status="ok", adb={"available": True})
        assert r.status == "ok"

    def test_adb_status_empty_allowed(self):
        r = HealthResponse(status="error")
        assert r.status == "error"


class TestCallResponse:
    def test_full_response(self):
        r = CallResponse(
            status="ok",
            phone_number="5551234567",
            door_code="4",
            duration_ms=8234,
        )
        assert r.door_code == "4"
        assert r.duration_ms == 8234

    def test_error_response(self):
        r = CallResponse(
            status="error",
            error="DEVICE_NOT_FOUND",
            message="No ADB device connected",
        )
        assert r.error == "DEVICE_NOT_FOUND"
