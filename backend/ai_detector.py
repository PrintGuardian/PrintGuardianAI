from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class AnalysisResult:
    risk_detected: bool
    confidence: float
    label: str
    details: dict[str, float]


class PrintFailureDetector:
    """Baseline temporal-change detector; replace with a trained vision model in production."""
    def __init__(self) -> None:
        self._previous_gray: np.ndarray | None = None

    def analyze(self, frame: np.ndarray) -> AnalysisResult:
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (320, 240))
        if self._previous_gray is None:
            self._previous_gray = gray
            return AnalysisResult(False, 0.0, "baseline_captured", {"changed_pixels_ratio": 0.0})
        difference = cv2.absdiff(gray, self._previous_gray)
        _, mask = cv2.threshold(difference, 35, 255, cv2.THRESH_BINARY)
        ratio = float(np.count_nonzero(mask)) / mask.size
        self._previous_gray = gray
        confidence = min(1.0, ratio / 0.35)
        suspected = ratio > 0.18
        return AnalysisResult(suspected, round(confidence, 3), "unexpected_visual_change" if suspected else "no_anomaly", {"changed_pixels_ratio": round(ratio, 4)})


detector = PrintFailureDetector()
