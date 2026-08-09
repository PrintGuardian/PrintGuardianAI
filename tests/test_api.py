from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend import config, events
from backend.camera import Camera
from backend.main import app
from backend.octoprint import OctoPrintClient


def test_root_describes_service() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "PrintGuardianAI"
    assert response.json()["docs"] == "/docs"


def test_event_store_returns_newest_events_first(tmp_path: Path, monkeypatch) -> None:
    event_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(
        events,
        "get_settings",
        lambda: SimpleNamespace(event_log_path=str(event_path)),
    )

    events.record_event("info", "first", "First event")
    events.record_event("warning", "second", "Second event")

    saved = events.recent_events()

    assert [event["type"] for event in saved] == ["second", "first"]
    assert saved[0]["level"] == "WARNING"


def test_mjpeg_stream_emits_a_valid_frame(monkeypatch) -> None:
    camera = Camera()
    monkeypatch.setattr(
        "backend.camera.get_settings",
        lambda: SimpleNamespace(camera_stream_fps=30),
    )
    monkeypatch.setattr(camera, "jpeg", lambda: b"jpeg-bytes")

    frame = next(camera.mjpeg_stream())

    assert frame.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n")
    assert b"Content-Length: 10" in frame
    assert frame.endswith(b"jpeg-bytes\r\n")


def test_settings_enforce_a_minimum_stream_rate(monkeypatch) -> None:
    config.get_settings.cache_clear()
    monkeypatch.setenv("CAMERA_STREAM_FPS", "0")

    settings = config.get_settings()

    assert settings.camera_stream_fps == 1
    config.get_settings.cache_clear()


def test_octoprint_returns_safe_response_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.octoprint.get_settings",
        lambda: SimpleNamespace(octoprint_url="", octoprint_api_key=""),
    )

    result = OctoPrintClient().cancel_print()

    assert result == {"success": False, "reason": "OctoPrint is not configured"}
