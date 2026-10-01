# 🛡️ ExamSentinel — AI-Powered Proctored Examination & Assessment Platform

![Build Status](https://img.shields.io/badge/Build-Passing-emerald?style=for-the-badge&logo=github)
![Frontend](https://img.shields.io/badge/Next.js-14_App_Router-000000?style=for-the-badge&logo=nextdotjs)
![Backend](https://img.shields.io/badge/FastAPI-Python_3.11+-009688?style=for-the-badge&logo=fastapi)
![Tests](https://img.shields.io/badge/Pytest-81%2F81_Passed-brightgreen?style=for-the-badge&logo=pytest)
![TypeScript](https://img.shields.io/badge/TypeScript-Clean_0_Errors-blue?style=for-the-badge&logo=typescript)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

> **ExamSentinel** is a state-of-the-art, enterprise-grade online examination and coding assessment platform featuring real-time AI computer vision proctoring, isolated multi-language code sandboxes, MOSS code plagiarism detection, Whisper AI speech-to-text interview transcription, and human-in-the-loop evaluator workflows.

---

## 🌟 Key Features

### 1. 🛡️ Real-Time Automated & Live Proctoring
* **YOLOv11 Computer Vision**: Real-time webcam frame analysis detecting secondary persons, cell phones, books, and gaze deviations (`yolo11n.pt`).
* **Integrity Telemetry**: Tracks window focus loss (`TAB_BLUR`), window resizes, fullscreen exits, right-clicks, and clipboard activity (`COPY_ATTEMPT`, `PASTE_ATTEMPT`).
* **Automated Enforcement**: Enforces 2-warning fullscreen exit limits with automatic emergency session submission upon violation.
* **Proctor Operations Console** (`/proctor/dashboard` & `/proctor/live`): Live video grid stream, risk level spectrum (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), one-click live candidate warning popups, and session termination controls.

### 2. 💻 Multi-Language Code Execution Sandbox
* **LeetCode-Style Split IDE**: Dual-pane workspace with Monaco code editor, theme customization, and test case execution console.
* **Supported Languages**: Python 3, JavaScript (Node.js), Java, C++, C, Go, Rust, and SQL.
* **Isolated Execution Cluster**: Powered by Piston execution engine enforcing strict 5.0-second timeout limits and 128MB memory caps per run.
* **Practice Sandbox** (`/candidate/practice`): Daily run quota counter (25 runs/day), 3-second rate-limit cooldown, and custom STDIN input support.

### 3. 🔍 MOSS Winnowing Code Plagiarism Detector
* Implements the **Winnowing Algorithm** (*Schleimer, Wilkerson, Aiken*) to generate k-gram document fingerprints.
* Computes Jaccard similarity indices across student code submissions to detect structural plagiarism and copied solutions.

### 4. 🎙️ WebRTC Technical Interview Transcriber
* Live AI interview assessment module (`/exam/[id]/interview`).
* Integrates **OpenAI Whisper AI** to transcribe WebRTC audio buffers in real-time.
* Performs semantic keyword extraction to verify technical topic coverage (`concurrency`, `database`, `kubernetes`, `api`).

### 5. 👑 Admin Command Center & User Portals
* **Admin Center** (`/admin/*`): Exam builder, question bank management, CSV bulk uploads, role-based access control (RBAC), AI risk calibrator, and CSV analytics export.
* **Reviewer Marking Center** (`/reviewer/*`): Human-in-the-loop evaluation queue for inspecting AI-flagged video snapshots and subjective grading.
* **Candidate Command Portal** (`/candidate/*`): Dashboard, hardware readiness system check (`/exam/readiness`), problem sets, historical exam results, global leaderboard, and profile activity heatmap.

---

## 🏗️ System Architecture

```
                               ┌────────────────────────┐
                               │   Next.js 14 Frontend   │
                               │   (TypeScript / Tailwind)│
                               └───────────┬────────────┘
                                           │
                                  REST API / WebSockets
                                           │
                               ┌───────────▼────────────┐
                               │   FastAPI Backend      │
                               │  (Python 3.11 / Async) │
                               └─────┬──────────────┬───┘
                                     │              │
             ┌───────────────────────┴─┐          ┌─┴───────────────────────┐
             │ Machine Learning Models │          │ Sandbox Execution Engine│
             │  • YOLOv11 (Vision)     │          │  • Piston Sandbox API   │
             │  • Whisper (Audio)      │          │  • Time/Mem Isolation   │
             │  • MOSS (Plagiarism)    │          └─────────────────────────┘
             └─────────────────────────┘
```

---

## 📂 Project Structure

```
ExamSentinel/
├── ai/                      # AI & Machine Learning Pipeline
│   ├── code_integrity/      # MOSS Winnowing Plagiarism Engine
│   ├── interview_analysis/  # Whisper AI Speech Transcriber & Keyword Extraction
│   ├── models/              # Neural Network Weights (yolo11n.pt)
│   └── proctoring/          # YOLOv11 Computer Vision Frame Analyzer
├── backend/                 # FastAPI Async Backend Application
│   ├── app/
│   │   ├── api/             # API Route Handlers (exams, questions, proctoring, sandbox)
│   │   ├── core/            # Database Config, Security & Auth Tokens
│   │   ├── models/          # SQLAlchemy ORM Models (User, Exam, Session, Question)
│   │   ├── schemas/         # Pydantic Schemas & Request Validation
│   │   └── services/        # Business Logic (Grading, Sandbox, IRT, AI)
│   └── tests/               # Pytest Automated Test Suite (81 Test Cases)
├── frontend/                # Next.js 14 App Router Frontend
│   ├── app/                 # App Router Pages & Layouts
│   │   ├── admin/           # Admin Command Center Routes (13 Sub-routes)
│   │   ├── auth/            # Authentication Routes (Login, Register, Callback)
│   │   ├── candidate/       # Candidate Portal Routes (Dashboard, Practice, Problems)
│   │   ├── exam/            # Live Exam Engine (Readiness, Runner, Interview, Lab)
│   │   ├── proctor/         # Proctor Operations Dashboard & Live Video Grid
│   │   ├── reviewer/        # Reviewer Evaluation & Marking Queue
│   │   ├── privacy/         # Privacy Policy
│   │   └── terms/           # Terms & Conditions
│   ├── components/          # Reusable UI Components & Monaco Editor Integration
│   └── services/            # Axios API Client & Exam Services
├── docs/                    # Technical Documentation & Manuals
│   ├── PROJECT.md           # Project Architecture Specifications
│   ├── PROFESSOR_MANUAL.md  # Administrator & Evaluator User Manual
│   ├── TEST_INFRA.md        # Test Infrastructure Documentation
│   └── ORIGINAL_REQUEST.md  # Original Project Requirements
├── docker-compose.yml       # Production & Development Orchestration
└── README.md                # Project Overview & Setup Instructions
```

---

## 🚀 Quickstart & Setup Guide

### Option 1: Launch via Docker Compose (Recommended)

To spin up the full stack (Frontend, Backend FastAPI, PostgreSQL, Redis, Sandbox) in one command:

```bash
docker-compose up --build
```

- **Frontend Application**: `http://localhost:3000`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`

---

### Option 2: Local Development Setup

#### 1. Backend Setup (FastAPI)
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations / initialization & start server
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup (Next.js 14)
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Run TypeScript compilation check
npx tsc --noEmit

# Start development server
npm run dev
```

---

## 🧪 Testing & Quality Assurance

### Run Backend Pytest Suite
```bash
cd backend
pytest
```
* **Status**: `81 passed` in automated test suite covering authentication, RBAC, exam grading, sandbox execution, IRT scoring, and proctoring telemetry.

### Run Frontend Type Check
```bash
cd frontend
npx tsc --noEmit
```
* **Status**: `0 errors` clean TypeScript compilation.

---

## 📄 Documentation

Detailed documentation and guides are available in the [`docs/`](./docs) folder:
- 📖 [Project Architecture (`docs/PROJECT.md`)](./docs/PROJECT.md)
- 👨‍🏫 [Professor & Administrator Manual (`docs/PROFESSOR_MANUAL.md`)](./docs/PROFESSOR_MANUAL.md)
- 🧪 [Test Infrastructure (`docs/TEST_INFRA.md`)](./docs/TEST_INFRA.md)

---

## 🔒 Security & Privacy

* **Zero Automated Penalty**: AI algorithms produce advisory risk telemetry. Human evaluators (`/reviewer/*`) retain final authority.
* **Encrypted Telemetry**: All proctoring events, frame snapshots, and auto-saved answers are transmitted over SSL/TLS and signed with security hashes.
* **Data Compliance**: Privacy Policy (`/privacy`) and Terms of Service (`/terms`) adhere to strict educational data governance.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
