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
        request_timeout_seconds=float(values.get("REQUEST_TIMEOUT_SECONDS", "5")),
        event_log_path=values.get("EVENT_LOG_PATH", "data/events.jsonl"),
        auto_stop_enabled=_as_bool(values.get("AUTO_STOP_ENABLED", "false")),
        auto_stop_confidence=float(values.get("AUTO_STOP_CONFIDENCE", "0.90")),
    )
