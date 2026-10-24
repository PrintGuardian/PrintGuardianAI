from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.main import app


def test_stop_print_rejects_missing_or_invalid_control_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.get_settings",
        lambda: SimpleNamespace(control_api_token="correct-secret"),
    )
    stop_requests: list[bool] = []
    monkeypatch.setattr(
        "backend.api.octoprint.cancel_print",
        lambda: stop_requests.append(True) or {"success": True},
    )

    with TestClient(app) as client:
        missing = client.post("/api/printer/stop")
        invalid = client.post(
            "/api/printer/stop",
            headers={"X-PrintGuardian-Token": "wrong-secret"},
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert stop_requests == []


def test_stop_print_is_disabled_without_configured_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.get_settings",
        lambda: SimpleNamespace(control_api_token=""),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/printer/stop",
            headers={"X-PrintGuardian-Token": "any-value"},
        )

    assert response.status_code == 503
    assert "CONTROL_API_TOKEN" in response.json()["detail"]


def test_stop_print_accepts_configured_control_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.get_settings",
        lambda: SimpleNamespace(control_api_token="correct-secret"),
    )
    monkeypatch.setattr(
        "backend.api.octoprint.cancel_print",
        lambda: {"success": True},
    )
    monkeypatch.setattr("backend.api.record_event", lambda *args, **kwargs: None)

    with TestClient(app) as client:
        response = client.post(
            "/api/printer/stop",
            headers={"X-PrintGuardian-Token": "correct-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"success": True}
