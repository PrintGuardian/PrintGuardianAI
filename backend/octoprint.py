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
        base_url = settings.octoprint_url.rstrip("/")
        headers = {"X-Api-Key": settings.octoprint_api_key}
        timeout = settings.request_timeout_seconds
        try:
            printer_response = requests.get(
                f"{base_url}/api/printer",
                headers=headers,
                timeout=timeout,
            )
            printer_response.raise_for_status()
        except requests.RequestException as exc:
            return {"connected": False, "reason": str(exc)}

        result: dict[str, Any] = {
            "connected": True,
            "printer": printer_response.json(),
        }
        try:
            job_response = requests.get(
                f"{base_url}/api/job",
                headers=headers,
                timeout=timeout,
            )
            job_response.raise_for_status()
            result["job"] = job_response.json()
        except requests.RequestException as exc:
            # Keep the printer connection healthy when the optional job endpoint fails.
            result["job_error"] = str(exc)
        return result

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

