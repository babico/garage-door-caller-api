import pytest
import subprocess
from unittest.mock import patch, MagicMock
from app.adb_service import (
    AdbService,
    ADBNotFoundError,
    DeviceNotFoundError,
    DeviceUnauthorizedError,
    CallFailedError,
)
from app.models import PhoneConfig


PHONE_CFG = PhoneConfig(
    manufacturer="HUAWEI",
    screen={"width": 1080, "height": 2340},
    wake_up=True,
    swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
    keypad_tap={"x": 228, "y": 1937},
)


PHONE_CFG_NO_PREP = PhoneConfig(
    manufacturer="HUAWEI",
    screen={"width": 1080, "height": 2340},
    wake_up=False,
    keypad_tap={"x": 228, "y": 1937},
)


def _mock_run(returncode=0, stdout=b"", stderr=b""):
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestGetDevices:
    def test_single_device(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b"List of devices attached\nqwerty123456qwerty123456\tdevice\n"
            )
            devices = svc.get_devices()
            assert devices == {"qwerty123456qwerty123456": "device"}
            mock.assert_called_once_with(["adb", "devices"])

    def test_multiple_devices(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b"List of devices attached\nA\tdevice\nB\tunauthorized\nC\tdevice\n"
            )
            devices = svc.get_devices()
            assert devices == {"A": "device", "B": "unauthorized", "C": "device"}

    def test_no_devices(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b"List of devices attached\n\n"
            )
            devices = svc.get_devices()
            assert devices == {}

    def test_unauthorized_only(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b"List of devices attached\nHVY\tunauthorized\n"
            )
            devices = svc.get_devices()
            assert devices == {"HVY": "unauthorized"}


class TestEnsureDaemon:
    def test_daemon_starts_successfully(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(stdout=b"* daemon started successfully *")
            result = svc.ensure_daemon()
            assert result is True

    def test_adb_not_found_raises(self):
        svc = AdbService(adb_path="/nonexistent/adb")
        with patch.object(svc, "_run") as mock:
            mock.side_effect = ADBNotFoundError("adb not found")
            with pytest.raises(ADBNotFoundError):
                svc.ensure_daemon()


class TestDetectModel:
    def test_model_detected(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(stdout=b"SNE-LX1\n")
            model = svc.detect_model("HVY")
            assert model == "SNE-LX1"

    def test_model_strips_newlines(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(stdout=b"  SNE-LX1  \n")
            model = svc.detect_model("HVY")
            assert model == "SNE-LX1"


class TestStartCall:
    def test_call_successful(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run()
            svc.start_call("HVY", "5551234")
            cmd = mock.call_args[0][0]
            assert "am start" in " ".join(cmd)
            assert "tel:5551234" in " ".join(cmd)

    def test_call_failure_raises(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(returncode=1, stderr=b"Error: intent not found")
            with pytest.raises(CallFailedError):
                svc.start_call("HVY", "5551234")


class TestTap:
    def test_tap_coordinates(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run()
            svc.tap("HVY", 228, 1937)
            cmd_str = " ".join(mock.call_args[0][0])
            assert "input tap" in cmd_str
            assert "228" in cmd_str
            assert "1937" in cmd_str


class TestKeyevent:
    def test_keyevent_sent(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run()
            svc.keyevent("HVY", "KEYCODE_4")
            cmd_str = " ".join(mock.call_args[0][0])
            assert "input keyevent" in cmd_str
            assert "KEYCODE_4" in cmd_str


class TestIsDeviceLocked:
    def test_locked(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b'User "Sahibi" (id=0, flags=0x13) (current): trusted=0, trustManaged=1, deviceLocked=1, strongAuthRequired=0x0\n'
            )
            assert svc.is_device_locked("HVY") is True

    def test_unlocked(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(
                stdout=b'User "Sahibi" (id=0, flags=0x13) (current): trusted=0, trustManaged=1, deviceLocked=0, strongAuthRequired=0x0\n'
            )
            assert svc.is_device_locked("HVY") is False

    def test_no_trust_output_defaults_locked(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run(stdout=b"")
            assert svc.is_device_locked("HVY") is True


class TestWake:
    def test_wake_sends_wakeup_keyevent(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run()
            svc.wake("HVY")
            cmd_str = " ".join(mock.call_args[0][0])
            assert "KEYCODE_WAKEUP" in cmd_str
            assert "input keyevent" in cmd_str


class TestSwipe:
    def test_swipe_coordinates(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "_run") as mock:
            mock.return_value = _mock_run()
            svc.swipe("HVY", 540, 2000, 540, 500, 300)
            cmd_str = " ".join(mock.call_args[0][0])
            assert "input swipe" in cmd_str
            assert "540" in cmd_str
            assert "2000" in cmd_str
            assert "500" in cmd_str
            assert "300" in cmd_str


class TestExecuteWorkflow:
    def test_workflow_skips_unlock_when_already_unlocked(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "is_device_locked", return_value=False),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            all_calls = [" ".join(c[0][0]) for c in mock.call_args_list]
            assert not any("KEYCODE_WAKEUP" in c for c in all_calls)
            assert not any("swipe" in c for c in all_calls)
            assert not any("KEYCODE_2" in c for c in all_calls)
            assert any("tel:5551234" in c for c in all_calls)
            assert any("KEYCODE_4" in c for c in all_calls)

    def test_workflow_runs_unlock_when_locked(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "is_device_locked", return_value=True),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            all_calls = [" ".join(c[0][0]) for c in mock.call_args_list]
            assert any("KEYCODE_WAKEUP" in c for c in all_calls)
            assert any("swipe" in c for c in all_calls)
            assert any("KEYCODE_2" in c for c in all_calls)

    def test_full_workflow_with_wake_swipe_pin_and_call(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            all_calls = [" ".join(c[0][0]) for c in mock.call_args_list]
            assert any("KEYCODE_WAKEUP" in c for c in all_calls)
            assert any("swipe 540 2000 540 500" in c for c in all_calls)
            assert any("tel:5551234" in c for c in all_calls)
            assert any("tap 228 1937" in c for c in all_calls)
            assert any("KEYCODE_4" in c for c in all_calls)
            keyevent_lines = [c for c in all_calls if "input keyevent" in c]
            assert len(keyevent_lines) == 8  # 1 wakeup + 6 pin + 1 door code

    def test_workflow_skips_wake_and_swipe_when_disabled(self):
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", PHONE_CFG_NO_PREP, "5551234", "4")
            all_calls = [" ".join(c[0][0]) for c in mock.call_args_list]
            assert not any("KEYCODE_WAKEUP" in c for c in all_calls)
            assert not any("swipe" in c for c in all_calls)

    def test_workflow_device_not_found_raises(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "get_devices", return_value={}):
            with pytest.raises(DeviceNotFoundError):
                svc.execute_workflow("HVY", PHONE_CFG, "5551234", "4")

    def test_workflow_device_unauthorized_raises(self):
        svc = AdbService(adb_path="adb")
        with patch.object(svc, "get_devices", return_value={"HVY": "unauthorized"}):
            with pytest.raises(DeviceUnauthorizedError):
                svc.execute_workflow("HVY", PHONE_CFG, "5551234", "4")

    def test_workflow_multidigit_code(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=False,
            keypad_tap={"x": 228, "y": 1937},
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "123")
            keyevent_calls = [
                c for c in mock.call_args_list
                if "keyevent" in " ".join(c[0][0])
            ]
            assert len(keyevent_calls) == 3

    def test_auto_swipe_from_screen_dimensions(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "is_device_locked", return_value=True),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            swipe_calls = [
                c for c in mock.call_args_list
                if "input swipe" in " ".join(c[0][0])
            ]
            assert len(swipe_calls) == 1
            cmd = " ".join(swipe_calls[0][0][0])
            assert "540 2240 540 468 300" in cmd  # w//2, h-100, w//2, h*0.2

    def test_explicit_swipe_unlock_overrides_auto(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 100, "start_y": 500, "end_x": 200, "end_y": 600, "duration_ms": 150},
            keypad_tap={"x": 228, "y": 1937},
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "is_device_locked", return_value=True),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            swipe_calls = [
                c for c in mock.call_args_list
                if "input swipe" in " ".join(c[0][0])
            ]
            assert len(swipe_calls) == 1
            cmd = " ".join(swipe_calls[0][0][0])
            assert "100 500 200 600 150" in cmd

    def test_workflow_phone_pin_then_door_code(self):
        cfg = PhoneConfig(
            manufacturer="HUAWEI",
            screen={"width": 1080, "height": 2340},
            wake_up=True,
            swipe_unlock={"start_x": 540, "start_y": 2000, "end_x": 540, "end_y": 500, "duration_ms": 300},
            keypad_tap=None,
            phone_pin="123456",
        )
        svc = AdbService(adb_path="adb")
        with (
            patch.object(svc, "get_devices", return_value={"HVY": "device"}),
            patch.object(svc, "_run") as mock,
        ):
            mock.return_value = _mock_run()
            svc.execute_workflow("HVY", cfg, "5551234", "4")
            all_calls = [" ".join(c[0][0]) for c in mock.call_args_list]
            assert any("KEYCODE_WAKEUP" in c for c in all_calls)
            assert any("swipe" in c for c in all_calls)
            assert not any("tel:" in c for c in all_calls)
            keyevent_lines = [c for c in all_calls if "input keyevent" in c]
            assert len(keyevent_lines) == 8  # 1 wakeup + 6 PIN + 1 door code
