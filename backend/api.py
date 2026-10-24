import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import StreamingResponse

from .ai_detector import detector
from .camera import camera, discover_cameras
from .config import get_settings
from .events import recent_events, record_event
from .octoprint import octoprint
from .vision_agent import vision_agent

router = APIRouter(prefix="/api")


def require_control_token(token: str | None = Header(default=None, alias="X-PrintGuardian-Token")) -> None:
    configured_token = get_settings().control_api_token
    if not configured_token:
        raise HTTPException(
            status_code=503,
            detail="Print stop is disabled. Set CONTROL_API_TOKEN on the backend.",
        )
    if token is None or not secrets.compare_digest(token, configured_token):
        raise HTTPException(status_code=401, detail="Missing or invalid control token")



@router.get("/status")
def status() -> dict:
    return {
        "service": get_settings().app_name,
        "status": "online",
        "camera": camera.status().__dict__,
    }


@router.get("/camera")
def camera_status() -> dict:
    return camera.status().__dict__


@router.get("/camera/devices")
def camera_devices(max_devices: int = 5) -> dict:
    """Discover locally attached cameras that can return a frame."""
    if not 0 <= max_devices <= 16:
        raise HTTPException(
            status_code=422,
            detail="max_devices must be between 0 and 16",
        )
    devices = discover_cameras(max_devices=max_devices)
    return {"devices": devices, "count": len(devices)}


@router.get("/camera/frame")
def camera_frame() -> Response:
    image = camera.jpeg()
    if image is None:
        raise HTTPException(status_code=503, detail="Camera frame is unavailable")
    return Response(content=image, media_type="image/jpeg")


@router.get("/camera/stream")
def camera_stream() -> StreamingResponse:
    status = camera.status()
    if not status.online:
        raise HTTPException(
            status_code=503,
            detail=status.error or "Camera stream is unavailable",
        )

    return StreamingResponse(
        camera.mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/analyze")
def analyze(control_token: str | None = Header(default=None, alias="X-PrintGuardian-Token")) -> dict:
    frame = camera.frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera frame is unavailable")
    result = detector.analyze(frame)
    payload = result.__dict__
    if result.risk_detected:
        record_event(
            "WARNING",
            "anomaly_suspected",
            "Unexpected visual change detected",
            **payload,
        )
        settings = get_settings()
        if (
            settings.auto_stop_enabled
            and result.confidence >= settings.auto_stop_confidence
        ):
            require_control_token(control_token)
            stopped = octoprint.cancel_print()
            record_event(
                "CRITICAL",
                "automatic_stop",
                "Automatic print stop requested",
                **stopped,
            )
            payload["automatic_stop"] = stopped
    return payload


@router.get("/ai/status")
def local_ai_status() -> dict:
    """Return local vision-agent state and its most recent assessment."""
    return vision_agent.status()


@router.get("/printer")
def printer_status() -> dict:
    return octoprint.status()


@router.post("/printer/stop")
def stop_print(_: None = Depends(require_control_token)) -> dict:
    result = octoprint.cancel_print()
    record_event(
        "CRITICAL" if result["success"] else "WARNING",
        "manual_stop",
        "Manual print stop requested",
        **result,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["reason"])
    return result


@router.get("/events")
def events(limit: int = 50) -> list[dict]:
    return recent_events(max(1, min(limit, 200)))
