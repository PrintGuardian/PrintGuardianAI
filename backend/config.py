import os
from dataclasses import dataclass
from functools import lru_cache


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "PrintGuardianAI"
    camera_index: int = 0
    camera_snapshot_url: str = ""
    camera_stream_fps: int = 5
    octoprint_url: str = ""
    octoprint_api_key: str = ""
    control_api_token: str = ""
    ai_agent_enabled: bool = False
    ollama_base_url: str = "http://ollama:11434"
    vision_model: str = "qwen3-vl:2b-instruct"
    ai_interval_seconds: int = 120
    ai_timeout_seconds: float = 180.0
    ai_min_confidence: float = 0.65
    ai_alert_cooldown_seconds: int = 1800
    ai_max_image_side: int = 768
    ai_context_tokens: int = 2048
    request_timeout_seconds: float = 5.0
    event_log_path: str = "data/events.jsonl"
    auto_stop_enabled: bool = False
    auto_stop_confidence: float = 0.90


@lru_cache
def get_settings() -> Settings:
    values: dict[str, str] = {}
    try:
        with open(".env", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
    except FileNotFoundError:
        pass

    values.update(os.environ)
    return Settings(
        app_name=values.get("APP_NAME", "PrintGuardianAI"),
        camera_index=int(values.get("CAMERA_INDEX", "0")),
        camera_snapshot_url=values.get("CAMERA_SNAPSHOT_URL", ""),
        camera_stream_fps=max(1, int(values.get("CAMERA_STREAM_FPS", "5"))),
        octoprint_url=values.get("OCTOPRINT_URL", ""),
        octoprint_api_key=values.get("OCTOPRINT_API_KEY", ""),
        control_api_token=values.get("CONTROL_API_TOKEN", "").strip(),
        ai_agent_enabled=_as_bool(values.get("AI_AGENT_ENABLED", "false")),
        ollama_base_url=values.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/"),
        vision_model=values.get("VISION_MODEL", "qwen3-vl:2b-instruct"),
        ai_interval_seconds=max(30, int(values.get("AI_INTERVAL_SECONDS", "120"))),
        ai_timeout_seconds=max(10.0, float(values.get("AI_TIMEOUT_SECONDS", "180"))),
        ai_min_confidence=min(1.0, max(0.0, float(values.get("AI_MIN_CONFIDENCE", "0.65")))),
        ai_alert_cooldown_seconds=max(0, int(values.get("AI_ALERT_COOLDOWN_SECONDS", "1800"))),
        ai_max_image_side=max(320, min(1280, int(values.get("AI_MAX_IMAGE_SIDE", "768")))),
        ai_context_tokens=max(512, min(8192, int(values.get("AI_CONTEXT_TOKENS", "2048")))),
        request_timeout_seconds=float(values.get("REQUEST_TIMEOUT_SECONDS", "5")),
        event_log_path=values.get("EVENT_LOG_PATH", "data/events.jsonl"),
        auto_stop_enabled=_as_bool(values.get("AUTO_STOP_ENABLED", "false")),
        auto_stop_confidence=float(values.get("AUTO_STOP_CONFIDENCE", "0.90")),
    )
