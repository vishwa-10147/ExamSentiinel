# Security Policy

## Supported versions

Security fixes are made on the `main` branch. Deployments should track the latest commit on
`main`.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report them privately through
GitHub's [private vulnerability reporting](https://github.com/vishwa-10147/ExamSentiinel/security/advisories/new)
(*Security → Report a vulnerability*) or by contacting the maintainer directly. Include the
affected component, steps to reproduce and the impact you observed. Please allow time for a fix
before any public disclosure.

## Security model

This section lists the controls that are **implemented and verified by an automated test**,
together with the test that verifies each one, and the known gaps. If a control is not listed
here, do not assume it exists.

### Contents

- [Code execution sandbox](#code-execution-sandbox)
- [Sessions and authentication](#sessions-and-authentication)
- [API controls](#api-controls)
- [Secrets](#secrets)
- [Known gaps](#known-gaps)

### Code execution sandbox

User code runs only inside the self-hosted Piston engine, which isolates every run with its
own sandbox (Piston uses `isolate`: Linux namespaces and cgroups). The API process sends
code over HTTP and never executes it.

Verified on the real engine by `backend/tests/test_sandbox_engine.py` (skipped when Piston is
not running; last run 2026-10-14, all passing):

| Control | Observed behaviour | Test |
|---|---|---|
| No network | `connect()` to 1.1.1.1 / 8.8.8.8 → "Network is unreachable"; DNS lookups fail | `test_no_network_access` |
| Time limit | `while True: pass` → `timeout` | `test_infinite_loop_is_killed_by_the_time_limit` |
| Memory limit | 1 GB allocation with a 128 MB limit → killed (`memory_limit`) | `test_memory_hog_is_killed` |
| Process limit | a fork loop stops at about 62 processes (`BlockingIOError`) | `test_fork_bomb_hits_the_process_limit` |
| Output limit | unbounded printing → `output_limit` | `test_output_flood_is_cut_off` |
| File-size limit | writing 2 GB → `EFBIG` ("File too large") | `test_large_files_are_refused` |
| Non-root | runs as an unprivileged UID (60 000+ range), not 0 | `test_runs_as_unprivileged_user_without_docker_socket_or_secrets` |
| No Docker socket | `/var/run/docker.sock` is absent inside the sandbox | Same test |
| No secrets | the environment holds only `HOME`, `PATH`, `PWD`, `LC_CTYPE`, `PISTON_LANGUAGE` and similar — no application secrets | Same test |
| Filesystem isolation | cannot write `/etc`, `/piston/packages`; cannot read `/etc/shadow` or the Piston API source | `test_filesystem_is_isolated_and_not_persistent` |
| No persistence | a file written in one run does not exist in the next | Same test |

Engine-side limits are configured in `docker-compose.piston.yml` (run timeout ≤ 10 s, 256 MB
run memory, 64 processes, 8 MB output); per-request limits are set by
`sandbox_service.execute_async` (playground: 5 s, 256 MB; judge: the problem's limits).

#### Deployment requirements and residual risk

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

### Sessions and authentication

| Control | Where | Verified by |
|---|---|---|
| Browser sessions use **httpOnly cookies** (`es_access`, `es_refresh`): page scripts cannot read the tokens, and in cookie mode the JSON body carries none | `app/core/auth_cookies.py`, `session_response` in `app/api/auth.py` | `test_cookie_login_keeps_tokens_out_of_javascript`, `test_cookie_refresh_rotates_without_exposing_tokens`; checked in a browser (`document.cookie` is empty, `localStorage` holds no token) |
| Cookies are `SameSite=Lax`, `Secure` in production, and the refresh cookie is scoped to `/api/auth` | `set_auth_cookies` | `test_cookie_login_keeps_tokens_out_of_javascript` |
| CSRF: a state-changing request authenticated by cookie must carry `X-Requested-With` (403 otherwise) | `get_current_user` in `app/api/deps.py` | `test_cookie_requests_that_change_state_need_the_csrf_header` |
| WebSockets accept the session cookie only from an allowed page `Origin` (cross-site WebSocket hijacking) | `_authenticate_ws` in `app/api/monitoring.py` | `test_websocket_cookie_auth_requires_an_allowed_origin` |
| Logout revokes refresh tokens and clears the cookies | `logout` in `app/api/auth.py` | `test_cookie_requests_that_change_state_need_the_csrf_header`, `test_bearer_clients_are_unchanged` |
| Failed sign-ins: 5 per minute per (IP, account), then 429 — successful sign-ins are not counted; plus `LOGIN_RATE_LIMIT_PER_IP` sign-ins per minute per IP (default 300, sized for a lab behind one NAT address). Enforced by Redis **with an in-process fallback** | `FailedLoginThrottle`, `RateLimiter(..., local_fallback=True)` | `test_failed_logins_are_throttled_per_account_without_redis`, `test_successful_logins_are_not_throttled` |
| Registration (3/hour per IP) and password-reset limits hold without Redis | `RateLimiter(..., local_fallback=True)` in `app/api/auth.py` | `test_concurrency_duplicate_registration` |
| Bearer tokens remain available for API clients and scripts (no cookies set for them) | `session_response` | `test_bearer_clients_are_unchanged` |

### API controls

| Control | Where | Verified by |
|---|---|---|
| Source size ≤ 50 000 chars; custom stdin ≤ 64 000 (playground) / 20 000 (judge custom input) | Pydantic schemas (`app/api/sandbox.py`, `app/schemas/practice.py`) | `test_playground_runs_programs_with_limits` |
| Rate limits on code execution: run/exam-run/playground 30/min, submit 10/min **per student** (not per IP — a lab shares one address) and one pending submission at a time. Enforced by Redis, **with an in-process fallback when Redis is down** | `RateLimiter(..., local_fallback=True, per_user=True)` in `app/api/deps.py` | `test_code_execution_is_rate_limited_without_redis`, `test_code_execution_limits_are_per_student_not_per_ip`, `test_slow_judging_returns_202_and_the_result_can_be_polled` |
| One judge job per user at a time (429 otherwise) | `_JudgeSlot` (practice), `_users_running` (playground) | Code review; not load-tested |
| Hidden tests never sent to students: list/detail return samples only; a failing hidden case reports only its number | `_case_out(reveal_hidden=False)` | `test_admin_creates_problem_and_students_never_see_hidden_tests`, `test_submit_records_submission_and_hides_hidden_failure`, `test_detail_exposes_formats_but_never_checker_or_unearned_editorial` |
| Reference solutions and checkers never returned to students; checkers never returned at all | Response schemas omit them | Same tests |
| Editorials hidden until the student has an accepted submission | `get_problem` | `test_detail_exposes_formats_but_never_checker_or_unearned_editorial` |
| Checkers (Python run in the API process) only from the repository bank; admin API ignores/refuses them | `ProblemUpsert`, `_apply_upsert` | `test_admin_api_cannot_set_or_enable_a_checker` |
| Engine errors are not leaked to students (generic message, logged server-side) | `app/api/sandbox.py` | `test_playground_hides_engine_internals_on_outage` |
| Unpublished problems hidden from students | `_get_problem(published_only=…)` | `test_unpublished_problems_are_hidden_from_students` |
| Admin-only authoring (403 for other roles) | `require_roles` | `test_admin_creates_problem_and_students_never_see_hidden_tests` |
| Submissions and history are private to their owner | queries filter by `user_id` | `test_submit_records_submission_and_hides_hidden_failure`, `test_submission_history_and_topic_progress` |

Other platform controls (JWT auth, RBAC, password reset OTPs, SSO with PKCE/nonce/JWKS,
DOMPurify for exam HTML, audit logging) are covered by `test_auth.py`, `test_rbac.py`,
`test_password_reset.py`, `test_sso.py`, `test_security.py` and `test_adversarial*.py`.

### Secrets

- Secrets live in environment variables (`backend/.env` locally — git-ignored; a secret
  manager in production). `.env.example` and `.env.production.example` contain placeholders only.
- Only `NEXT_PUBLIC_*` variables reach the browser; none of them is a secret.
- The sandbox environment contains no application variables (verified above).

### Known gaps

- In-process rate-limit windows are per worker process: with N workers the effective limit is
  N × the configured value until Redis is available.
- An XSS bug could still act *as* the signed-in user while the page is open (it cannot steal
  the tokens); exam HTML is sanitised with DOMPurify to reduce that risk.
- AI proctoring signals are advisory only; they never penalise a candidate automatically.

---

[Back to README](../README.md) · [Documentation index](README.md)
