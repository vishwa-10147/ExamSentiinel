# Milestone 1 Challenger Report: Platform Foundation, Docs & Core Services

**Agent:** `challenger_m1_2`  
**Working Directory:** `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_2\`  
**Milestone:** Milestone 1 (Features 1–7)  
**Date:** 2026-09-16  
**Verdict:** **REJECT**  

---

## 1. Observation

### 1.1 Documentation Suite Completeness (`docs/`)
Direct line-by-line verification was performed comparing files in `docs/` against `ORIGINAL_REQUEST.md`:
- `docs/readme.md` (56 lines) matches `ORIGINAL_REQUEST.md` lines 17–72 verbatim.
- `docs/plan.md` (327 lines) matches `ORIGINAL_REQUEST.md` lines 78–404 verbatim.
- `docs/explain.md` (53 lines) matches `ORIGINAL_REQUEST.md` lines 410–462 verbatim.
- `docs/prompt.md` (29 lines) matches `ORIGINAL_REQUEST.md` lines 468–496 verbatim.
- **Finding:** Documentation is 100% complete and verbatim identical to the specification.

### 1.2 Docker Compose Service Bindings (`docker-compose.yml`)
Inspection of `docker-compose.yml` lines 98–115:
```yaml
  sandbox-worker:
    build:
      context: ./execution-workers
      dockerfile: Dockerfile
    container_name: examsentinel-sandbox-worker
```
- **Filesystem observation:** The directory `d:\vishwa47\v47Studio\ExamSentinel\execution-workers` DOES NOT EXIST.
- **Empirical error:** Executing `docker compose up -d` or `docker compose up --build` fails immediately with:
  `unable to prepare context: path "./execution-workers" not found`.
- This directly breaks acceptance criterion in `ORIGINAL_REQUEST.md` line 528:
  `- [ ] docker compose up -d starts the full stack (frontend, backend, database, Redis) without errors`.

### 1.3 Audit Trail Completeness & Gaps (`backend/app/api/`)
Inspection of `backend/app/api/auth.py` lines 76–85:
```python
    result = await db.execute(select(User).where(User.email == credentials.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
```
- **Observation:** `log_audit_event()` is only called on lines 104–113 upon *successful* login.
- **Finding:** When a login attempt fails due to wrong password or nonexistent user, `HTTPException(401)` is raised with ZERO audit trail logging. Brute force / credential stuffing attacks against student, proctor, and admin accounts leave no forensic records in `audit_logs`.

Inspection of `backend/app/api/deps.py` lines 90–100:
```python
def require_roles(allowed_roles: List[UserRole]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {current_user.role.value}",
            )
        return current_user
    return role_checker
```
- **Finding:** When an authenticated candidate attempts unauthorized access to an administrative endpoint (e.g. `/api/rbac-test/admin-only`), `HTTPException(403)` is returned with ZERO audit trail logging. Internal privilege probing is completely invisible.

### 1.4 Audit Log Buffer Overflow / DoS Vulnerability
Inspection of `backend/app/api/deps.py` lines 114–126:
```python
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    audit_entry = AuditLog(
        ...
        user_agent=user_agent,
    )
    db.add(audit_entry)
    await db.flush()
```
And `backend/app/models/audit_log.py` line 33:
```python
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
```
And `backend/alembic/versions/001_initial_core_schema.py` line 76:
```python
    sa.Column("user_agent", sa.String(length=512), nullable=True),
```
- **Finding:** The incoming `User-Agent` HTTP header is assigned directly without length truncation (`[:512]`). In production PostgreSQL, inserting a string >512 characters into a `VARCHAR(512)` column raises `sqlalchemy.exc.DataError: (psycopg2.errors.StringDataRightTruncation) value too long for type character varying(512)`.
- This causes `await db.flush()` to abort the transaction and crash valid authentication requests (`POST /api/auth/login`, `POST /api/auth/register`) with an unhandled 500 Internal Server Error.

### 1.5 Critical Privilege Escalation on Public Registration
Inspection of `backend/app/api/auth.py` lines 23–50:
```python
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ...
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role,  # <-- ACCEPTS ANY ROLE
        institution_id=user_in.institution_id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
```
And `backend/app/schemas/user.py` lines 15–20:
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.CANDIDATE
    institution_id: Optional[uuid.UUID] = None
```
- **Finding:** An unauthenticated caller on the public registration endpoint can pass `"role": "admin"` or `"role": "proctor"`. The endpoint creates an active user with full administrative privileges, completely bypassing the RBAC security model.

### 1.6 Missing Token Revocation / Refresh Replay Attack
Inspection of `backend/app/api/auth.py` lines 125–207 (`refresh_access_token`):
- `POST /api/auth/refresh` validates the signature of `refresh_req.refresh_token` and generates a new token pair.
- The presented refresh token is NEVER invalidated or recorded in any revocation list (Redis/DB).
- An attacker possessing an intercepted refresh token can repeatedly rotate it and obtain new access tokens until expiration.
- This violates `PROJECT.md` Feature 4: "Access/refresh tokens, password hashing (bcrypt), token revocation".

---

## 2. Logic Chain

1. **Premise 1 (Platform Deployability):** `ORIGINAL_REQUEST.md` Acceptance Criteria specifies that `docker compose up -d` must start the full stack without errors. Because `docker-compose.yml` includes `sandbox-worker` targeting non-existent directory `./execution-workers`, standard container builds fail fatally.
2. **Premise 2 (Security Integrity & RBAC):** An examination integrity platform must prevent unauthorized elevation of privilege. Because `POST /api/auth/register` assigns `role = user_in.role` without enforcing candidate-only self-registration or requiring admin authorization, any user can acquire the `admin` role.
3. **Premise 3 (Audit Trail Completeness):** The platform's foundational principle is "Signals, not verdicts" and transparent accountability. An audit log that records only successful logins while omitting failed logins and 403 authorization denials fails to provide visibility into brute-force attacks and privilege probing.
4. **Premise 4 (System Robustness):** Un-truncated user-controlled input (`User-Agent`) stored into a fixed-width `VARCHAR(512)` column exposes the authentication service to Denial of Service via unhandled database truncation errors in PostgreSQL.
5. **Conclusion:** Because the implementation contains fatal Docker build configuration issues, critical security vulnerabilities (role escalation, token replay), audit logging blindspots, and an unhandled buffer crash, Milestone 1 cannot be approved in its current state.

---

## 3. Caveats

- **SQLite vs PostgreSQL DDL Differences:** Tests executed against in-memory SQLite do not throw `StringDataRightTruncation` on `String(512)` because SQLite does not enforce column width limits by default. However, in the target PostgreSQL 16 production environment specified in `ORIGINAL_REQUEST.md`, this error is fatal.
- **Worker Scope:** The `sandbox-worker` service is slated for Milestone 4 (Features 26–41). However, since `worker_m1` included it in the root `docker-compose.yml`, its missing directory causes Milestone 1's core container orchestration command (`docker compose up -d`) to fail. Either the directory with a minimal stub Dockerfile must be provided, or `sandbox-worker` should be commented out until M4.

---

## 4. Conclusion

**Verdict: REJECT**

Milestone 1 work product is rejected due to five concrete failure modes:
1. `docker-compose.yml` fails to build due to missing context `./execution-workers`.
2. Public user registration permits arbitrary privilege escalation to `admin` or `proctor`.
3. Audit trail completely omits failed logins and unauthorized RBAC access denials.
4. Un-truncated `User-Agent` header in `log_audit_event()` triggers PostgreSQL `DataError` crash.
5. No token revocation or replay defense on rotated refresh tokens.

Documentation in `docs/` is approved (100% verbatim fidelity).

---

## 5. Verification Method

### 5.1 Adversarial Pytest Suite
The empirical challenge suite has been written to `backend/tests/test_adversarial_m1_2.py`.
Run with:
```bash
cd d:\vishwa47\v47Studio\ExamSentinel\backend
pytest tests/test_adversarial_m1_2.py -v
```

Expected failure confirmations:
1. `test_docker_compose_build_contexts_exist` -> FAILS (`./execution-workers` missing)
2. `test_audit_log_completeness_failed_login_attempt` -> FAILS (zero audit records on failed login)
3. `test_audit_log_completeness_unauthorized_rbac_probe` -> FAILS (zero audit records on 403 denial)
4. `test_public_registration_admin_role_escalation` (in `test_adversarial.py`) -> FAILS (admin role granted)
5. `test_refresh_token_replay_vulnerability` (in `test_adversarial.py`) -> FAILS (replay allowed)

### 5.2 Manual Docker Verification
Run:
```bash
docker compose config
docker compose up --build -d
```
Expected output:
```
unable to prepare context: path "./execution-workers" not found
```

### 5.3 Invalidation Conditions
This rejection verdict will be invalidated only when:
1. `docker-compose.yml` builds and starts all services cleanly without missing directory errors.
2. `POST /api/auth/register` restricts public registration to `candidate` role (or ignores caller-supplied privileged roles).
3. Failed login attempts and 403 RBAC access denials create audit log entries in `audit_logs`.
4. `user_agent` in `log_audit_event()` is truncated to 512 characters before insertion.
5. Token revocation is implemented to prevent refresh token replay attacks.
