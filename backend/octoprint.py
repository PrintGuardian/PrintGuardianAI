from typing import Any
import requests
from .config import get_settings


class OctoPrintClient:
    def _configured(self) -> bool:
        settings = get_settings()
        return bool(settings.octoprint_url and settings.octoprint_api_key)

    def status(self) -> dict[str, Any]:
        if not self._configured():
            return {"connected": False, "reason": "OctoPrint is not configured"}
        settings = get_settings()
        try:
            response = requests.get(f"{settings.octoprint_url.rstrip('/')}/api/printer", headers={"X-Api-Key": settings.octoprint_api_key}, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            return {"connected": True, "printer": response.json()}
        except requests.RequestException as exc:
            return {"connected": False, "reason": str(exc)}

    def cancel_print(self) -> dict[str, Any]:
        if not self._configured():
            return {"success": False, "reason": "OctoPrint is not configured"}
        settings = get_settings()
        try:
            response = requests.post(f"{settings.octoprint_url.rstrip('/')}/api/job", headers={"X-Api-Key": settings.octoprint_api_key}, json={"command": "cancel"}, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            return {"success": True}
        except requests.RequestException as exc:
            return {"success": False, "reason": str(exc)}


octoprint = OctoPrintClient()
