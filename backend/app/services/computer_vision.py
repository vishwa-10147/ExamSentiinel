"""Capability-aware webcam frame analysis.

Face detection uses OpenCV's bundled Haar cascade. Phone detection is optional
and uses an Ultralytics model when a model path is configured; unavailable
models are reported explicitly instead of being treated as a clean result.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any


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

    def analyze_frame(self, frame: bytes) -> list[DetectionResult]:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Computer-vision dependencies are not installed") from exc

        image = cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded frame is not a valid image")

        results: list[DetectionResult] = []
        if hasattr(cv2, "CascadeClassifier"):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
            if len(faces) == 0:
                results.append(DetectionResult("FACE_NOT_DETECTED", {"faces_found": 0}))
            elif len(faces) > 1:
                results.append(
                    DetectionResult(
                        "MULTIPLE_FACES",
                        {"faces_found": len(faces), "bounding_boxes": [box.tolist() for box in faces]},
                    )
                )
        else:
            results.append(DetectionResult(None, {"face_detection": "unavailable_opencv_api"}))

        if self.phone_model_path:
            try:
                from ultralytics import YOLO

                model = YOLO(self.phone_model_path)
                detections = model.predict(image, verbose=False)
                phone_boxes = []
                for detection in detections:
                    for box in detection.boxes:
                        label = int(box.cls.item())
                        confidence = float(box.conf.item())
                        if label == 67 and confidence >= 0.60:
                            phone_boxes.append({"confidence": confidence, "box": box.xyxy[0].tolist()})
                if phone_boxes:
                    results.append(DetectionResult("PHONE_DETECTED", {"detections": phone_boxes}))
            except ImportError:
                results.append(DetectionResult(None, {"phone_detection": "unavailable_model_dependency"}))
        else:
            results.append(DetectionResult(None, {"phone_detection": "unavailable_model_not_configured"}))

        return results


computer_vision_service = ComputerVisionService()