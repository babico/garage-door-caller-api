from pydantic import BaseModel, Field, field_validator
from typing import Optional


class PhoneConfig(BaseModel):
    manufacturer: str = Field(min_length=1)
    screen: dict
    wake_up: bool = False
    swipe_unlock: Optional[dict] = None
    keypad_tap: Optional[dict] = None
    phone_pin: str = ""

    @field_validator("screen")
    @classmethod
    def screen_dimensions_positive(cls, v):
        if v.get("width", 0) <= 0 or v.get("height", 0) <= 0:
            raise ValueError("screen dimensions must be positive")
        return v


class AdbDevice(BaseModel):
    serial: str = Field(min_length=1)
    state: str = "unknown"
    model: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    adb: Optional[dict] = None
    config: Optional[dict] = None


class CallResponse(BaseModel):
    status: str
    message: Optional[str] = None
    phone_number: Optional[str] = None
    door_code: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
