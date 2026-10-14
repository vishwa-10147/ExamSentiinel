# ExamSentinel

Online examination platform with AI-assisted proctoring and a LeetCode-style coding
practice platform: **116 data-structures-and-algorithms problems** (plus 11 SQL problems)
judged by real compilers and interpreters in an isolated sandbox.

- **Exams** — MCQ, short/long answer, coding and SQL questions, timed sessions, auto-save,
  proctoring signals (tab switches, fullscreen exits, webcam phone/person detection),
  a risk score that is *advisory only*, and a human reviewer workflow.
- **Practice** — problem list with topic/difficulty/status filters, search by title or `#ID`,
  sorting by ID or difficulty; Monaco editor; Run (samples + custom input) and Submit (all
  hidden tests); verdicts; editorials unlocked after solving; submission history and per-topic
  progress.
- **Playground** — compile and run any C, C++, Java, Python or JavaScript program with custom
  stdin, seeing stdout, stderr, compile errors and the exit code.
- **Interviews** — WebRTC interview rooms with Whisper transcription.

## Contents

[Stack](#stack) · [Quick start](#quick-start) · [Question bank](#question-bank) ·
[Languages](#languages) · [Editor, Run and Submit](#editor-run-and-submit) ·
[API](#api) · [Testing](#testing) · [Deployment](#deployment) ·
[Security](#security-and-limitations) · [Troubleshooting](#troubleshooting) ·
[Contributing](#contributing)

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React, TypeScript, Tailwind CSS, Monaco Editor |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL (Docker/production) or SQLite (local development) |
| Cache | Redis (optional; every caller has a fallback) |
| Code execution | self-hosted [Piston](https://github.com/engineer-man/piston) (`infra/piston/`) |
| AI | YOLO11n (phone/person), BlazeFace (in browser), faster-whisper (interviews) |

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start

Requires Python 3.12, Node.js 20+, Docker. Full guide: [docs/INSTALLATION.md](docs/INSTALLATION.md).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt     # macOS/Linux: .venv/bin/python
cd frontend && npm install && cd ..

cp .env.example backend/.env                                        # placeholders; set SECRET_KEY
printf "NEXT_PUBLIC_API_URL=http://localhost:8000\n" > frontend/.env.local

docker compose -f docker-compose.piston.yml up -d --build           # code runner
.venv/Scripts/python scripts/install_piston_runtimes.py             # once

cd backend
../.venv/Scripts/python seed_admin.py                               # demo accounts (development only)
../.venv/Scripts/python seed_practice.py                            # question bank (idempotent)
../.venv/Scripts/python -m uvicorn app.main:app --port 8000         # API → http://localhost:8000/docs
cd ../frontend && npm run dev                                       # UI  → http://localhost:3000
```

Sign in as `candidate@sentinel.edu` (development password printed by `seed_admin.py`) and
open **Problem Set**. Full stack in containers: `docker compose up -d --build`
(see INSTALLATION.md).

## Question bank

| Topic | # | Topic | # |
|---|---|---|---|
| Arrays | 12 | Stacks & Queues | 8 |
| Strings | 10 | Recursion & Backtracking | 8 |
| Hashing | 8 | Trees & BST | 8 |
| Two Pointers | 6 | Heaps | 4 |
| Sliding Window | 6 | Greedy | 4 |
| Binary Search | 7 | Dynamic Programming | 8 |
| Sorting & Searching | 7 | Graphs | 8 |
| Linked Lists | 8 | Bit Manipulation | 4 |
| **DSA total** | **116** (43 Easy · 57 Medium · 16 Hard) | SQL | 11 |

Every problem has a permanent number, statement, input/output format, constraints, 2–3
samples, hidden tests, starter code, a reference solution, complexity, hints and an
editorial. Expected outputs are produced by **executing** the reference solutions, and every
reference passes its tests on the real engine. Seeding is idempotent and never changes IDs.
Details, the full problem index and how to add problems:
[docs/DSA_QUESTION_BANK.md](docs/DSA_QUESTION_BANK.md).

## Languages

| | Python 3.12 | JavaScript (Node 20) | Java 15 | C++17 (gcc 10.2) | C (gcc 10.2) | SQLite 3.36 |
|---|---|---|---|---|---|---|
| Playground | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Function-style problems | ✓ | ✓ | ✓ | ✓ | — | — |
| Stdin/stdout problems | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| SQL problems | — | — | — | — | — | ✓ |

## Editor, Run and Submit

- **Editor**: Monaco with per-language starter code, auto-saved drafts, Ctrl+Enter to run,
  Ctrl+Shift+Enter to submit.
- **Run** executes the visible samples, plus your own input if you add one (its expected
  answer comes from the reference solution). Nothing is stored.
- **Submit** judges every test, samples first, stopping at the first failure. The submission
  is stored; for a failing hidden test only its number is shown.
- **Verdicts**: Accepted, Wrong Answer, Time Limit Exceeded, Memory Limit Exceeded,
  Output Limit Exceeded, Runtime Error, Compile Error (System Error when the engine is down;
  not counted as an attempt).
- Problems with several valid answers use a problem-specific checker (e.g. #111 accepts any
  valid topological order).

How judging works: [docs/CODE_EXECUTION.md](docs/CODE_EXECUTION.md).

## API

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"candidate@sentinel.edu","password":"<dev password>"}' | jq -r .access_token)

curl -s "localhost:8000/api/practice/problems?topic=Graphs&sort=difficulty" -H "Authorization: Bearer $TOKEN"

curl -s -X POST localhost:8000/api/practice/problems/lone-value/submit -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"language":"python","code":"class Solution:\n    def loneValue(self, nums):\n        r = 0\n        for x in nums:\n            r ^= x\n        return r\n"}'

curl -s -X POST localhost:8000/api/sandbox/execute -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"language":"python","code":"print(input()[::-1])","stdin":"hello"}'
```

Reference with real responses: [docs/API.md](docs/API.md). Every route: `/docs` (Swagger).

## Testing

```bash
cd backend && ../.venv/Scripts/python -m pytest -q -p no:cacheprovider   # unit, API, bank and real-engine tests
cd frontend && npx tsc --noEmit                                          # type check
cd frontend && npx playwright test                                       # browser tests
python scripts/e2e_roles_smoke.py                                        # live end-to-end (servers running)
```

Real-engine tests (`backend/tests/test_sandbox_engine.py`) run only when Piston is reachable
on `localhost:2000`; otherwise they are reported as skipped. See
[docs/TEST_INFRA.md](docs/TEST_INFRA.md) for the latest recorded results.

## Deployment

- `docker-compose.yml` — postgres, redis, backend, frontend, piston (development/staging).
- `docker-compose.prod.yml` and [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) — production
  on AWS (ECS for the app, EC2 for Piston, RDS, ElastiCache, S3).

## Security and limitations

Verified controls, with the tests behind them: [docs/SECURITY.md](docs/SECURITY.md). In short,
submissions run only in the Piston sandbox — no network, non-root, time/memory/process/output/
file-size limits, no Docker socket, no application secrets, nothing persisted between runs —
and hidden tests, reference solutions and checkers never reach the browser.

Limitations:

- C is not offered for function-style problems (only for stdin problems and the playground).
- The Piston container must run `privileged`; isolate it on its own host or subnet.
- Login rate limits need Redis; code-execution limits fall back to per-process windows.
- Runtimes are wall-clock measurements and vary with engine load; per-case memory is not reported.
- Access tokens live in `localStorage`.
- AI proctoring signals are advisory; a human reviews every case.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Execution engine unavailable" | start Piston (`docker compose -f docker-compose.piston.yml up -d`) and install runtimes |
| `PayloadTooLargeError` | rebuild our Piston image (`--build`); the stock image has a 100 kB body limit |
| Backend tries to reach Postgres | `backend/.env` missing — copy `.env.example`, which uses SQLite |
| Health is `degraded` | Redis isn't running — fine for local development |

More: [docs/INSTALLATION.md#troubleshooting](docs/INSTALLATION.md#troubleshooting).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Other docs:
[PROFESSOR_MANUAL.md](docs/PROFESSOR_MANUAL.md) (staff guide),
[PROJECT.md](docs/PROJECT.md) (original feature inventory).
