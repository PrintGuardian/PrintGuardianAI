import cv2
from .config import config

class Camera:
    def __init__(self):
        self.camera = cv2.VideoCapture(config.CAMERA_INDEX)

    def capture_frame(self):
        ok, frame = self.camera.read()
        if not ok:
            return None
        return frame

    def release(self):
        self.camera.release()

camera = Camera()
