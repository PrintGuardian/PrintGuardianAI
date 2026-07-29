import threading
from dataclasses import dataclass
import cv2
import numpy as np
import requests
from .config import get_settings


@dataclass
class CameraStatus:
    online: bool
    index: int
    error: str | None = None


class Camera:
    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._lock = threading.Lock()

    def _open(self) -> cv2.VideoCapture:
        if self._capture is None or not self._capture.isOpened():
            self._capture = cv2.VideoCapture(get_settings().camera_index)
        return self._capture

    def status(self) -> CameraStatus:
        if get_settings().camera_snapshot_url:
            image = self._snapshot_frame()
            return CameraStatus(image is not None, get_settings().camera_index, None if image is not None else "Could not fetch camera snapshot")
        try:
            capture = self._open()
            return CameraStatus(capture.isOpened(), get_settings().camera_index, None if capture.isOpened() else "Could not open camera")
        except Exception as exc:
            return CameraStatus(False, get_settings().camera_index, str(exc))

    def frame(self) -> np.ndarray | None:
        if get_settings().camera_snapshot_url:
            return self._snapshot_frame()
        with self._lock:
            ok, image = self._open().read()
        return image if ok else None

    def _snapshot_frame(self) -> np.ndarray | None:
        settings = get_settings()
        try:
            response = requests.get(settings.camera_snapshot_url, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            encoded = np.frombuffer(response.content, dtype=np.uint8)
            return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        except requests.RequestException:
            return None

    def jpeg(self) -> bytes | None:
        image = self.frame()
        if image is None:
            return None
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return encoded.tobytes() if ok else None

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


camera = Camera()
