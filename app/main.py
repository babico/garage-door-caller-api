import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.config import Settings, PhoneConfigLoader
from app.adb_service import AdbService
from app.routes import health, call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    loader = PhoneConfigLoader(settings.CONFIG_PATH)
    adb = AdbService(adb_path=settings.ADB_PATH)
    app.state.settings = settings
    app.state.phone_config_loader = loader
    app.state.adb_service = adb
    logger.info(
        "Started with serial=%s phone=%s code=%s",
        settings.PHONE_SERIAL,
        settings.PHONE_NUMBER,
        settings.DOOR_CODE,
    )
    yield


app = FastAPI(
    title="Garage Door Caller API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(call.router)


@app.get("/")
def root():
    return RedirectResponse(url="/docs")
