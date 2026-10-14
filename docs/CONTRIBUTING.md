# Contributing

## Workflow

1. Branch from `main` (`feature/<topic>` or `fix/<topic>`).
2. Make the change with tests (see below). Keep the existing style of the file you touch.
3. Run the checks:
   ```bash
   cd backend && ../.venv/Scripts/python -m pytest -q -p no:cacheprovider
   cd frontend && npx tsc --noEmit && npm run lint
   ```
   With Piston running, the real-engine tests in `backend/tests/test_sandbox_engine.py` run
   too (they are skipped otherwise — say so in your PR if they were skipped).
4. Open a pull request describing what changed and what you ran. Report test results as
   they are; do not mark skipped or unexecuted tests as passing.

## Rules that matter here

- **AI is advisory.** Never add code that penalises a candidate automatically; humans decide
  through the reviewer workflow.
- **User code never runs in the API process.** Everything goes through
  `sandbox_service` → Piston. Checkers are the only problem-specific code that runs in
  the API, and they come only from `backend/practice_bank/`.
- **Never expose hidden tests, reference solutions or checkers** in student-facing responses.
  Add a test when you touch these responses.
- **Model changes need an Alembic migration** in `backend/alembic/versions/`; guard
  Postgres-only SQL with a dialect check. SQLite dev databases are created with `create_all`.
- **Redis is optional.** Use `redis_breaker` (`app/core/redis_client.py`) and provide a
  fallback for every Redis call.
- **No secrets in git.** Configuration comes from environment variables; `.env.example`
  holds placeholders only.
- **Security claims need tests.** Do not document a control in `docs/SECURITY.md` unless a
  test verifies it.

## Adding practice problems

Follow [DSA_QUESTION_BANK.md](DSA_QUESTION_BANK.md#adding-a-problem): append (never
reorder), use the next free number, write an original statement and a Python reference,
then run `tests/test_practice_bank.py`, the engine test for your slug, and
`python seed_practice.py`.

## Frontend

- One API client: `frontend/services/apiClient.ts` (practice calls in
  `services/practiceService.ts`).
- Pages under `app/<role>/` are wrapped by that role's layout guard.
- Browser tests: `cd frontend && npx playwright test` (set `PLAYWRIGHT_BASE_URL` to reuse a
  running dev server).

## Commit messages

Imperative mood, one logical change per commit, explain *why* in the body when it is not
obvious.
