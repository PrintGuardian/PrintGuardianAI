from pathlib import Path
from types import SimpleNamespace

import numpy as np
import requests
from fastapi.testclient import TestClient

from backend import config, events
from backend.camera import Camera, discover_cameras
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
        lambda: SimpleNamespace(camera_stream_fps=30, camera_snapshot_url=""),
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


def test_camera_discovery_returns_only_devices_with_frames(monkeypatch) -> None:
    class FakeCapture:
        def __init__(self, index: int) -> None:
            self.index = index
            self.released = False

        def isOpened(self) -> bool:
            return self.index == 0

        def read(self):
            if self.index == 0:
                return True, np.zeros((48, 64, 3), dtype=np.uint8)
            return False, None

        def release(self) -> None:
            self.released = True

    monkeypatch.setattr("backend.camera.cv2.VideoCapture", FakeCapture)

    assert discover_cameras(max_devices=2) == [
        {"index": 0, "online": True, "width": 64, "height": 48}
    ]


def test_camera_devices_endpoint_validates_probe_limit(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.discover_cameras", lambda max_devices: [])

    with TestClient(app) as client:
        valid = client.get("/api/camera/devices?max_devices=2")
        invalid = client.get("/api/camera/devices?max_devices=17")

    assert valid.status_code == 200
    assert valid.json() == {"devices": [], "count": 0}
    assert invalid.status_code == 422


def test_octoprint_status_includes_active_job(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return self.payload

    responses = iter([
        FakeResponse({"state": {"text": "Printing"}}),
        FakeResponse({
            "job": {"file": {"name": "benchy.gcode"}, "estimatedPrintTime": 7200},
            "progress": {"completion": 42.5, "printTime": 1800, "printTimeLeft": 2400},
            "state": "Printing",
        }),
    ])
    monkeypatch.setattr(
        "backend.octoprint.get_settings",
        lambda: SimpleNamespace(
            octoprint_url="http://octoprint.local",
            octoprint_api_key="test-key",
            request_timeout_seconds=2,
        ),
    )
    monkeypatch.setattr("backend.octoprint.requests.get", lambda *args, **kwargs: next(responses))

    result = OctoPrintClient().status()

    assert result["connected"] is True
    assert result["job"]["job"]["file"]["name"] == "benchy.gcode"
    assert result["job"]["progress"]["completion"] == 42.5


def test_octoprint_status_keeps_connection_when_job_request_fails(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"state": {"text": "Operational"}}

    responses = iter([FakeResponse(), requests.Timeout("job timed out")])
    monkeypatch.setattr(
        "backend.octoprint.get_settings",
        lambda: SimpleNamespace(
            octoprint_url="http://octoprint.local",
            octoprint_api_key="test-key",
            request_timeout_seconds=2,
        ),
    )

    def fake_get(*args, **kwargs):
        response = next(responses)
        if isinstance(response, requests.RequestException):
            raise response
        return response

    monkeypatch.setattr("backend.octoprint.requests.get", fake_get)

    result = OctoPrintClient().status()

    assert result["connected"] is True
    assert result["printer"]["state"]["text"] == "Operational"
    assert result["job_error"] == "job timed out"

