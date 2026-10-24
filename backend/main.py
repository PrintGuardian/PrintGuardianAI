import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .api import router
from .camera import camera
from .config import get_settings
from .events import record_event
from .vision_agent import vision_agent


@asynccontextmanager
async def lifespan(_: FastAPI):
    record_event("INFO", "service_started", "PrintGuardianAI service started")
    agent_task = None
    if get_settings().ai_agent_enabled:
        agent_task = asyncio.create_task(vision_agent.run(camera))
    try:
        yield
    finally:
        if agent_task is not None:
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
        camera.release()
        record_event("INFO", "service_stopped", "PrintGuardianAI service stopped")


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": get_settings().app_name, "docs": "/docs"}
