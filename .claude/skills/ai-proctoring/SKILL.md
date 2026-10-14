---
name: ai-proctoring
description: Work on ExamSentinel's cheating detection — browser telemetry, webcam AI (YOLO phone/person detection, BlazeFace), risk weights, de-duplication, auto-submission and the human review queue. Use when changing proctoring events, detection thresholds, or investigating a false/missed detection.
argument-hint: "[event-type or symptom]"
allowed-tools: Bash, Read, Edit
---

# AI proctoring

## Signal flow

```
Browser (frontend/app/exam/[id]/page.tsx)
  tab blur, fullscreen exit, paste, blocked keys …  ─► POST /api/telemetry/events ─┐
FaceTracker (frontend/components/FaceTracker.tsx)                                  │
  BlazeFace face count every 3 s (reports on change, ≤ 1 per 30 s) ─► same ───────┤
  JPEG frame every 10 s ─► POST /api/proctoring/sessions/{id}/webcam/analyze ──────┤
                             (YOLO: phone = COCO 67, person = COCO 0)             │
                                                                                    ▼
             _ingest_signals()  backend/app/api/proctoring.py
               de-dup window per type ─ violation count ─ auto-submit at 4
               risk_engine.recalculate_and_update ─ review case ─ WebSocket broadcast
```

Both entry points go through `_ingest_signals`, so the rules are identical whatever detected the signal.

## Rules (keep them)

- Signals are **advisory**. Auto-submission at `AUTO_SUBMIT_VIOLATIONS` (4) holds results **unpublished**
  and always opens a review case; a human decides. Don't add automatic penalties.
- `_SECURITY_EVENT_TYPES` (backend) and `securityEvents` (exam page) must match.
  `VISIBILITY_HIDDEN` is informational because a tab switch also fires `TAB_BLUR`.
- `_DEDUPE_WINDOW_SECONDS`: one phone held up for a minute is one incident. Add a window for any
  new continuous signal.
- New event type ⇒ add it to `DEFAULT_RISK_WEIGHTS` (that set is the allow-list),
  `_EVENT_CATEGORY_MAP`, `_EVENT_SEVERITY_MAP`, and `ProctoringEventType` in
  `frontend/services/proctoringService.ts`.

## Vision model

- `pip install -r backend/requirements-ai.txt` (CPU PyTorch + ultralytics). Without it the API still
  runs: phone detection reports `unavailable_*` and faces fall back to OpenCV Haar.
- Weights: `ai/models/yolo11n.pt` (or `CV_MODEL_PATH`). Thresholds: `PHONE_CONFIDENCE_THRESHOLD`
  (0.45), `PERSON_CONFIDENCE_THRESHOLD` (0.5).
- The model loads once and is warmed at startup (`computer_vision_service.warm_up`); first inference
  otherwise takes ~15 s. Steady state ≈ 50 ms/frame on CPU.

## Checking detections

```bash
cd backend && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_ai_proctoring.py
```
`test_real_yolo_counts_people_on_sample_images` runs YOLO on the ultralytics sample photos
(2 and 4 people). For phones, use the admin **AI Test** page (`/admin/ai-test`) with a real webcam and
hold a phone up — no bundled sample image contains one.
