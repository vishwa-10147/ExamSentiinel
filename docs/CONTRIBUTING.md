# Contributing to ExamSentinel

Thank you for helping improve ExamSentinel. This guide explains how to set up a development
environment, the rules every change must follow, and how to get a pull request merged.

## Contents

- [Development setup](#development-setup)
- [Workflow](#workflow)
- [Engineering rules](#engineering-rules)
- [Pull request checklist](#pull-request-checklist)
- [Conventions](#conventions)
- [Adding practice problems](#adding-practice-problems)
- [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)

## Development setup

Follow [Installation](INSTALLATION.md). On Windows, `start-local.cmd` sets everything up and
starts the stack. Keep the code-execution engine running while you work so the real-engine
tests run instead of being skipped.

## Workflow

1. Create a branch from `main`: `feature/<short-name>`, `fix/<short-name>` or `docs/<short-name>`.
2. Make a focused change with tests.
3. Run the checks:
   ```bash
   cd backend && ../.venv/Scripts/python -m pytest -q -p no:cacheprovider
   cd frontend && npx tsc --noEmit && npx next lint
   ```
   For user-facing changes, also run the Playwright suite (see [Testing](TESTING.md)).
4. Open a pull request against `main` using the pull request template. CI runs the backend tests
   and a production frontend build.

## Engineering rules

These rules protect candidates and the integrity of assessments. Reviews enforce them.

| Rule | Why |
|---|---|
| AI output is advisory — never penalise a candidate automatically | Final decisions belong to human reviewers |
| User code runs only in the sandbox, never in the API process | Untrusted code must stay isolated |
| Hidden tests, reference solutions and checkers never reach the browser | Prevents answer leakage |
| Model changes ship with an Alembic migration; guard Postgres-only SQL by dialect | Keeps SQLite development and PostgreSQL production in step |
| Every Redis call has a fallback through `redis_breaker` | Redis is optional; an outage must not fail requests |
| Configuration comes from environment variables; no secrets in Git | `.env.example` holds placeholders only |
| Security claims need a test | [SECURITY.md](SECURITY.md) lists only verified controls |

## Pull request checklist

- [ ] The change is focused and described clearly, including how it was tested
- [ ] New behaviour has tests; the backend suite and frontend checks pass
- [ ] Real-engine tests were run, or the PR states that they were skipped
- [ ] Student-facing responses still exclude hidden data (tests assert this where relevant)
- [ ] Database changes include a migration
- [ ] Documentation is updated where behaviour or configuration changed
- [ ] No secrets, local databases or generated build output are committed

## Conventions

**Commit messages** use the imperative mood ("Add topic filter", not "Added"), keep the subject
under about 72 characters, and explain *why* in the body when it is not obvious. One logical
change per commit.

**Backend** — follow the existing module layout (`api/`, `services/`, `models/`, `schemas/`).
Routes depend on `get_current_user` or `require_roles`; business logic lives in services.

**Frontend** — call the API only through `services/apiClient.ts` (practice calls through
`services/practiceService.ts`). Pages under `app/<role>/` are protected by that role's layout.
Use Tailwind utility classes consistent with neighbouring components.

**Tests** — fake the engine with the `fake_sandbox` fixture for API and verdict logic; put
anything that depends on real execution in `tests/test_sandbox_engine.py`. Report results as
they are: a skipped test is not a passing test.

## Adding practice problems

See [Adding a problem](DSA_QUESTION_BANK.md#adding-a-problem). In short: append (never reorder)
to the bank, use the next free number, write an original statement and a Python reference
solution, then run `tests/test_practice_bank.py`, the engine test for your problem, and
`python seed_practice.py`.

## Reporting bugs and requesting features

Use the issue templates on GitHub. For bugs, include steps to reproduce, the expected and actual
behaviour, and relevant logs. **Report security vulnerabilities privately** as described in the
[security policy](SECURITY.md#reporting-a-vulnerability).

---

[Back to README](../README.md) · [Documentation index](README.md)
