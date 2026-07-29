class AIDetector:
    def __init__(self):
        self.model_loaded = False

    def analyze(self, frame):
        if frame is None:
            return {"error": "no_frame"}

        return {
            "failure_detected": False,
            "confidence": 0.0,
            "status": "model_not_trained"
        }


detector = AIDetector()
