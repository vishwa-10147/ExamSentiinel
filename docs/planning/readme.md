# ExamSentinel

AI-Powered Examination Integrity Platform — now extended with coding exams, interview exams, and adaptive digital exam capabilities.

ExamSentinel lets institutions run secure online exams — MCQ, short/long answer, live coding challenges, and structured interviews — with intelligent, human-reviewed integrity monitoring. No AI model ever issues a final verdict; every signal it surfaces is routed to a human reviewer.

## What's Included

| Track | Capabilities |
|-------|-------------|
| Core Exam Platform | Student portal, exam builder, question bank, browser + webcam proctoring, risk engine, live admin dashboard, review workflow, reporting |
| Coding Exams | In-browser code editor (Monaco), sandboxed multi-language execution, autograding, plagiarism/similarity detection, paste- and typing-pattern integrity signals |
| Interview Exams | Live video interviews (WebRTC), async recorded interviews, panel rubric scoring, auto-transcription, reviewer highlight navigation |
| Digital Exam Extensions | Adaptive (IRT-based) difficulty, offline-resilient exam state, LMS/SSO integration, mobile exam mode, multi-modal question types (diagram, whiteboard, audio) |
| Compliance & Legal | Versioned consent capture, per-institution data retention/deletion, student appeals process, accessibility (WCAG) audits, question-bank IP handling |
| Reliability & Operations | CI/CD gating, observability/alerting, exam-start load testing, backup & disaster recovery |
| Anti-Cheat Hardening | VPN/proxy detection, multi-device/multi-tab detection, interview screen-share detection, question-leak detection |
| Cost & Product Polish | Usage metering and budget alerts, notifications (email/SMS), calendar integration for interviews, pre-publish autograder validation |

## Tech Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Monaco Editor
- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy, WebSockets
- **Database**: PostgreSQL
- **AI / Computer Vision**: OpenCV, YOLO, MediaPipe, NumPy, scikit-learn
- **Code Execution**: Judge0 (or custom gVisor/Firecracker-isolated workers)
- **Video Interviews**: LiveKit / Daily
- **Transcription**: Whisper-class model
- **Infrastructure**: Docker, Docker Compose, Redis

## Getting Started

```bash
git clone <repo-url>
cd exam-sentinel
cp .env.example .env
docker compose up -d
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API Docs (Swagger) → http://localhost:8000/docs

Seed demo data:
```bash
docker compose exec backend python scripts/seed_demo_data.py
```

## Design Principles

1. **No automated guilt.** The platform calculates risk scores and surfaces evidence; only a human reviewer decides on misconduct.
2. **Signals, not verdicts.** Every detector feeds a review queue, never an auto-penalty.
3. **No overclaiming.** The platform never implies monitoring coverage it doesn't actually have.
4. **Privacy by design.** Data minimization, configurable retention, role-based access to evidence, and explicit consent before any capture.
5. **Human review at every consequential step.**
