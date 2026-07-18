import logging
import subprocess
import threading
import time
from app.models import PhoneConfig

logger = logging.getLogger(__name__)

KEYCODE_MAP: dict[str, str] = {
    "0": "KEYCODE_0", "1": "KEYCODE_1", "2": "KEYCODE_2",
    "3": "KEYCODE_3", "4": "KEYCODE_4", "5": "KEYCODE_5",
    "6": "KEYCODE_6", "7": "KEYCODE_7", "8": "KEYCODE_8",
    "9": "KEYCODE_9", "*": "KEYCODE_STAR", "#": "KEYCODE_POUND",
}


class ADBNotFoundError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class DeviceUnauthorizedError(Exception):
    pass


class CallFailedError(Exception):
    pass


class CommandTimeoutError(Exception):
    pass


class AdbService:
    def __init__(self, adb_path: str = "adb", timeout: int = 30):
        self._adb_path = adb_path
        self._timeout = timeout
        self._lock = threading.Lock()

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        logger.debug("ADB: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
            logger.debug("ADB stdout: %s", result.stdout.decode(errors="replace").strip()[:500])
            return result
        except FileNotFoundError as e:
            raise ADBNotFoundError(f"ADB binary not found: {self._adb_path}") from e
        except subprocess.TimeoutExpired as e:
            raise CommandTimeoutError(f"ADB command timed out after {self._timeout}s") from e

    def _device_arg(self, serial: str) -> list[str]:
        return ["-s", serial]

    def ensure_daemon(self) -> bool:
        self._run([self._adb_path, "start-server"])
        return True

    def get_devices(self) -> dict[str, str]:
        result = self._run([self._adb_path, "devices"])
        devices: dict[str, str] = {}
        for line in result.stdout.decode().strip().splitlines():
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    serial, state = parts[0], parts[1]
                    devices[serial] = state
        return devices

    def detect_model(self, serial: str) -> str:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "getprop", "ro.product.model"
        ]
        result = self._run(cmd)
        return result.stdout.decode().strip()

    def is_device_locked(self, serial: str) -> bool:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "dumpsys", "trust",
        ]
        result = self._run(cmd)
        for line in result.stdout.decode().splitlines():
            if "deviceLocked=" in line:
                return "deviceLocked=1" in line
        return True

    def wake(self, serial: str) -> None:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "input", "keyevent", "KEYCODE_WAKEUP",
        ]
        self._run(cmd)

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms),
        ]
        self._run(cmd)

    def start_call(self, serial: str, phone_number: str) -> None:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "am", "start", "-a",
            "android.intent.action.CALL", "-d", f"tel:{phone_number}",
        ]
        result = self._run(cmd)
        if result.returncode != 0:
            raise CallFailedError(
                f"Call failed: {result.stderr.decode().strip()}"
            )

    def tap(self, serial: str, x: int, y: int) -> None:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "input", "tap", str(x), str(y),
        ]
        self._run(cmd)

    def keyevent(self, serial: str, keycode: str) -> None:
        cmd = [self._adb_path] + self._device_arg(serial) + [
            "shell", "input", "keyevent", keycode,
        ]
        self._run(cmd)

    def execute_workflow(
        self,
        serial: str,
        phone_cfg: PhoneConfig,
        phone_number: str,
        door_code: str = "",
        wait_after_dial_s: int = 0,
    ) -> None:
        with self._lock:
            self._execute(serial, phone_cfg, phone_number, door_code, wait_after_dial_s)

    def _execute(
        self,
        serial: str,
        phone_cfg: PhoneConfig,
        phone_number: str,
        door_code: str,
        wait_after_dial_s: int,
    ) -> None:
        devices = self.get_devices()
        if serial not in devices:
            raise DeviceNotFoundError(f"Device {serial} not found")
        if devices[serial] != "device":
            raise DeviceUnauthorizedError(f"Device {serial} state: {devices[serial]}")

        should_unlock = self.is_device_locked(serial)

        if should_unlock:
            if phone_cfg.wake_up:
                self.wake(serial)

            if phone_cfg.swipe_unlock:
                s = phone_cfg.swipe_unlock
                self.swipe(serial, s["start_x"], s["start_y"], s["end_x"], s["end_y"],
                           s.get("duration_ms", 300))
            elif phone_cfg.wake_up:
                w = phone_cfg.screen["width"]
                h = phone_cfg.screen["height"]
                self.swipe(serial, w // 2, h - 100, w // 2, int(h * 0.2), 300)

            for digit in phone_cfg.phone_pin:
                kc = KEYCODE_MAP.get(digit)
                if kc:
                    self.keyevent(serial, kc)

        if phone_cfg.keypad_tap:
            self.start_call(serial, phone_number)
            time.sleep(wait_after_dial_s)
            self.tap(serial, phone_cfg.keypad_tap["x"], phone_cfg.keypad_tap["y"])

        for digit in door_code:
            kc = KEYCODE_MAP.get(digit)
            if kc:
                self.keyevent(serial, kc)
