import os
import yaml
from typing import Optional
from dotenv import load_dotenv
from app.models import PhoneConfig

load_dotenv()


class Settings:
    def __init__(self):
        self.PHONE_NUMBER = self._require("PHONE_NUMBER")
        self.DOOR_CODE = self._require("DOOR_CODE")
        self.PHONE_SERIAL = self._require("PHONE_SERIAL")
        self.CONFIG_PATH = os.getenv("CONFIG_PATH", "config/phones.yaml")
        self.ADB_PATH = os.getenv("ADB_PATH", "adb")
        self.WAIT_AFTER_DIAL_S = int(os.getenv("WAIT_AFTER_DIAL_S", "0"))

    def _require(self, name: str) -> str:
        val = os.getenv(name)
        if not val:
            raise ValueError(f"{name} is required but not set")
        return val


class PhoneConfigLoader:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        self._configs: dict[str, PhoneConfig] = {}
        raw_serials = raw.get("serials") or {}
        for serial, data in raw_serials.items():
            self._configs[serial] = PhoneConfig(**data)

    def get(self, serial: str) -> Optional[PhoneConfig]:
        return self._configs.get(serial)

    def list_serials(self) -> list[str]:
        return list(self._configs.keys())
