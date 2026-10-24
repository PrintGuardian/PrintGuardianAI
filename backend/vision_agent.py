import asyncio
import base64
import json
import math
import threading
import time
from datetime import datetime, timezone
from typing import Any

import cv2
import numpy as np
import requests

from .config import get_settings
from .events import record_event


VISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "risk_level": {
            "type": "string",
            "enum": ["clear", "watch", "warning", "critical"],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "issue": {"type": "string"},
        "evidence": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": [
        "risk_level",
        "confidence",
        "issue",
        "evidence",
        "recommendation",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You inspect FDM 3D printer camera images for visible print failures. "
    "You are an advisory monitor, never a controller. Do not infer hidden "
    "causes or claim a failure unless visible evidence supports it. The first "
    "image is an earlier frame and the second is the current frame when both "
    "are provided. Look for a detached print, severe warping, spaghetti, a "
    "collision, a blocked nozzle, or a clearly abnormal change. Ordinary "
    "layer lines, supports, and intended geometry are not failures. If the "
    "view is unclear or evidence is weak, choose watch or clear with low "
    "confidence. Return only the requested structured assessment."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalVisionAgent:
    """Periodic, local-only visual adviser backed by an Ollama vision model."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._previous_image: bytes | None = None
        self._state = "disabled"
        self._last_analysis_at: str | None = None
        self._last_observation: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._last_duration_seconds: float | None = None
        self._last_alert_fingerprint: str | None = None
        self._last_alert_monotonic = 0.0

    def status(self) -> dict[str, Any]:
        settings = get_settings()
        with self._lock:
            enabled = settings.ai_agent_enabled
            return {
                "enabled": enabled,
                "state": self._state if enabled else "disabled",
                "provider": "Ollama (local)",
                "model": settings.vision_model,
                "interval_seconds": settings.ai_interval_seconds,
                "last_analysis_at": self._last_analysis_at,
                "last_observation": self._last_observation,
                "last_error": self._last_error,
                "last_duration_seconds": self._last_duration_seconds,
            }

    async def run(self, camera: Any) -> None:
        """Analyze one frame per interval without blocking FastAPI's event loop."""
        while True:
            settings = get_settings()
            started = time.monotonic()
            if settings.ai_agent_enabled:
                try:
                    await asyncio.to_thread(self.analyze_once, camera)
                except Exception as exc:  # keep the monitor alive after a bad cycle
                    self._set_error(str(exc))
            else:
                with self._lock:
                    self._state = "disabled"
            elapsed = time.monotonic() - started
            delay = max(30, settings.ai_interval_seconds - int(elapsed))
            await asyncio.sleep(delay)

    def analyze_once(self, camera: Any) -> dict[str, Any] | None:
        """Capture and assess one frame; exposed for explicit diagnostics and tests."""
        settings = get_settings()
        if not settings.ai_agent_enabled:
            with self._lock:
                self._state = "disabled"
            return None

        started = time.monotonic()
        with self._lock:
            self._state = "analyzing"
            self._last_error = None

        try:
            image = camera.jpeg()
            if image is None:
                raise RuntimeError("Camera frame is unavailable")
            current = self._prepare_image(image, settings.ai_max_image_side)
            with self._lock:
                previous = self._previous_image
                self._previous_image = current

            images = [base64.b64encode(current).decode("ascii")]
            if previous is not None:
                images.insert(0, base64.b64encode(previous).decode("ascii"))
            context = (
                "Assess the current printer image. Only one frame is available."
                if previous is None
                else "Compare the earlier image with the current image and assess visible changes."
            )
            response = requests.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.vision_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context, "images": images},
                    ],
                    "format": VISION_SCHEMA,
                    "stream": False,
                    "keep_alive": "2m",
                    "options": {
                        "temperature": 0,
                        "num_ctx": settings.ai_context_tokens,
                        "num_predict": 160,
                    },
                },
                timeout=settings.ai_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            raw_content = body.get("message", {}).get("content", "")
            assessment = self._parse_assessment(raw_content)
            result = {
                **assessment,
                "model": settings.vision_model,
                "timestamp": _utc_now(),
                "compared_frames": len(images),
            }
            duration = round(time.monotonic() - started, 2)
            with self._lock:
                self._state = "ready"
                self._last_analysis_at = result["timestamp"]
                self._last_observation = result
                self._last_error = None
                self._last_duration_seconds = duration

            self._record_alert_if_needed(assessment, settings.ai_min_confidence, settings.ai_alert_cooldown_seconds)
            return result
        except Exception as exc:
            self._set_error(str(exc))
            return None

    @staticmethod
    def _prepare_image(image: bytes, max_side: int) -> bytes:
        decoded = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("Camera returned an invalid JPEG frame")
        height, width = decoded.shape[:2]
        largest = max(width, height)
        if largest > max_side:
            scale = max_side / largest
            decoded = cv2.resize(
                decoded,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        ok, encoded = cv2.imencode(".jpg", decoded, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if not ok:
            raise ValueError("Could not encode camera frame for local analysis")
        return encoded.tobytes()

    @staticmethod
    def _parse_assessment(content: str) -> dict[str, Any]:
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError("Vision model returned an invalid assessment")
        risk = value.get("risk_level")
        if risk not in {"clear", "watch", "warning", "critical"}:
            raise ValueError("Vision model returned an unknown risk level")
        confidence = float(value.get("confidence"))
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Vision model returned invalid confidence")
        return {
            "risk_level": risk,
            "confidence": round(confidence, 3),
            "issue": str(value.get("issue", ""))[:240],
            "evidence": str(value.get("evidence", ""))[:500],
            "recommendation": str(value.get("recommendation", ""))[:300],
        }

    def _record_alert_if_needed(
        self,
        assessment: dict[str, Any],
        minimum_confidence: float,
        cooldown_seconds: int,
    ) -> None:
        risk = assessment["risk_level"]
        if risk not in {"warning", "critical"} or assessment["confidence"] < minimum_confidence:
            return

        fingerprint = f"{risk}:{assessment['issue'].strip().casefold()}"
        now = time.monotonic()
        with self._lock:
            repeated_too_soon = (
                fingerprint == self._last_alert_fingerprint
                and now - self._last_alert_monotonic < cooldown_seconds
            )
            if repeated_too_soon:
                return
            self._last_alert_fingerprint = fingerprint
            self._last_alert_monotonic = now

        record_event(
            "CRITICAL" if risk == "critical" else "WARNING",
            "local_ai_assessment",
            assessment["issue"] or "Local AI detected a possible print issue",
            risk_level=risk,
            confidence=assessment["confidence"],
            evidence=assessment["evidence"],
            recommendation=assessment["recommendation"],
            model=get_settings().vision_model,
            automatic_stop=False,
        )

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._state = "unavailable"
            self._last_error = message[:500]
            self._last_analysis_at = _utc_now()
            self._last_duration_seconds = None


vision_agent = LocalVisionAgent()
