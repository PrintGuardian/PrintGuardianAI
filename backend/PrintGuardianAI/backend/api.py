from fastapi import APIRouter, HTTPException, Response
from .ai_detector import detector
from .camera import camera
from .config import get_settings
from .events import recent_events, record_event
from .octoprint import octoprint

router = APIRouter(prefix="/api")


@router.get("/status")
def status() -> dict:
    return {"service": get_settings().app_name, "status": "online", "camera": camera.status().__dict__}


@router.get("/camera")
def camera_status() -> dict:
    return camera.status().__dict__


@router.get("/camera/frame")
def camera_frame() -> Response:
    image = camera.jpeg()
    if image is None:
        raise HTTPException(status_code=503, detail="Camera frame is unavailable")
    return Response(content=image, media_type="image/jpeg")


@router.get("/analyze")
def analyze() -> dict:
    frame = camera.frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera frame is unavailable")
    result = detector.analyze(frame)
    payload = result.__dict__
    if result.risk_detected:
        record_event("WARNING", "anomaly_suspected", "Unexpected visual change detected", **payload)
        settings = get_settings()
        if settings.auto_stop_enabled and result.confidence >= settings.auto_stop_confidence:
            stopped = octoprint.cancel_print()
            record_event("CRITICAL", "automatic_stop", "Automatic print stop requested", **stopped)
            payload["automatic_stop"] = stopped
    return payload


@router.get("/printer")
def printer_status() -> dict:
    return octoprint.status()


@router.post("/printer/stop")
def stop_print() -> dict:
    result = octoprint.cancel_print()
    record_event("CRITICAL" if result["success"] else "WARNING", "manual_stop", "Manual print stop requested", **result)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["reason"])
    return result


@router.get("/events")
def events(limit: int = 50) -> list[dict]:
    return recent_events(max(1, min(limit, 200)))
