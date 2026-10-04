# Milestone 1 Adversarial Challenge Report: Platform Foundation & Authentication

**Agent:** `challenger_m1_1`  
**Role:** Adversarial Correctness Challenger (critic, specialist)  
**Working Directory:** `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\`  
**Target:** Milestone 1 Work Product (`worker_m1`)  
**Date:** 2026-09-16  
**Formal Verdict:** **REJECT**

---

## Challenge Summary

**Overall Risk Assessment:** **CRITICAL**

The Milestone 1 platform foundation contains severe security flaws in authentication and authorization that fundamentally undermine the platform's security boundary:
1. **Critical Privilege Escalation:** Any anonymous user can directly self-register as a system `admin` via `POST /api/auth/register` because the endpoint accepts and applies the requested `role` without restriction.
2. **Critical Token Replay / Missing Revocation:** Refresh token rotation does not invalidate prior refresh tokens. A captured or rotated refresh token can be reused repeatedly to mint new token pairs for up to 7 days, directly violating RFC 6819 and the explicit mandate in `DISPATCH.md` and `PROJECT.md` Feature 4.
3. **High Concurrency Flaw:** Simultaneous duplicate registration requests trigger an unhandled database `IntegrityError`, resulting in a `500 Internal Server Error` crash instead of a clean `400 Bad Request` or `409 Conflict`.
4. **Medium Foreign Key Crash:** Submitting an arbitrary `institution_id` at registration causes an unhandled database foreign key violation crash (HTTP 500) in PostgreSQL.

---

## 1. Observation

### 1.1 Arbitrary Role Escalation via Public Registration
- **File:** `backend/app/schemas/user.py`, lines 15–21:
  ```python
  class UserCreate(BaseModel):
      email: EmailStr
      password: str = Field(..., min_length=8, max_length=128)
      full_name: str = Field(..., min_length=1, max_length=255)
      role: UserRole = UserRole.CANDIDATE
      institution_id: Optional[uuid.UUID] = None
  ```
- **File:** `backend/app/api/auth.py`, lines 40–49:
  ```python
  hashed_pwd = get_password_hash(user_in.password)
  user = User(
      email=user_in.email.lower(),
      hashed_password=hashed_pwd,
      full_name=user_in.full_name,
      role=user_in.role,
      institution_id=user_in.institution_id,
      is_active=True,
      is_verified=True,
  )
  db.add(user)
  ```
- **Direct Observation:** The public endpoint `POST /api/auth/register` accepts `role` directly from the client. When an unauthenticated caller sends `{"role": "admin", ...}`, the backend creates an active user with `role = UserRole.ADMIN`. Subsequent login issues a JWT with `"role": "admin"`, granting immediate access to `/api/rbac-test/admin-only` and all administrative operations.

### 1.2 Missing Refresh Token Revocation & Replay Permitted
- **File:** `backend/app/api/auth.py`, lines 132–206:
  ```python
  @router.post("/refresh", response_model=TokenResponse)
  async def refresh_access_token(
      refresh_req: TokenRefreshRequest,
      request: Request,
      db: AsyncSession = Depends(get_db),
  ):
      ...
      payload = decode_token(refresh_req.refresh_token)
      ...
      token_data = {
          "user_id": str(user.id),
          "email": user.email,
          "role": user.role.value,
          "institution_id": str(user.institution_id) if user.institution_id else None,
      }
      new_access_token = create_access_token(data=token_data)
      new_refresh_token = create_refresh_token(data=token_data)
      ...
      return TokenResponse(...)
  ```
- **File:** `backend/tests/test_auth.py`, lines 95–105 (`test_refresh_token_rotation`):
  Worker `worker_m1` verified only that calling `/api/auth/refresh` returned a different access token string. They never attempted to reuse `refresh_token` a second time.
- **Direct Observation:** There is no token blacklist, revocation storage, or `jti` tracking in PostgreSQL or Redis. Once a refresh token is issued, it remains completely valid for 7 days regardless of how many times it has been rotated. An attacker with a captured refresh token can continuously replay it to mint new access and refresh tokens indefinitely.

### 1.3 Unhandled Concurrency Crash on Duplicate Registration
- **File:** `backend/app/api/auth.py`, lines 31–36 and 64:
  ```python
  existing_result = await db.execute(select(User).where(User.email == user_in.email.lower()))
  if existing_result.scalar_one_or_none():
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="A user with this email address already exists",
      )
  ...
  await db.commit()
  ```
- **Direct Observation:** A classic Time-of-Check to Time-of-Use (TOCTOU) race condition exists. When concurrent requests submit the same email, both pass the `SELECT` query. The second transaction triggers a database `IntegrityError` upon `await db.commit()`. Because `auth.py` lacks a `try...except IntegrityError` handler, the exception escapes to `main.py:80-93`, resulting in an unhandled exception and `500 Internal Server Error`.

### 1.4 Adversarial Test Suite Implemented
- **File:** `backend/tests/test_adversarial.py`
  Created a 17-test adversarial suite testing:
  1. `test_token_wrong_signature`
  2. `test_token_algorithm_none_attack`
  3. `test_token_expired`
  4. `test_token_role_tampering_in_payload`
  5. `test_token_nonexistent_user_uuid`
  6. `test_token_malformed_user_id`
  7. `test_refresh_token_used_as_bearer_token`
  8. `test_refresh_token_replay_vulnerability` (EMPIRICAL FAILURE)
  9. `test_public_registration_admin_role_escalation` (EMPIRICAL FAILURE)
  10. `test_role_route_enforcement`
  11. `test_proctor_cannot_access_admin_route`
  12. `test_reviewer_cannot_access_admin_route`
  13. `test_sql_injection_in_login_email`
  14. `test_sql_injection_in_login_password`
  15. `test_xss_payload_in_full_name`
  16. `test_unicode_and_special_chars_in_full_name`
  17. `test_deactivated_account_rejection`
  18. `test_concurrent_duplicate_registration_race_condition` (EMPIRICAL FAILURE)

---

## 2. Logic Chain

1. **Premise 1 (Privilege Escalation):** Per `PROJECT.md` Feature 5 and `ORIGINAL_REQUEST.md`, RBAC must strictly segregate `admin`, `proctor`, `reviewer`, and `candidate` privileges. A public user registration endpoint that accepts `role` directly from unauthenticated requests allows any actor to bypass the entire security perimeter by creating an administrator account.
2. **Premise 2 (Refresh Token Security):** Per `DISPATCH.md` Item 1 ("ensure reuse of old refresh token fails") and `PROJECT.md` Feature 4 ("token revocation"), refresh tokens must support single-use rotation with revocation. In the current implementation, `refresh_access_token` is entirely stateless with respect to tokens. Because the server does not record consumed `jti` values or invalidate prior tokens, any rotated token can be replayed repeatedly throughout its 7-day lifetime.
3. **Premise 3 (System Reliability & Error Handling):** High-availability exam systems cannot crash with unhandled 500 exceptions when concurrent users register or when duplicate network submissions occur. The unhandled database `IntegrityError` in `register_user` violates error-handling standards.
4. **Deduction:** Because these vulnerabilities allow full administrator takeover, token replay persistence, and server crash under concurrency, Milestone 1 cannot be approved in its current state.

---

## 3. Challenges & Detailed Findings

### [CRITICAL] Challenge 1: Arbitrary Administrative Role Escalation via Public Registration
- **Assumption Challenged:** "Role-Based Access Control (RBAC) securely protects admin and staff operations."
- **Attack Scenario:** Attacker calls `POST /api/auth/register` with payload `{"email": "hacker@domain.com", "password": "Password123!", "full_name": "Hacker", "role": "admin"}`. Server creates an admin user. Attacker logs in and gains full admin rights.
- **Blast Radius:** Total compromise of all exams, student data, monitoring feeds, reviewer queues, and system configuration.
- **Mitigation:**
  1. Remove `role` from `UserCreate` schema or force `user.role = UserRole.CANDIDATE` unconditionally inside `register_user`.
  2. Create a dedicated `POST /api/users/` endpoint protected by `require_roles([UserRole.ADMIN])` for provisioning `admin`, `proctor`, and `reviewer` users.

### [CRITICAL] Challenge 2: Indefinite Refresh Token Replay / Missing Revocation
- **Assumption Challenged:** "Refresh token rotation secures session renewal."
- **Attack Scenario:** Attacker steals a refresh token. The legitimate user refreshes their token, generating a new pair. The attacker uses the stolen original refresh token to refresh again; the server accepts it and issues a new access token, allowing perpetual unauthorized access.
- **Blast Radius:** Stolen refresh tokens cannot be invalidated and survive rotation, granting ongoing account takeover.
- **Mitigation:**
  1. Store active refresh token `jti` in Redis or a `refresh_tokens` database table with expiration matching token lifetime.
  2. On `/api/auth/refresh`, verify that the submitted `jti` is active. Delete/mark it as consumed upon rotation.
  3. If an already-consumed `jti` is presented (replay attack), immediately reject with HTTP 401 and revoke all tokens belonging to that user/family.

### [HIGH] Challenge 3: Unhandled 500 Crash on Concurrent Duplicate Registration
- **Assumption Challenged:** "Duplicate registration errors are safely caught and return HTTP 400."
- **Attack Scenario:** Network latency or client double-click generates two concurrent `POST /api/auth/register` requests with the same email. Both pass the pre-check `SELECT`, and the second transaction triggers an unhandled `IntegrityError` on commit.
- **Blast Radius:** Server returns HTTP 500, corrupts error monitoring with false crash alarms, and leaks database driver exception traces.
- **Mitigation:**
  Wrap database operations in `register_user` with `try...except IntegrityError:` and return `HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email address already exists")`.

### [MEDIUM] Challenge 4: Missing Institution ID Existence Check
- **Assumption Challenged:** "Foreign keys in user registration are safely validated."
- **Attack Scenario:** Registration payload contains an arbitrary UUID for `institution_id`.
- **Blast Radius:** In PostgreSQL, committing a non-existent foreign key raises an unhandled `IntegrityError` (HTTP 500) rather than a 400 Bad Request.
- **Mitigation:**
  If `user_in.institution_id` is provided, verify its existence via `select(Institution).where(Institution.id == user_in.institution_id)` before persisting the user.

---

## 4. Stress Test Results

| Test Scenario | Target | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| Forged secret signature | `/api/rbac-test/admin-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Algorithm "none" attack | `/api/rbac-test/admin-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Expired access token | `/api/rbac-test/admin-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Tampered payload role claim | `/api/rbac-test/admin-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Non-existent user UUID in token | `/api/rbac-test/candidate-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Malformed UUID string in token | `/api/rbac-test/candidate-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Refresh token used as Bearer auth | `/api/rbac-test/admin-only` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| Access token used on `/refresh` | `/api/auth/refresh` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| **Refresh token replay after rotation** | `/api/auth/refresh` | **401 Unauthorized (Replay blocked)** | **200 OK (Accepted old token)** | **FAIL (CRITICAL)** |
| **Public registration as Admin role** | `/api/auth/register` | **Role forced to candidate / 403** | **201 Created as Admin** | **FAIL (CRITICAL)** |
| Candidate accessing Admin route | `/api/rbac-test/admin-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| Candidate accessing Proctor route | `/api/rbac-test/proctor-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| Candidate accessing Reviewer route | `/api/rbac-test/reviewer-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| Proctor accessing Admin route | `/api/rbac-test/admin-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| Reviewer accessing Admin route | `/api/rbac-test/admin-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| SQLi payloads in login email | `/api/auth/login` | 401 or 422 (rejected) | 401 / 422 | **PASS** |
| SQLi payload in login password | `/api/auth/login` | 401 Unauthorized | 401 Unauthorized | **PASS** |
| XSS payload in registration name | `/api/auth/register` | Stored as plain string | Stored as plain string | **PASS** |
| Multi-byte UTF-8 / RTL in name | `/api/auth/register` | Preserved correctly | Preserved correctly | **PASS** |
| Deactivated account access token | `/api/rbac-test/candidate-only` | 403 Forbidden | 403 Forbidden | **PASS** |
| Deactivated account refresh token | `/api/auth/refresh` | 403 Forbidden | 403 Forbidden | **PASS** |
| Deactivated account login | `/api/auth/login` | 403 Forbidden | 403 Forbidden | **PASS** |
| **Concurrent duplicate registration** | `/api/auth/register` | **400/409 (No 500 crash)** | **Unhandled IntegrityError (500)** | **FAIL (HIGH)** |

---

## 5. Caveats

- **External Live Database:** Tests execute against async SQLite in `conftest.py`. The foreign key constraint defect on `institution_id` manifests in PostgreSQL 16 (where foreign key checking is active by default) and produces a 500 crash unless caught.
- **Frontend Token Refresh:** The frontend `apiClient.ts` transparently handles 401 by refreshing tokens. Once refresh token revocation is implemented, the frontend client should be verified to handle 401 from an invalid/reused refresh token by clearing `localStorage` and redirecting to `/auth/login`.

---

## 6. Conclusion & Formal Verdict

### Formal Verdict: **REJECT**

Milestone 1 **CANNOT BE APPROVED** until the following three remediations are made:
1. **Fix Role Escalation:** Modify `register_user` in `backend/app/api/auth.py` so that public self-registration assigns `role = UserRole.CANDIDATE` unconditionally, ignoring or omitting client-supplied roles.
2. **Fix Refresh Token Rotation & Revocation:** Implement refresh token single-use invalidation / revocation tracking (in Redis or database) so that reusing a rotated refresh token fails with HTTP 401.
3. **Fix Concurrency Crash:** Catch `IntegrityError` during `register_user` and return HTTP 400 Bad Request instead of an unhandled HTTP 500 error.

---

## 7. Verification Method

To independently verify these findings:

1. Inspect the adversarial test file:
   `backend/tests/test_adversarial.py`
2. Run pytest with the adversarial suite:
   ```bash
   cd d:\vishwa47\v47Studio\ExamSentinel\backend
   pytest tests/test_adversarial.py -v
   ```
3. Observe test failures:
   - `tests/test_adversarial.py::test_public_registration_admin_role_escalation` -> FAILS (registers user as admin)
   - `tests/test_adversarial.py::test_refresh_token_replay_vulnerability` -> FAILS (permits replay of old refresh token)
   - `tests/test_adversarial.py::test_concurrent_duplicate_registration_race_condition` -> FAILS (500 crash on duplicate commit)
4. Invalidation Conditions:
   This REJECT verdict will be invalidated if and only if:
   - Public registration rejects or disallows `admin`/`proctor`/`reviewer` role assignment.
   - Replay of an already-used refresh token returns HTTP 401.
   - Concurrent duplicate registration returns clean HTTP 400/409 without unhandled 500 exceptions.
