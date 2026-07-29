import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import get_settings


def record_event(level: str, event_type: str, message: str, **details: Any) -> dict[str, Any]:
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level.upper(), "type": event_type, "message": message, "details": details}
    path = Path(get_settings().event_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    return event


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    path = Path(get_settings().event_log_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in reversed(path.read_text(encoding="utf-8").splitlines()[-limit:])]
