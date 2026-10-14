---
name: backend-tests
description: Run the ExamSentinel backend pytest suite (and frontend type-check) and report results. Use after changing backend/ or frontend/ code, or when asked to run tests.
argument-hint: "[pytest -k expression]"
allowed-tools: Bash
---

# ExamSentinel tests

## Backend (pytest, ~6 min)

```bash
cd backend && ../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
```
- Pass `-k "<expr>"` (from `$ARGUMENTS`) to narrow the run.
- Tests use their own temp SQLite DB (`tests/conftest.py`) — no Postgres/Redis needed. Slowness comes from Redis connection timeouts; that is expected.
- `-p no:cacheprovider` avoids a permission error writing `backend/.pytest_cache`.
- Never set `DATABASE_URL=` to an empty string — config will fail to parse it.
- Baseline: 81 passed (2026-10-14).

## Frontend type-check

```bash
cd frontend && npx tsc --noEmit
```
Expect exit code 0.

## Report

State pass/fail counts and paste the failing test names with their assertion lines. Do not claim success without the summary line.
