# Security

This document lists the security controls that are **implemented and verified by a test**,
the test that verifies each one, and the known gaps. If a control is not in the "verified"
tables, do not assume it exists.

Report vulnerabilities privately to the maintainers rather than in a public issue.

## Code execution sandbox

User code runs only inside the self-hosted Piston engine, which isolates every run with its
own sandbox (Piston uses `isolate`: Linux namespaces + cgroups). The API process sends
code over HTTP and never executes it.

Verified on the real engine by `backend/tests/test_sandbox_engine.py` (skipped when Piston is
not running; last run 2026-10-14, all passing):

| Control | Observed behaviour | Test |
|---|---|---|
| No network | `connect()` to 1.1.1.1 / 8.8.8.8 → "Network is unreachable"; DNS lookups fail | `test_no_network_access` |
| Time limit | `while True: pass` → `timeout` | `test_infinite_loop_is_killed_by_the_time_limit` |
| Memory limit | 1 GB allocation with a 128 MB limit → killed (`memory_limit`) | `test_memory_hog_is_killed` |
| Process limit | fork loop stops at ~62 processes (`BlockingIOError`) | `test_fork_bomb_hits_the_process_limit` |
| Output limit | unbounded printing → `output_limit` | `test_output_flood_is_cut_off` |
| File-size limit | writing 2 GB → `EFBIG` ("File too large") | `test_large_files_are_refused` |
| Non-root | runs as an unprivileged UID (60 000+ range), not 0 | `test_runs_as_unprivileged_user_without_docker_socket_or_secrets` |
| No Docker socket | `/var/run/docker.sock` absent inside the sandbox | same test |
| No secrets | sandbox environment has only `HOME`, `PATH`, `PWD`, `LC_CTYPE`, `PISTON_LANGUAGE`, …; no app secrets | same test |
| Filesystem isolation | cannot write `/etc`, `/piston/packages`; cannot read `/etc/shadow` or the Piston API source | `test_filesystem_is_isolated_and_not_persistent` |
| No persistence | a file written in one run does not exist in the next | same test |

Engine-side limits are configured in `docker-compose.piston.yml` (run timeout ≤ 10 s, 256 MB
run memory, 64 processes, 8 MB output); per-request limits are set by
`sandbox_service.execute_async` (playground: 5 s, 256 MB; judge: the problem's limits).

### Deployment requirements and residual risk

- **The Piston container itself is `privileged`** so it can create per-run sandboxes. Treat it
  as a high-trust component: run it on its own host/instance, bind its port to localhost or a
  private subnet (`127.0.0.1:2000` in compose; backend security group only on AWS), and do
  not put secrets or other services in that container. A kernel or `isolate` escape would
  give access to that container, not to the API.
- **No container mounts the Docker socket.** The old `sandbox-worker` service, which did,
  has been removed from `docker-compose.yml`.
- Piston's network isolation comes from per-run network namespaces. The test above proves
  outbound IP and DNS are unreachable from user code in our deployment; re-run it after
  changing the engine image or host.

## API controls

| Control | Where | Verified by |
|---|---|---|
| Source size ≤ 50 000 chars; custom stdin ≤ 64 000 (playground) / 20 000 (judge custom input) | Pydantic schemas (`app/api/sandbox.py`, `app/schemas/practice.py`) | `test_playground_runs_programs_with_limits` |
| Rate limits on code execution: run/exam-run/playground 30/min, submit 10/min per IP and path. Enforced by Redis, **with an in-process fallback when Redis is down** | `RateLimiter(..., local_fallback=True)` in `app/api/deps.py` | `test_code_execution_is_rate_limited_without_redis` |
| One judge job per user at a time (429 otherwise) | `_JudgeSlot` (practice), `_users_running` (playground) | code review; not load-tested |
| Hidden tests never sent to students: list/detail return samples only; a failing hidden case reports only its number | `_case_out(reveal_hidden=False)` | `test_admin_creates_problem_and_students_never_see_hidden_tests`, `test_submit_records_submission_and_hides_hidden_failure`, `test_detail_exposes_formats_but_never_checker_or_unearned_editorial` |
| Reference solutions and checkers never returned to students; checkers never returned at all | response schemas omit them | same tests |
| Editorials hidden until the student has an accepted submission | `get_problem` | `test_detail_exposes_formats_but_never_checker_or_unearned_editorial` |
| Checkers (Python run in the API process) only from the repository bank; admin API ignores/refuses them | `ProblemUpsert`, `_apply_upsert` | `test_admin_api_cannot_set_or_enable_a_checker` |
| Engine errors are not leaked to students (generic message, logged server-side) | `app/api/sandbox.py` | `test_playground_hides_engine_internals_on_outage` |
| Unpublished problems hidden from students | `_get_problem(published_only=…)` | `test_unpublished_problems_are_hidden_from_students` |
| Admin-only authoring (403 for other roles) | `require_roles` | `test_admin_creates_problem_and_students_never_see_hidden_tests` |
| Submissions and history are private to their owner | queries filter by `user_id` | `test_submit_records_submission_and_hides_hidden_failure`, `test_submission_history_and_topic_progress` |

Other platform controls (JWT auth, RBAC, password reset OTPs, SSO with PKCE/nonce/JWKS,
DOMPurify for exam HTML, audit logging) are covered by `test_auth.py`, `test_rbac.py`,
`test_password_reset.py`, `test_sso.py`, `test_security.py` and `test_adversarial*.py`.

## Secrets

- Secrets live in environment variables (`backend/.env` locally — git-ignored; a secret
  manager in production). `.env.example` and `.env.production.example` contain placeholders only.
- Only `NEXT_PUBLIC_*` variables reach the browser; none of them is a secret.
- The sandbox environment contains no application variables (verified above).

## Known gaps

- Login/registration rate limits require Redis (they are skipped without it, on purpose, so
  local test suites can log in repeatedly).
- In-process rate-limit windows are per worker process: with N workers the effective limit is
  N × the configured value until Redis is available.
- Access tokens are stored in `localStorage` (no httpOnly cookies), so an XSS bug would expose
  them; exam HTML is sanitised with DOMPurify to reduce that risk.
- AI proctoring signals are advisory only; they never penalise a candidate automatically.
