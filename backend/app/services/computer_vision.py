"""Capability-aware webcam frame analysis.

Object detection (phones, people) uses an Ultralytics YOLO model from
``requirements-ai.txt``; it is loaded once per process and reused. Without it,
face counting falls back to OpenCV's bundled Haar cascade and phone detection
is reported as unavailable instead of being treated as a clean result.

Signals are advisory: they feed the risk score and the human review queue,
never an automatic verdict on their own.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import threading
from typing import Any

from app.core.logging import logger

COCO_PERSON = 0
COCO_CELL_PHONE = 67


@dataclass
class DetectionResult:
    event_type: str | None
    details: dict[str, Any]


class ComputerVisionService:
    def __init__(self) -> None:
        configured_path = os.getenv("CV_MODEL_PATH", "")
        default_path = Path(__file__).resolve().parents[3] / "ai" / "models" / "yolo11n.pt"
        candidate = Path(configured_path) if configured_path else default_path
        self.phone_model_path = str(candidate) if candidate.exists() else ""
        self.phone_threshold = float(os.getenv("PHONE_CONFIDENCE_THRESHOLD", "0.45"))
        self.person_threshold = float(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.5"))
        self._model = None
        self._model_error: str | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _get_model(self):
        """Load YOLO once (thread-safe). Returns None when unavailable."""
        if self._model is not None or self._model_error is not None:
            return self._model
        with self._lock:
            if self._model is None and self._model_error is None:
                if not self.phone_model_path:
                    self._model_error = "model_not_configured"
                else:
                    try:
                        from ultralytics import YOLO

                        self._model = YOLO(self.phone_model_path)
                        logger.info("computer_vision.model_loaded", path=self.phone_model_path)
                    except ImportError:
                        self._model_error = "model_dependency_missing"
                    except Exception as exc:  # corrupt weights, incompatible versions
                        self._model_error = f"model_load_failed: {exc}"
                        logger.error("computer_vision.model_load_failed", error=str(exc))
        return self._model

    @property
    def capabilities(self) -> dict[str, Any]:
        model = self._get_model()
        return {
            "object_detection": model is not None,
            "phone_detection": model is not None,
            "person_counting": model is not None,
            "face_detection_fallback": True,
            "unavailable_reason": self._model_error,
        }

    def warm_up(self) -> None:
        """Load the model and run one tiny inference so the first real frame is fast.

        PyTorch initialisation takes several seconds on first use; call this
        from a background thread at startup.
        """
        model = self._get_model()
        if model is None:
            return
        try:
            import numpy as np

            with self._lock:
                model.predict(np.zeros((64, 64, 3), dtype=np.uint8), verbose=False)
            logger.info("computer_vision.warm")
        except Exception as exc:
            logger.warning("computer_vision.warm_up_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Analysis (CPU-bound: call via asyncio.to_thread from async code)
    # ------------------------------------------------------------------

    def analyze_frame(self, frame: bytes) -> list[DetectionResult]:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Computer-vision dependencies are not installed") from exc

        image = cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded frame is not a valid image")

        model = self._get_model()
        if model is not None:
            return self._analyze_with_yolo(model, image)
        return self._analyze_with_haar(image, cv2) + [
            DetectionResult(None, {"phone_detection": f"unavailable_{self._model_error}"})
        ]

    def _analyze_with_yolo(self, model, image) -> list[DetectionResult]:
        with self._lock:  # Ultralytics predictors are not safe for concurrent calls
            predictions = model.predict(image, verbose=False, classes=[COCO_PERSON, COCO_CELL_PHONE])
        people, phones = [], []
        for prediction in predictions:
            for box in prediction.boxes:
                label = int(box.cls.item())
                confidence = round(float(box.conf.item()), 3)
                coords = [round(v, 1) for v in box.xyxy[0].tolist()]
                if label == COCO_PERSON and confidence >= self.person_threshold:
                    people.append({"confidence": confidence, "box": coords})
                elif label == COCO_CELL_PHONE and confidence >= self.phone_threshold:
                    phones.append({"confidence": confidence, "box": coords})

        results: list[DetectionResult] = []
        if phones:
            results.append(DetectionResult("PHONE_DETECTED", {"source": "yolo", "detections": phones}))
        if len(people) == 0:
            results.append(DetectionResult("FACE_NOT_DETECTED", {"source": "yolo", "people_found": 0}))
        elif len(people) > 1:
            results.append(DetectionResult("MULTIPLE_FACES", {"source": "yolo", "people_found": len(people), "detections": people}))
        if not results:
            results.append(DetectionResult(None, {"source": "yolo", "people_found": len(people), "phones_found": 0}))
        return results

    @staticmethod
    def _analyze_with_haar(image, cv2) -> list[DetectionResult]:
        if not hasattr(cv2, "CascadeClassifier"):
            return [DetectionResult(None, {"face_detection": "unavailable_opencv_api"})]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        if len(faces) == 0:
            return [DetectionResult("FACE_NOT_DETECTED", {"source": "haar", "faces_found": 0})]
        if len(faces) > 1:
            return [DetectionResult("MULTIPLE_FACES", {"source": "haar", "faces_found": len(faces), "bounding_boxes": [b.tolist() for b in faces]})]
        return []


computer_vision_service = ComputerVisionService()
