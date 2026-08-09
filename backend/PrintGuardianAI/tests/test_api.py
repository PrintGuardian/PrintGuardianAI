from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend import events
from backend.main import app


def test_root_describes_service() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "PrintGuardianAI"
    assert response.json()["docs"] == "/docs"


def test_event_store_returns_newest_events_first(tmp_path: Path, monkeypatch) -> None:
    event_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(events, "get_settings", lambda: SimpleNamespace(event_log_path=str(event_path)))

    events.record_event("info", "first", "First event")
    events.record_event("warning", "second", "Second event")

    saved = events.recent_events()

    assert [event["type"] for event in saved] == ["second", "first"]
    assert saved[0]["level"] == "WARNING"
