import requests
from .config import config

class OctoPrintClient:
    def __init__(self):
        self.url = config.OCTOPRINT_URL
        self.headers = {
            "X-Api-Key": config.OCTOPRINT_API_KEY
        }

    def get_status(self):
        try:
            response = requests.get(
                f"{self.url}/api/job",
                headers=self.headers,
                timeout=5
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

client = OctoPrintClient()
