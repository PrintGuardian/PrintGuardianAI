import json
from types import SimpleNamespace

import cv2
import numpy as np

from backend.vision_agent import LocalVisionAgent


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"message": {"content": self.content}}


class FakeCamera:
    def jpeg(self) -> bytes:
        ok, image = cv2.imencode(".jpg", np.zeros((80, 120, 3), dtype=np.uint8))
        assert ok
        return image.tobytes()


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        ai_agent_enabled=True,
        ollama_base_url="http://ollama:11434",
        vision_model="qwen3-vl:2b-instruct",
        ai_timeout_seconds=180,
        ai_max_image_side=64,
        ai_context_tokens=2048,
        ai_min_confidence=0.65,
        ai_alert_cooldown_seconds=1800,
    )


def test_local_agent_compares_frames_and_deduplicates_alerts(monkeypatch) -> None:
    monkeypatch.setattr("backend.vision_agent.get_settings", _settings)
    recorded_events: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(
        "backend.vision_agent.record_event",
        lambda *args, **kwargs: recorded_events.append((args, kwargs)),
    )
    payloads: list[dict] = []
    assessment = {
        "risk_level": "warning",
        "confidence": 0.82,
        "issue": "Possible detached print",
        "evidence": "The object appears displaced compared with the earlier frame.",
        "recommendation": "Check the live printer before intervening.",
    }

    def fake_post(url, *, json, timeout):
        assert url == "http://ollama:11434/api/chat"
        assert timeout == 180
        payloads.append(json)
        return FakeResponse(__import__("json").dumps(assessment))

    monkeypatch.setattr("backend.vision_agent.requests.post", fake_post)
    agent = LocalVisionAgent()

    first = agent.analyze_once(FakeCamera())
    second = agent.analyze_once(FakeCamera())

    assert first is not None and first["compared_frames"] == 1
    assert second is not None and second["compared_frames"] == 2
    assert payloads[0]["options"]["num_ctx"] == 2048
    assert payloads[0]["format"]["type"] == "object"
    assert len(recorded_events) == 1
    assert recorded_events[0][1]["automatic_stop"] is False
    assert agent.status()["state"] == "ready"


def test_local_agent_stays_disabled_without_contacting_ollama(monkeypatch) -> None:
    settings = _settings()
    settings.ai_agent_enabled = False
    monkeypatch.setattr("backend.vision_agent.get_settings", lambda: settings)

    def unexpected_request(*args, **kwargs):
        raise AssertionError("Ollama must not be contacted when disabled")

    monkeypatch.setattr("backend.vision_agent.requests.post", unexpected_request)
    result = LocalVisionAgent().analyze_once(FakeCamera())

    assert result is None
