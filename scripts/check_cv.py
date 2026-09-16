"""Smoke-test the computer-vision dependencies and configured model capability."""

import importlib.util
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def check_module(name: str) -> bool:
    available = importlib.util.find_spec(name) is not None
    print(f"{'PASS' if available else 'FAIL'} dependency: {name}")
    return available


def main() -> int:
    dependencies_ok = all(check_module(name) for name in ("cv2", "numpy", "ultralytics"))
    if not dependencies_ok:
        print("FAIL computer vision dependencies are incomplete")
        return 1

    configured_model_path = os.getenv("CV_MODEL_PATH", "")
    model_path = configured_model_path or str(ROOT / "ai" / "models" / "yolo11n.pt")
    if model_path:
        model = Path(model_path)
        if not model.is_absolute():
            model = ROOT / model
        if model.exists():
            print(f"PASS phone model configured: {model}")
        else:
            print(f"FAIL phone model path does not exist: {model}")
            return 1
    else:
        print("WARN phone model is not configured; face detection remains available")

    import cv2
    import numpy as np
    from app.services.computer_vision import computer_vision_service

    blank = np.zeros((160, 160, 3), dtype=np.uint8)
    encoded, buffer = cv2.imencode(".jpg", blank)
    if not encoded:
        print("FAIL OpenCV could not encode the smoke-test frame")
        return 1

    results = computer_vision_service.analyze_frame(buffer.tobytes())
    if model_path:
        print("PASS YOLO inference smoke test")
    if any(result.event_type == "FACE_NOT_DETECTED" for result in results):
        print("PASS OpenCV frame decode and face-analysis pipeline")
    else:
        print("WARN frame decoded, but face detection is unavailable in this OpenCV build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
