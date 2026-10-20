import threading
import time
from collections.abc import Iterator
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
    """Thread-safe camera adapter for local USB cameras or HTTP snapshots."""

    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._lock = threading.Lock()

    def _open(self) -> cv2.VideoCapture:
        """Open the configured local camera. Caller must hold _lock."""
        if self._capture is None or not self._capture.isOpened():
            if self._capture is not None:
                self._capture.release()
            self._capture = cv2.VideoCapture(get_settings().camera_index)
        return self._capture

    def status(self) -> CameraStatus:
        settings = get_settings()
        if settings.camera_snapshot_url:
            image = self._snapshot_frame()
            return CameraStatus(
                image is not None,
                settings.camera_index,
                None if image is not None else "Could not fetch camera snapshot",
            )

        try:
            with self._lock:
                capture = self._open()
                online = capture.isOpened()
            return CameraStatus(
                online,
                settings.camera_index,
                None if online else "Could not open camera",
            )
        except Exception as exc:
            return CameraStatus(False, settings.camera_index, str(exc))

    def frame(self) -> np.ndarray | None:
        if get_settings().camera_snapshot_url:
            return self._snapshot_frame()
        with self._lock:
            capture = self._open()
            ok, image = capture.read()
        return image if ok else None

    def _snapshot_frame(self) -> np.ndarray | None:
        settings = get_settings()
        try:
            response = requests.get(
                settings.camera_snapshot_url,
                timeout=settings.request_timeout_seconds,
            )
            response.raise_for_status()
            encoded = np.frombuffer(response.content, dtype=np.uint8)
            return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        except (requests.RequestException, ValueError):
            return None

    def jpeg(self) -> bytes | None:
        image = self.frame()
        if image is None:
            return None
        ok, encoded = cv2.imencode(
            ".jpg",
            image,
            [cv2.IMWRITE_JPEG_QUALITY, 85],
        )
        return encoded.tobytes() if ok else None

    def mjpeg_stream(self) -> Iterator[bytes]:
        """Yield browser-compatible multipart MJPEG frames."""
        interval_seconds = 1 / max(1, get_settings().camera_stream_fps)
        while True:
            image = self.jpeg()
            if image is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(image)}\r\n\r\n".encode()
                    + image
                    + b"\r\n"
                )
            time.sleep(interval_seconds)

    def release(self) -> None:
        """Release the camera safely; safe to call more than once."""
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None


def discover_cameras(max_devices: int = 5) -> list[dict]:
    """Probe camera indexes and return only devices that can produce a frame.

    This is intended as an explicit diagnostic endpoint, not a background scan.
    It may briefly open each device while probing it.
    """
    devices: list[dict] = []
    for index in range(max(0, min(max_devices, 16))):
        capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                continue
            ok, frame = capture.read()
            if ok and frame is not None:
                height, width = frame.shape[:2]
                devices.append(
                    {
                        "index": index,
                        "online": True,
                        "width": int(width),
                        "height": int(height),
                    }
                )
        finally:
            capture.release()
    return devices


camera = Camera()
