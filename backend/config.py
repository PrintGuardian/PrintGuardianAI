import os

class Config:
    OCTOPRINT_URL = os.getenv("OCTOPRINT_URL", "http://localhost:5000")
    OCTOPRINT_API_KEY = os.getenv("OCTOPRINT_API_KEY", "")
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

config = Config()
