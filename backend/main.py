from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api import router
from .camera import camera
from .config import get_settings
from .events import record_event


@asynccontextmanager
async def lifespan(_: FastAPI):
    record_event("INFO", "service_started", "PrintGuardianAI service started")
    yield
    camera.release()
    record_event("INFO", "service_stopped", "PrintGuardianAI service stopped")


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": get_settings().app_name, "docs": "/docs"}
