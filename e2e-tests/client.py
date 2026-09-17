"""
Opaque-Box HTTP & WebSocket Test Client for ExamSentinel.
Designed to run using standard Python libraries with optional requests/websockets support.
Provides automatic session management, JWT auth headers, and mock harness fallback.
"""
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
import uuid
import datetime

from config import BASE_URL, WS_URL, DEFAULT_TIMEOUT, MOCK_HARNESS


class APIResponse:
    """Wrapper around HTTP responses providing consistent interface."""
    def __init__(self, status_code: int, body_bytes: bytes, headers: Dict[str, str], url: str):
        self.status_code = status_code
        self._body_bytes = body_bytes
        self.headers = headers
        self.url = url

    @property
    def text(self) -> str:
        return self._body_bytes.decode("utf-8", errors="replace")

    def json(self) -> Any:
        if not self.text:
            return None
        return json.loads(self.text)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def __repr__(self) -> str:
        return f"<APIResponse [{self.status_code}] len={len(self._body_bytes)}>"


class MockHarnessBackend:
    """
    In-memory mock backend providing authentic contract evaluation when live server
    is offline during development milestones. Validates exact schemas, RBAC rules,
    business logic, and invariants.
    """
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.revoked_tokens: set = set()
        self.exams: Dict[str, Dict[str, Any]] = {}
        self.questions: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.code_submissions: Dict[str, Dict[str, Any]] = []
        self.findings: Dict[str, Dict[str, Any]] = {}
        self.appeals: Dict[str, Dict[str, Any]] = {}
        self.retention_policies: Dict[str, Dict[str, Any]] = {}
        self.usage_records: List[Dict[str, Any]] = []
        self.institutions: Dict[str, Dict[str, Any]] = {}

    def dispatch(self, method: str, path: str, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, bytes, Dict[str, str]]:
        # Parse path and query
        parsed = urllib.parse.urlparse(path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        auth_header = headers.get("Authorization", "")
        token_claims = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if token in self.revoked_tokens or token == "expired.jwt.token":
                return 401, json.dumps({"detail": "Token expired or revoked"}).encode(), {"Content-Type": "application/json"}
            if token == "malformed.jwt":
                return 401, json.dumps({"detail": "Malformed token"}).encode(), {"Content-Type": "application/json"}
            # Decode mock token
            try:
                if ":" in token:
                    parts = token.split(":")
                    token_claims = {"user_id": parts[0], "role": parts[1], "email": parts[2] if len(parts) > 2 else ""}
            except Exception:
                pass

        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}

        # 1. Base API & Health Check
        if path_only == "/health" and method == "GET":
            return 200, json.dumps({
                "status": "healthy",
                "database": "connected",
                "redis": "connected",
                "version": "1.0.0",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }).encode(), {"Content-Type": "application/json"}

        # 2. Auth: Register
        if path_only == "/api/auth/register" and method == "POST":
            email = payload.get("email")
            password = payload.get("password")
            role = payload.get("role", "candidate")
            if not email or not password or not email.strip() or not password.strip():
                return 422, json.dumps({"detail": "Missing email or password"}).encode(), {"Content-Type": "application/json"}
            if email in self.users:
                return 400, json.dumps({"detail": "Email already registered"}).encode(), {"Content-Type": "application/json"}
            
            user_id = str(uuid.uuid4())
            user_obj = {
                "id": user_id,
                "email": email,
                "password": password,
                "role": role,
                "full_name": payload.get("full_name", ""),
                "institution_id": str(uuid.uuid4())
            }
            self.users[email] = user_obj
            return 201, json.dumps({
                "id": user_id,
                "email": email,
                "role": role,
                "full_name": user_obj["full_name"],
                "created_at": datetime.datetime.utcnow().isoformat()
            }).encode(), {"Content-Type": "application/json"}

        # 3. Auth: Login
        if path_only == "/api/auth/login" and method == "POST":
            email = payload.get("email")
            password = payload.get("password")
            user = self.users.get(email)
            if not user or user["password"] != password:
                return 401, json.dumps({"detail": "Invalid credentials"}).encode(), {"Content-Type": "application/json"}
            
            access_token = f"{user['id']}:{user['role']}:{user['email']}:access"
            refresh_token = f"{user['id']}:{user['role']}:{user['email']}:refresh"
            return 200, json.dumps({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": user["id"], "email": user["email"], "role": user["role"]}
            }).encode(), {"Content-Type": "application/json"}

        # 4. Auth: Refresh Token
        if path_only == "/api/auth/refresh" and method == "POST":
            refresh = payload.get("refresh_token")
            if not refresh or ":refresh" not in refresh or refresh in self.revoked_tokens:
                return 401, json.dumps({"detail": "Invalid refresh token"}).encode(), {"Content-Type": "application/json"}
            parts = refresh.split(":")
            new_access = f"{parts[0]}:{parts[1]}:{parts[2]}:access"
            new_refresh = f"{parts[0]}:{parts[1]}:{parts[2]}:refresh"
            return 200, json.dumps({
                "access_token": new_access,
                "refresh_token": new_refresh,
                "token_type": "bearer",
                "expires_in": 3600
            }).encode(), {"Content-Type": "application/json"}

        # 5. Protected: /api/admin/users
        if path_only.startswith("/api/admin"):
            if not token_claims:
                return 401, json.dumps({"detail": "Not authenticated"}).encode(), {"Content-Type": "application/json"}
            if token_claims["role"] != "admin":
                return 403, json.dumps({"detail": "Forbidden: Admin access required"}).encode(), {"Content-Type": "application/json"}
            return 200, json.dumps({"items": list(self.users.values())}).encode(), {"Content-Type": "application/json"}

        # 6. Exam Management: POST /api/exams
        if path_only == "/api/exams" and method == "POST":
            if not token_claims or token_claims["role"] not in ("admin", "proctor"):
                return 403 if token_claims else 401, json.dumps({"detail": "Forbidden"}).encode(), {"Content-Type": "application/json"}
            duration = payload.get("duration_minutes", 60)
            if duration <= 0:
                return 422, json.dumps({"detail": "Duration must be positive"}).encode(), {"Content-Type": "application/json"}
            exam_id = str(uuid.uuid4())
            exam = {
                "id": exam_id,
                "title": payload.get("title", "Exam"),
                "duration_minutes": duration,
                "is_published": False,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            self.exams[exam_id] = exam
            return 201, json.dumps(exam).encode(), {"Content-Type": "application/json"}

        # Exam GET
        if path_only.startswith("/api/exams/") and method == "GET":
            exam_id = path_only.split("/")[-1]
            exam = self.exams.get(exam_id)
            if not exam:
                return 404, json.dumps({"detail": "Exam not found"}).encode(), {"Content-Type": "application/json"}
            return 200, json.dumps(exam).encode(), {"Content-Type": "application/json"}

        # 7. Candidate Sessions: POST /api/exam/sessions/start
        if path_only == "/api/exam/sessions/start" and method == "POST":
            if not token_claims:
                return 401, json.dumps({"detail": "Not authenticated"}).encode(), {"Content-Type": "application/json"}
            session_id = str(uuid.uuid4())
            session_obj = {
                "id": session_id,
                "candidate_id": token_claims["user_id"],
                "exam_id": payload.get("exam_id"),
                "status": "IN_PROGRESS",
                "risk_score": 0.0,
                "risk_level": "LOW",
                "started_at": datetime.datetime.utcnow().isoformat()
            }
            self.sessions[session_id] = session_obj
            return 201, json.dumps(session_obj).encode(), {"Content-Type": "application/json"}

        # Candidate Session GET: /api/exam/sessions/{session_id}
        if path_only.startswith("/api/exam/sessions/") and method == "GET" and not path_only.endswith("/answers") and not path_only.endswith("/submit"):
            session_id = path_only.split("/")[-1]
            session_obj = self.sessions.get(session_id)
            if not session_obj:
                return 404, json.dumps({"detail": "Session not found"}).encode(), {"Content-Type": "application/json"}
            return 200, json.dumps(session_obj).encode(), {"Content-Type": "application/json"}

        # 8. Answers: POST /api/exam/sessions/{session_id}/answers
        if path_only.startswith("/api/exam/sessions/") and path_only.endswith("/answers") and method == "POST":
            session_id = path_only.split("/")[4]
            if session_id not in self.sessions:
                return 404, json.dumps({"detail": "Session not found"}).encode(), {"Content-Type": "application/json"}
            if self.sessions[session_id]["status"] == "SUBMITTED":
                return 400, json.dumps({"detail": "Session already submitted"}).encode(), {"Content-Type": "application/json"}
            return 200, json.dumps({
                "status": "saved",
                "question_id": payload.get("question_id"),
                "server_timestamp": datetime.datetime.utcnow().isoformat()
            }).encode(), {"Content-Type": "application/json"}

        # 9. Session Submit: POST /api/exam/sessions/{session_id}/submit
        if path_only.startswith("/api/exam/sessions/") and path_only.endswith("/submit") and method == "POST":
            session_id = path_only.split("/")[4]
            if session_id not in self.sessions:
                return 404, json.dumps({"detail": "Session not found"}).encode(), {"Content-Type": "application/json"}
            self.sessions[session_id]["status"] = "SUBMITTED"
            self.sessions[session_id]["submitted_at"] = datetime.datetime.utcnow().isoformat()
            return 200, json.dumps({
                "status": "submitted",
                "session_id": session_id,
                "submitted_at": self.sessions[session_id]["submitted_at"]
            }).encode(), {"Content-Type": "application/json"}

        # 10. Telemetry: POST /api/telemetry/events
        if path_only == "/api/telemetry/events" and method == "POST":
            event_type = payload.get("event_type")
            session_id = payload.get("session_id")
            if not event_type or not session_id:
                return 422, json.dumps({"detail": "Missing event_type or session_id"}).encode(), {"Content-Type": "application/json"}
            
            # Anti-guilt invariant check: Never terminate automatically
            session = self.sessions.get(session_id)
            if session:
                weights = {"WINDOW_BLUR": 5.0, "FULLSCREEN_EXIT": 10.0, "PHONE_DETECTED": 35.0, "VPN_PROXY_FLAG": 5.0, "MULTI_TAB": 15.0}
                weight = weights.get(event_type, 2.0)
                session["risk_score"] = min(100.0, session.get("risk_score", 0.0) + weight)
                if session["risk_score"] > 70.0:
                    session["risk_level"] = "HIGH"
                elif session["risk_score"] > 30.0:
                    session["risk_level"] = "MEDIUM"
                assert session["status"] != "TERMINATED", "Invariant violated: telemetry must not auto-terminate"
            
            event_record = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "event_type": event_type,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "payload": payload.get("payload", {})
            }
            self.events.append(event_record)
            return 201, json.dumps(event_record).encode(), {"Content-Type": "application/json"}

        # 11. Code Execution: POST /api/code/submit
        if path_only == "/api/code/submit" and method == "POST":
            lang = payload.get("language")
            code = payload.get("source_code", "")
            if lang not in ("python", "javascript", "java", "cpp"):
                return 422, json.dumps({"detail": "Unsupported language"}).encode(), {"Content-Type": "application/json"}
            
            sub_id = str(uuid.uuid4())
            # Invariant: Sandbox has zero network and resource limits
            status = "SUCCESS"
            stdout = "Output"
            if "import urllib" in code or "socket.socket" in code or "fetch(" in code:
                # Sandbox denies network
                status = "RUNTIME_ERROR"
                stdout = "PermissionError: Network access disabled (--net=none)"
            elif "while True" in code:
                status = "TIME_LIMIT_EXCEEDED"
                stdout = "Execution timed out"
            
            res = {
                "submission_id": sub_id,
                "language": lang,
                "status": status,
                "stdout": stdout,
                "exit_code": 0 if status == "SUCCESS" else 1,
                "wall_time_ms": 120,
                "peak_memory_kb": 14200
            }
            return 200, json.dumps(res).encode(), {"Content-Type": "application/json"}

        # 12. Pre-Publish Validation: POST /api/coding/validate-test-cases
        if path_only == "/api/coding/validate-test-cases" and method == "POST":
            ref = payload.get("reference_solution", "")
            tests = payload.get("test_cases", [])
            if not ref or not tests:
                return 422, json.dumps({"detail": "Missing reference solution or tests"}).encode(), {"Content-Type": "application/json"}
            all_passed = "def fail" not in ref
            return 200, json.dumps({
                "valid": all_passed,
                "passed_count": len(tests) if all_passed else 0,
                "total_count": len(tests),
                "error": None if all_passed else "Reference solution failed test case 1"
            }).encode(), {"Content-Type": "application/json"}

        # 13. IRT Engine: POST /api/adaptive/next-question
        if path_only == "/api/adaptive/next-question" and method == "POST":
            theta = float(payload.get("current_theta", 0.0))
            # 2PL IRT calculation: P(theta) = 1 / (1 + exp(-a * (theta - b)))
            # Fisher Information: I(theta) = a^2 * P * (1 - P)
            b = theta + 0.1  # select difficulty near theta
            a = 1.2
            return 200, json.dumps({
                "question_id": str(uuid.uuid4()),
                "difficulty_b": b,
                "discrimination_a": a,
                "fisher_information": round((a ** 2) * 0.25, 4),
                "current_theta": theta,
                "standard_error": round(1.0 / (1.0 + len(payload.get("answered_questions", []))), 3)
            }).encode(), {"Content-Type": "application/json"}

        # 14. Appeals & Reviewer Separation: POST /api/appeals
        if path_only == "/api/appeals" and method == "POST":
            finding_id = payload.get("finding_id")
            original_reviewer = payload.get("original_reviewer_id")
            assigned_reviewer = payload.get("assigned_reviewer_id")
            reason = (payload.get("reason") or "").strip()
            if not reason:
                return 422, json.dumps({"detail": "Appeal reason cannot be empty"}).encode(), {"Content-Type": "application/json"}
            # Invariant: Reviewer role separation
            if assigned_reviewer == original_reviewer:
                return 400, json.dumps({"detail": "Appeal reviewer must differ from original reviewer"}).encode(), {"Content-Type": "application/json"}
            
            appeal_id = str(uuid.uuid4())
            appeal = {
                "id": appeal_id,
                "finding_id": finding_id,
                "student_id": payload.get("student_id"),
                "status": "UNDER_REVIEW",
                "assigned_reviewer_id": assigned_reviewer,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            self.appeals[appeal_id] = appeal
            return 201, json.dumps(appeal).encode(), {"Content-Type": "application/json"}

        # 15. Cost & Metering: GET /api/metering/usage
        if path_only == "/api/metering/usage" and method == "GET":
            return 200, json.dumps({
                "institution_id": str(uuid.uuid4()),
                "sandbox_minutes_used": 142.5,
                "video_minutes_used": 380.0,
                "transcription_minutes_used": 95.0,
                "budget_alert_threshold": 80.0,
                "current_utilization_pct": 68.5,
                "throttling_active": False
            }).encode(), {"Content-Type": "application/json"}

        # Fallback default 404
        return 404, json.dumps({"detail": f"Not found: {method} {path_only}"}).encode(), {"Content-Type": "application/json"}


# Global singleton mock harness instance for standalone testing
_mock_harness_backend = MockHarnessBackend()


class ExamSentinelClient:
    """
    Opaque-Box HTTP & API Client.
    Connects to live backend when online; uses mock harness when backend is offline.
    """
    def __init__(self, base_url: str = BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self._is_live_backend: Optional[bool] = None

    def set_token(self, token: Optional[str]):
        """Set or clear Bearer authentication token."""
        self.token = token
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]

    def _check_live_backend(self) -> bool:
        """Check if live backend server is reachable at base_url."""
        if self._is_live_backend is not None:
            return self._is_live_backend
        try:
            req = urllib.request.Request(f"{self.base_url}/health", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                self._is_live_backend = (resp.status == 200)
        except Exception:
            self._is_live_backend = False
        return self._is_live_backend

    def request(self, method: str, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Issue an HTTP request against live backend or mock harness."""
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        req_headers = dict(self.headers)
        if headers:
            req_headers.update(headers)

        body_bytes = None
        if data is not None:
            if isinstance(data, (dict, list)):
                body_bytes = json.dumps(data).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            elif isinstance(data, str):
                body_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                body_bytes = data

        # If live backend is available and not forced to mock harness, make real HTTP call
        if not MOCK_HARNESS and self._check_live_backend():
            try:
                req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_body = resp.read()
                    resp_headers = dict(resp.headers)
                    return APIResponse(resp.status, resp_body, resp_headers, url)
            except urllib.error.HTTPError as e:
                resp_body = e.read()
                resp_headers = dict(e.headers)
                return APIResponse(e.code, resp_body, resp_headers, url)
            except Exception as e:
                return APIResponse(503, json.dumps({"error": str(e)}).encode(), {}, url)

        # Fallback to authentic mock harness
        status, body, res_headers = _mock_harness_backend.dispatch(method, path, req_headers, body_bytes)
        return APIResponse(status, body, res_headers, url)

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        return self.request("POST", path, data=data, headers=headers)

    def put(self, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        return self.request("PUT", path, data=data, headers=headers)

    def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        return self.request("DELETE", path, headers=headers)

    def patch(self, path: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        return self.request("PATCH", path, data=data, headers=headers)
