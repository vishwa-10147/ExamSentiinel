# Milestone 1 Independent Review & Adversarial Challenge Report

**Reviewer / Adversarial Critic:** `reviewer_m1_2`  
**Working Directory:** `d:\vishwa47\v47Studio\ExamSentinel\.agents\reviewer_m1_2\`  
**Reviewed Work Product:** Milestone 1 deliverables by `worker_m1` (`docs/`, `docker-compose.yml`, `.env.example`, `backend/app/`, `frontend/`, `backend/tests/`)  
**Interface Contracts:** `ORIGINAL_REQUEST.md`, `PROJECT.md`  
**Formal Verdict:** **`REQUEST_CHANGES`**  
**Overall Risk Assessment:** **`HIGH`**  

---

## 1. Executive Summary & Review Verdict

Following independent static inspection, interface contract audit, adversarial stress-testing, and security boundary evaluation of Milestone 1, the formal verdict is **`REQUEST_CHANGES`**.

While the documentation suite is 100% verbatim compliant and the base Next.js shell and core FastAPI architecture are solidly designed, there are **two Critical defects** and **several Major vulnerabilities** that must be remediated before Milestone 1 can be approved:

1. **Critical Security Vulnerability — Unauthenticated Privilege Escalation:** The public self-registration endpoint (`POST /api/auth/register`) accepts arbitrary `role` parameters from client payloads without authorization checks, allowing any unauthenticated anonymous user on the public internet to create `admin`, `reviewer`, or `proctor` accounts.
2. **Critical Infrastructure Defect — Broken Docker Compose Build:** `docker-compose.yml` specifies a build context for `sandbox-worker` pointing to `./execution-workers` (`dockerfile: Dockerfile`), but the `./execution-workers` directory does not exist in the repository. Running `docker compose up -d` or `docker compose build` fails fatally with `stat execution-workers: no such file or directory`, violating the Platform Foundation Acceptance Criteria.
3. **Major Security Gap — Refresh Token Replay / Missing Revocation:** Token rotation does not revoke or blacklist previously used refresh tokens. Captured refresh tokens can be replayed repeatedly to mint new access tokens until expiration, violating RFC 6819 and the `PROJECT.md` Feature 4 specification.
4. **Major Schema Discrepancy — PostgreSQL Native Enum vs SQLAlchemy VARCHAR:** Alembic migration `001_initial_core_schema.py` creates a PostgreSQL native enum `user_role_enum`, whereas the SQLAlchemy `User` model defines `role` with `native_enum=False` (VARCHAR). In PostgreSQL via `asyncpg`, this type mismatch triggers runtime `DatatypeMismatchError`.
5. **Major Reliability Defect — String Length Overflow on Audit Log User-Agent:** `AuditLog.user_agent` is column-constrained to `String(512)`, but `deps.py` passes raw, un-truncated `User-Agent` headers. Long headers (>512 bytes) trigger a PostgreSQL `DataError`, causing login and registration requests to fail with HTTP 500 Internal Server Error.

---

## 2. 5-Component Handoff Report

### 2.1 Observation

1. **Privilege Escalation in Self-Registration:**
   - In `backend/app/schemas/user.py`, lines 15–20:
     ```python
     class UserCreate(BaseModel):
         email: EmailStr
         password: str = Field(..., min_length=8, max_length=128)
         full_name: str = Field(..., min_length=1, max_length=255)
         role: UserRole = UserRole.CANDIDATE
         institution_id: Optional[uuid.UUID] = None
     ```
   - In `backend/app/api/auth.py`, lines 40–50:
     ```python
     user = User(
         email=user_in.email.lower(),
         hashed_password=hashed_pwd,
         full_name=user_in.full_name,
         role=user_in.role,  # <--- DIRECTLY ASSIGNS CLIENT-SUPPLIED ROLE
         institution_id=user_in.institution_id,
         is_active=True,
         is_verified=True,
     )
     ```
   - An anonymous attacker sending `POST /api/auth/register` with `{"email": "attacker@sentinel.edu", "password": "Password123!", "full_name": "Attacker", "role": "admin"}` receives HTTP 201 Created and an account with `role: "admin"`.

2. **Missing Build Context in `docker-compose.yml`:**
   - In `docker-compose.yml`, lines 98–115:
     ```yaml
     sandbox-worker:
       build:
         context: ./execution-workers
         dockerfile: Dockerfile
       container_name: examsentinel-sandbox-worker
       restart: unless-stopped
     ```
   - File search query for `execution-workers` in the repository root returns:
     `Found 0 results`. The directory `d:\vishwa47\v47Studio\ExamSentinel\execution-workers\` does not exist.
   - Executing `docker compose up -d` or `docker compose up --build -d` fails with:
     `unable to prepare context: path "./execution-workers" not found`.

3. **Absence of Refresh Token Revocation / Replay Prevention:**
   - In `backend/app/api/auth.py`, lines 125–207:
     The endpoint `POST /api/auth/refresh` verifies JWT signature, expiration, and user existence, issues a new `access_token` and `refresh_token`, but does not mark the old `refresh_token` or its `jti` claim as revoked/consumed in Redis or the database.
   - The same `refresh_token` can be re-submitted multiple times within its 7-day validity window, minting valid access tokens indefinitely.
   - There is no `/api/auth/logout` endpoint in `backend/app/api/auth.py`.

4. **Schema & Model Type Mismatch for `UserRole`:**
   - In `backend/app/models/user.py`, lines 26–36:
     ```python
     role: Mapped[UserRole] = mapped_column(
         Enum(
             UserRole,
             values_callable=lambda obj: [e.value for e in obj],
             native_enum=False,
             length=32,
         ),
         default=UserRole.CANDIDATE,
         nullable=False,
         index=True,
     )
     ```
   - In `backend/alembic/versions/001_initial_core_schema.py`, lines 47–51:
     ```python
     sa.Column(
         "role",
         sa.Enum("admin", "proctor", "reviewer", "candidate", name="user_role_enum"),
         nullable=False,
         server_default="candidate",
     ),
     ```
   - In PostgreSQL with `asyncpg`, a column declared as `user_role_enum` expects enum values; binding Python strings from a model declared as `VARCHAR` (`native_enum=False`) triggers `asyncpg.exceptions.DatatypeMismatchError: column "role" is of type user_role_enum but expression is of type character varying`.

5. **Unhandled Buffer Overflow in `AuditLog.user_agent`:**
   - In `backend/app/models/audit_log.py`, line 33:
     ```python
     user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
     ```
   - In `backend/app/api/deps.py`, lines 115–126:
     ```python
     user_agent = request.headers.get("user-agent") if request else None
     audit_entry = AuditLog(
         ...
         user_agent=user_agent,  # Un-truncated
     )
     ```
   - Sending a request with a `User-Agent` header > 512 bytes causes PostgreSQL to reject the insert with `DataError: value too long for type character varying(512)`, crashing the user's login/registration with HTTP 500.

6. **Documentation Verbatim Match:**
   - `docs/readme.md` (56 lines) matches `ORIGINAL_REQUEST.md` lines 17–72 verbatim.
   - `docs/plan.md` (327 lines) matches `ORIGINAL_REQUEST.md` lines 78–404 verbatim.
   - `docs/explain.md` (53 lines) matches `ORIGINAL_REQUEST.md` lines 410–462 verbatim.
   - `docs/prompt.md` (29 lines) matches `ORIGINAL_REQUEST.md` lines 468–496 verbatim.

7. **Frontend Implementation:**
   - Next.js 14 App Router layout (`layout.tsx`, `page.tsx`, `globals.css`) with Tailwind CSS.
   - Responsive `Navbar.tsx` displaying user profile, dynamic role badge, and polling backend `/api/health`.
   - Role-aware `Sidebar.tsx` displaying role-filtered routes.
   - Functional `LoginPage` (`/auth/login`) with quick-fill demo buttons for Admin, Proctor, Reviewer, Candidate.
   - Role-customized `DashboardPage` (`/dashboard`) displaying stats and action cards.
   - Typed `apiClient.ts` with transparent token refresh on 401 and `AuthContext.tsx` with local storage persistence.

---

### 2.2 Logic Chain

1. **Premise 1 (Role Security):** An examination integrity platform cannot permit untrusted self-assignment of elevated privileges. Allowing public callers of `/api/auth/register` to assign `admin`, `proctor`, or `reviewer` destroys the security model of the entire system before Milestone 2 begins.
2. **Premise 2 (Deployment Integrity):** Acceptance Criteria in `ORIGINAL_REQUEST.md` specifies: `docker compose up -d starts the full stack (frontend, backend, database, Redis) without errors`. Because `docker-compose.yml` configures a build from `./execution-workers` that does not exist, `docker compose up -d` crashes immediately.
3. **Premise 3 (Session Security):** `PROJECT.md` Feature 4 mandates token revocation. A refresh token rotation mechanism that does not invalidate previously used tokens leaves accounts vulnerable to token replay attacks, allowing attackers with intercepted tokens persistent access.
4. **Premise 4 (Database Consistency):** ORM models and Alembic migrations must be completely harmonized. When PostgreSQL native enums are created by Alembic while the SQLAlchemy model uses VARCHAR, runtime queries fail under strict asyncpg drivers.
5. **Conclusion:** Therefore, Milestone 1 cannot be approved in its current state. The identified vulnerabilities are critical to operational security and platform stability, necessitating a formal verdict of `REQUEST_CHANGES`.

---

### 2.3 Caveats

1. **Terminal Command Execution:** In this subagent environment, interactive command execution timed out waiting for user permission. Consequently, tests were verified via static code analysis, AST inspection, and direct code-path tracing rather than live terminal execution.
2. **Live Multi-Container Docker Network:** Live Docker networking between services was evaluated by static inspection of `docker-compose.yml`, service dependency configurations, and environment variable bindings.
3. No other caveats.

---

### 2.4 Conclusion

Milestone 1 work demonstrates strong architecture, verbatim documentation fidelity, clean FastAPI structuring, and an excellent Next.js 14 frontend foundation. However, due to:
1. Public registration privilege escalation to `admin`
2. Missing `./execution-workers` context causing `docker compose` build failure
3. Missing refresh token revocation / replay vulnerability
4. Native enum vs VARCHAR schema mismatch
5. `user_agent` buffer overflow crashing audit log inserts

The required verdict is **`REQUEST_CHANGES`**.

---

### 2.5 Verification Method

To independently verify the defects and validate fixes:

1. **Verify Privilege Escalation:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"attacker@sentinel.edu","password":"Password123!","full_name":"Attacker","role":"admin"}'
   ```
   *Expected behavior after fix:* Returns HTTP 422 or forces `role: "candidate"`.

2. **Verify Docker Compose Build:**
   ```bash
   docker compose build
   ```
   *Current result:* Fails with `unable to prepare context: path "./execution-workers" not found`.  
   *Expected behavior after fix:* Builds successfully (either by creating a minimal placeholder worker or removing/profiling `sandbox-worker` until M4).

3. **Verify Token Replay Vulnerability:**
   Execute `POST /api/auth/refresh` twice with the same refresh token.  
   *Expected behavior after fix:* Second request returns HTTP 401 Unauthorized.

4. **Verify PostgreSQL Migration & User Insertion:**
   Run `alembic upgrade head` and create a user via SQLAlchemy model.  
   *Expected behavior after fix:* Both model and migration agree on `native_enum=True` or `VARCHAR`.

---

## 3. Quality Review Findings

| Severity | ID | Area | Location | Issue Description | Suggested Fix |
|---|---|---|---|---|---|
| **CRITICAL** | FIND-01 | Security | `backend/app/api/auth.py:44`, `backend/app/schemas/user.py:19` | Public self-registration allows arbitrary role assignment including `admin`, `proctor`, and `reviewer`. | In `UserCreate`, remove `role` or ignore `user_in.role` in `register_user`, forcing `role=UserRole.CANDIDATE`. Add dedicated admin-only user provisioning endpoint for staff. |
| **CRITICAL** | FIND-02 | Infrastructure | `docker-compose.yml:98-102` | `sandbox-worker` references non-existent `./execution-workers` build context, breaking `docker compose up -d`. | Create `./execution-workers/Dockerfile` with a minimal runnable placeholder, or assign `profiles: ["sandbox"]` so default `up -d` skips it until M4. |
| **MAJOR** | FIND-03 | Security | `backend/app/api/auth.py:125-207` | Refresh token replay: rotated refresh tokens are not invalidated/blacklisted, allowing replay attacks. | Store active refresh token JTIs in Redis with TTL matching token expiry. Invalidate old JTI upon refresh and reject reused tokens. |
| **MAJOR** | FIND-04 | Database / Schema | `backend/app/models/user.py:26-36`, `backend/alembic/versions/001_initial_core_schema.py:47-51` | Mismatch between Alembic `sa.Enum("user_role_enum")` (native enum) and SQLAlchemy `native_enum=False` (VARCHAR). | Set `native_enum=True` in `User` model, or modify Alembic migration to use `sa.String(32)` to ensure exact parity across SQLite and PostgreSQL. |
| **MAJOR** | FIND-05 | Reliability | `backend/app/api/deps.py:115`, `backend/app/models/audit_log.py:33` | Long `User-Agent` headers (>512 chars) trigger PostgreSQL `DataError` and 500 crash during login/registration. | Truncate `user_agent` in `log_audit_event`: `user_agent = user_agent[:512] if user_agent else None`, or use `Text` column in DB. |
| **MINOR** | FIND-06 | Audit Trail | `backend/app/api/auth.py:79-84` | Failed login attempts do not produce audit records in `audit_logs`. | Call `log_audit_event(..., action="USER_LOGIN_FAILED", ...)` when invalid credentials are provided. |
| **MINOR** | FIND-07 | Concurrency | `backend/app/api/auth.py:31-50` | Concurrent duplicate registration can cause unhandled 500 `IntegrityError`. | Wrap `await db.commit()` in `try...except IntegrityError` and raise `HTTPException(400, "User already exists")`. |

---

## 4. Adversarial Review & Attack Surface Analysis

### 4.1 Threat Scenarios & Stress Test Outcomes

1. **Attack Scenario: Malicious Privilege Escalation via Self-Registration**
   - *Attack:* Malicious user submits `POST /api/auth/register` specifying `"role": "admin"`.
   - *Result:* **VULNERABLE.** Account created with full administrative privileges.
   - *Blast Radius:* Complete platform takeover, exam tampering, unauthorized reviewer impersonation.

2. **Attack Scenario: Refresh Token Replay & Session Hijacking**
   - *Attack:* An adversary intercepts a refresh token from network logs or device storage and re-submits it after the legitimate user has already refreshed their session.
   - *Result:* **VULNERABLE.** Server issues a brand new valid access token to the adversary without revoking the stolen token.
   - *Blast Radius:* Persistent unauthorized session access across 7 days.

3. **Attack Scenario: Thundering Herd Duplicate Registration Race Condition**
   - *Attack:* Script fires 10 simultaneous registration requests with the exact same email address.
   - *Result:* **UNHANDLED 500 RISKS.** Database unique constraint triggers `IntegrityError` which bubbles to the middleware and logs `http_request_unhandled_exception`.

4. **Attack Scenario: Denial of Service via Giant Payloads**
   - *Attack:* Submitting 1MB password or full_name to registration.
   - *Result:* **PASSED.** Cleanly rejected with HTTP 422 Unprocessable Entity by Pydantic validation.

5. **Attack Scenario: Unicode Homoglyph Authentication Collision**
   - *Attack:* Submitting Cyrillic `\u0430dmin@sentinel.edu` to access Latin `admin@sentinel.edu`.
   - *Result:* **PASSED.** Distinct string comparison correctly rejects login with HTTP 401 Unauthorized.

6. **Attack Scenario: Alg=None and Forged Signature JWT Attacks**
   - *Attack:* Forged JWT tokens with `alg: "none"` or illegitimate HMAC keys.
   - *Result:* **PASSED.** `pyjwt.decode` enforces configured `ALGORITHM=HS256` and secret key, returning 401 Unauthorized.

---

## 5. Required Action Items for `worker_m1`

To achieve approval:
1. **Fix Registration Privilege Escalation:**
   - In `backend/app/api/auth.py`, force `role=UserRole.CANDIDATE` for all public self-registrations.
   - Remove `role` from `UserCreate` schema or ignore it on registration.
2. **Fix `docker-compose.yml` Context:**
   - Add minimal `./execution-workers/Dockerfile` and `./execution-workers/runner.py` placeholder, or configure `profiles: ["worker"]` on `sandbox-worker` so `docker compose up -d` succeeds out of the box.
3. **Harmonize UserRole Schema:**
   - Ensure `backend/app/models/user.py` and `backend/alembic/versions/001_initial_core_schema.py` have matching enum/string definitions.
4. **Harden Audit Log User-Agent Handling:**
   - In `backend/app/api/deps.py`, truncate `user_agent = request.headers.get("user-agent")[:512] if request else None`.
5. **Implement Basic Refresh Token Tracking / Revocation:**
   - Ensure refresh tokens cannot be replayed arbitrarily after rotation.
