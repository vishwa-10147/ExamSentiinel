# Testing

ExamSentinel is tested at four levels: backend unit and API tests, real-engine tests against
the code-execution sandbox, browser tests with Playwright, and a live end-to-end script.

## Contents

- [Test suites](#test-suites)
- [Running the tests](#running-the-tests)
- [Backend test files](#backend-test-files)
- [Browser tests](#browser-tests)
- [Latest results](#latest-results)
- [Load test](#load-test)
- [Writing tests](#writing-tests)

## Test suites

| Suite | Location | Needs |
|---|---|---|
| Backend unit and API | `backend/tests/` | Nothing — uses a temporary SQLite database and a faked engine |
| Real engine | `backend/tests/test_sandbox_engine.py` | Piston on `localhost:2000` (or `PISTON_URL`); skipped otherwise |
| Browser | `frontend/tests/*.spec.ts` | Running frontend and backend for the role journeys |
| End to end | `scripts/e2e_roles_smoke.py` | Running backend with seeded data and Piston |
| Static checks | `tsc`, `next lint`, `next build` | Node.js |
| Theme check | `python frontend/scripts/add-dark-variants.py --check` (CI); `node frontend/scripts/theme-audit.mjs` for screenshots of every page in light and dark mode | Python; running stack for the screenshots |

## Running the tests

```bash
# Backend (about 9 minutes with the engine running; much faster without it)
cd backend
../.venv/Scripts/python -m pytest -q -p no:cacheprovider

# A subset
../.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_practice_bank.py
../.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_sandbox_engine.py -k reverse-linked-list

# Frontend static checks
cd frontend
npx tsc --noEmit
npx next lint

# Browser tests against a running dev server
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test

# End-to-end against running servers
python scripts/e2e_roles_smoke.py
```

`-p no:cacheprovider` avoids a permission error on `.pytest_cache` in some Windows checkouts.
Without `PLAYWRIGHT_BASE_URL`, Playwright starts its own dev server on port 3110.

## Backend test files

| File | Tests | Covers |
|---|---:|---|
| `test_practice_bank.py` | 247 | At least 100 DSA problems, topic minimums, unique and stable IDs, required fields, harness generation in every language, checkers, idempotent seeding |
| `test_sandbox_engine.py` | 183 | Programs in five languages with stdin, stdout and stderr; compile and runtime errors; isolation and limits; solutions in Java, C++, JavaScript and C; a round trip of every type through the C harness; every reference solution |
| `test_practice.py` | 35 | Verdict logic, harness generation, authoring, hidden-data redaction, SQL judging, practice problems in exams |
| `test_judge_queue.py` | 6 | Verdict within the wait, 202 then polling, one pending submission per student, engine-outage retries, recovery of an orphaned job, bounded engine concurrency, per-student (not per-IP) limits |
| `test_cookie_sessions.py` | 7 | httpOnly cookie sign-in and refresh, CSRF header, logout, bearer clients unchanged, failed-login throttle, WebSocket origin check |
| `test_resilience.py` | 4 | Half-open Redis circuit breaker (one probe at a time, cool-down, healthy Redis stays closed); one pooled HTTP client for the engine |
| `test_practice_dsa_api.py` | 8 | IDs, topics, sorting and search; editorial gating; checker protection; history and progress; playground limits; rate limiting |
| Other `test_*.py` | 116 | Authentication, RBAC, SSO, password reset, exams, proctoring and AI, interviews, IRT, adversarial and security checks |

## Browser tests

| Spec | Covers |
|---|---|
| `dashboard.spec.ts` | Login and registration pages render; dashboard requires authentication |
| `protected-routes.spec.ts` | Every protected route redirects anonymous users; login works on a mobile viewport |
| `roles.spec.ts` | Solving a problem (Run and Submit), browsing by topic and ID, a C++ linked-list solution unlocking the editorial, a C solution with LeetCode-style signatures, the progress page, a C program in the playground, staff areas closed to candidates, user creation, problem authoring, reviewer and proctor dashboards |

## Latest results

Recorded on 2026-10-15 on Windows 11 with the execution engine running, so no real-engine test
was skipped. Re-run the suites after any change rather than relying on these figures.

| Suite | Result |
|---|---|
| Backend | **606 passed**, 0 failed, 0 skipped |
| Browser | **26 passed** |
| End to end | **73 / 73** steps passed |
| Type check, lint, production build | No errors or warnings |

Continuous integration (`.github/workflows/ci.yml`) runs the backend suite and a production
frontend build on every pull request and on pushes to `main`. The engine is not available in
CI, so real-engine tests are skipped there.

## Load test

`scripts/load_test.py` simulates an exam rush: N students sign in, then all submit a correct
solution at the same moment; queued (202) submissions are polled like the web app does.

```bash
.venv/Scripts/python scripts/load_test.py --students 200 --api http://localhost:8000
.venv/Scripts/python scripts/load_test.py --cleanup
```

It creates development-only accounts directly in the configured database and refuses to run
when `ENVIRONMENT=production`. All traffic comes from one IP, so for runs above ~250 students
raise `LOGIN_RATE_LIMIT_PER_IP` on the test instance. Results on 2026-10-15 (one API process,
PostgreSQL 16, one Piston container, Windows 11 / 32 cores):

| Students | Sign-in p95 | Submit responses | Accepted | Time to verdict p50 / p95 | Throughput | Errors |
|---:|---:|---|---:|---:|---:|---:|
| 200 | 3.3 s | 200 × 200 | 200 / 200 | 3.7 s / 5.7 s | 29 verdicts/s | 0 |
| 500 | 8.8 s | 500 × 200 | 500 / 500 | 6.1 s / 13.2 s | 33 verdicts/s | 0 |

Load testing found and fixed five problems: the database pool was exhausted by requests
waiting for verdicts; password hashing blocked the event loop; every request in a burst tried
to reconnect to a missing Redis (100 sign-ins took 51 s, now 1.6 s); code-execution limits were
per IP although a whole lab shares one; and a new HTTP connection per engine call cost
150-400 ms (judging rose from 6 to 29-33 verdicts/s once the client was pooled).

## Writing tests

- Fake the engine with the `fake_sandbox` fixture (`tests/test_practice.py`) for API and verdict
  logic; use `test_sandbox_engine.py` for anything that depends on real execution.
- Never assert on random identifiers (UUIDs) containing a substring — compare structured fields.
- Tests that touch student-facing responses should assert that hidden tests, reference
  solutions and checkers are absent.
- Report results as they are; a skipped test is not a passing test.

---

[Back to README](../README.md)
