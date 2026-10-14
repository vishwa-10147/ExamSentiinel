# Architecture

```
 Browser (Next.js 14, React, Monaco)
   │  REST + WebSocket, JWT in Authorization header
   ▼
 FastAPI backend (backend/app)  ──────────────►  PostgreSQL (prod) / SQLite (dev)
   │   │                                          Redis (optional: rate limits, OTPs, pub/sub)
   │   └── HTTP ──► Piston engine (privileged container, per-run isolate sandbox)
   │                 python · node · java · gcc · sqlite3
   └── in-process AI: YOLO (phone/person), BlazeFace (browser), faster-whisper (interviews)
```

## Components

| Component | Code | Notes |
|---|---|---|
| Frontend | `frontend/` (Next.js 14 App Router, TypeScript, Tailwind) | one API client (`services/apiClient.ts`); tokens in localStorage; role areas guarded by `RoleAreaLayout` |
| API | `backend/app/api/` | all routers mounted under `/api` in `router.py` |
| Services | `backend/app/services/` | `practice_judge.py` (judge), `sandbox_service.py` (engine client), `grading_service.py`, `risk_engine.py`, `irt_service.py`, … |
| Models | `backend/app/models/` | SQLAlchemy 2 async; Alembic migrations in `backend/alembic/versions/` (Postgres) |
| Question bank | `backend/practice_bank/` + `backend/seed_practice.py` | see [DSA_QUESTION_BANK.md](DSA_QUESTION_BANK.md) |
| Code execution | `infra/piston/`, `docker-compose.piston.yml` | see [CODE_EXECUTION.md](CODE_EXECUTION.md) |
| AI modules | `ai/` (standalone), backend uses `app/services/*` | YOLO weights in `ai/models/yolo11n.pt` |

## Practice platform data model

```
practice_problems
  id (uuid) · number (unique, public ID) · slug (unique) · title · topic · difficulty · tags[]
  statement · input_format · output_format · constraints · complexity · editorial · hints[]
  judge_mode (FUNCTION | STDIO | SQL) · function_spec (json) · sql_schema · compare_mode
  checker (bank-only Python) · starter_code (json) · reference_solution (json)
  time_limit_ms · memory_limit_mb · is_published · created_by · timestamps
practice_test_cases
  id · problem_id → practice_problems · input_data · expected_output · is_sample · explanation · order_index
practice_submissions
  id · problem_id · user_id · language · source_code · verdict · passed_count · total_count
  runtime_ms · failure (json, hidden-case details redacted) · created_at
```

Migrations: `012_practice_problems` (tables), `013_practice_sql_problems` (SQL mode), `014_practice_dsa_metadata`
(number, topic, formats, complexity, editorial, checker). On SQLite (dev) the seeder creates
tables with `create_all`.

Progress (solved / attempted per topic and difficulty, streaks) is computed from
`practice_submissions`; nothing is denormalised.

## Request flow: Submit

1. `POST /api/practice/problems/{slug}/submit` — auth, rate limit (Redis or in-process
   fallback), one-job-per-user guard.
2. Load the problem and **all** its test cases (samples first).
3. `practice_judge.judge()` builds the language harness, writes every case to
   `es_input.txt`, and makes **one** engine request.
4. Piston compiles/runs inside a fresh sandbox; the harness prints one `@@ES@@` record per
   case.
5. The judge compares each result (`exact` / `unordered` / `float` / `checker`), applies the
   per-case time limit, stops at the first failure and maps engine status to a verdict.
6. The submission is stored (unless the engine was unavailable) with hidden-case details
   removed; the response mirrors it.

Exam questions created from practice problems (`/admin/problems/{id}/to-exam`) store
`practice_problem_id`; `grading_service` judges the candidate's final answer the same way.

## Deployment shapes

- **Local**: backend + frontend natively (SQLite, no Redis), Piston in Docker —
  [INSTALLATION.md](INSTALLATION.md).
- **docker-compose.yml**: postgres, redis, backend, frontend, piston.
- **docker-compose.prod.yml** / AWS: [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md). Piston needs
  `privileged`, so it runs on EC2 (not Fargate) in a private subnet.

## Design rules

- AI risk scores are advisory; humans decide via the reviewer workflow.
- Every Redis caller has a fallback (`redis_breaker`), so a Redis outage degrades features
  instead of failing requests.
- User code never runs in the API process; checkers (trusted bank code) are the only
  problem-specific code that does.
