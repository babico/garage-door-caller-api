import time
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.models import CallResponse
from app.adb_service import (
    DeviceNotFoundError,
    DeviceUnauthorizedError,
    CallFailedError,
    CommandTimeoutError,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["call"])


def _error(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=CallResponse(
            status="error", error=error, message=message
        ).model_dump(),
    )


@router.post("/call")
def call_garage(request: Request):
    settings = request.app.state.settings
    loader = request.app.state.phone_config_loader
    adb = request.app.state.adb_service

    phone_cfg = loader.get(settings.PHONE_SERIAL)
    if phone_cfg is None:
        return _error(
            400, "PHONE_SERIAL_UNKNOWN",
            f"Phone serial '{settings.PHONE_SERIAL}' not found in config",
        )

    devices = adb.get_devices()
    serial = settings.PHONE_SERIAL
    if serial not in devices:
        return _error(
            503, "DEVICE_NOT_FOUND",
            f"Device '{serial}' not connected",
        )
    if devices[serial] != "device":
        return _error(
            503, "DEVICE_UNAUTHORIZED",
            f"Device {serial} is not authorized (state: {devices[serial]})",
        )

    start = time.monotonic()
    try:
        adb.execute_workflow(
            serial=serial,
            phone_cfg=phone_cfg,
            phone_number=settings.PHONE_NUMBER,
            door_code=settings.DOOR_CODE,
            wait_after_dial_s=settings.WAIT_AFTER_DIAL_S,
        )
    except DeviceNotFoundError as e:
        logger.error("Call failed: %s", e)
        return _error(503, "DEVICE_NOT_FOUND", str(e))
    except DeviceUnauthorizedError as e:
        logger.error("Call failed: %s", e)
        return _error(503, "DEVICE_UNAUTHORIZED", str(e))
    except CallFailedError as e:
        logger.error("Call failed: %s", e)
        return _error(502, "CALL_FAILED", str(e))
    except CommandTimeoutError as e:
        logger.error("Call timed out: %s", e)
        return _error(504, "WORKFLOW_TIMEOUT", str(e))

    elapsed = int((time.monotonic() - start) * 1000)
    return CallResponse(
        status="ok",
        message="Call initiated",
        phone_number=settings.PHONE_NUMBER,
        door_code=settings.DOOR_CODE,
        duration_ms=elapsed,
    )
