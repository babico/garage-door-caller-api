from fastapi import APIRouter, Request
from app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    settings = request.app.state.settings
    loader = request.app.state.phone_config_loader
    adb = request.app.state.adb_service

    adb_available = True
    devices = []
    try:
        adb.ensure_daemon()
        raw_devices = adb.get_devices()
        devices = []
        for serial, state in raw_devices.items():
            try:
                model = adb.detect_model(serial)
            except Exception:
                model = None
            devices.append({"serial": serial, "state": state, "model": model})
    except Exception:
        adb_available = False

    phone_cfg = loader.get(settings.PHONE_SERIAL)

    status = "ok"
    if not adb_available:
        status = "error"
    elif not devices:
        status = "degraded"

    return HealthResponse(
        status=status,
        adb={
            "available": adb_available,
            "daemon_running": adb_available,
            "devices": devices,
        },
        config={
            "phone_serial": settings.PHONE_SERIAL,
            "config_loaded": phone_cfg is not None,
        },
    )
