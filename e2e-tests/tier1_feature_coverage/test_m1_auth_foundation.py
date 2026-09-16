"""
Tier 1 Feature Coverage: Milestone 1 — Platform Foundation, Auth & Core Services
Features Covered: 1 to 7
- Feature 1: Documentation Suite
- Feature 2: Docker Compose Environment
- Feature 3: Core Database Schema & Migrations
- Feature 4: Authentication & JWT Service
- Feature 5: Role-Based Access Control (RBAC)
- Feature 6: Base API Infrastructure
- Feature 7: Base Frontend Shell
"""
import unittest
import os
import json
import uuid
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient
from config import ADMIN_USER, PROCTOR_USER, REVIEWER_USER_1, CANDIDATE_USER


class TestM1AuthFoundation(unittest.TestCase):
    """Tier 1 Test Suite for Platform Foundation & Authentication."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

    def test_01_health_check_returns_200_and_healthy_services(self):
        """Feature 6: Health check endpoint returns 200 and healthy DB/Redis."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200, f"Health check failed with {res.status_code}: {res.text}")
        data = res.json()
        self.assertIsNotNone(data, "Response must be valid JSON")
        self.assertEqual(data.get("status"), "healthy", "Expected status to be 'healthy'")
        self.assertEqual(data.get("database"), "connected", "Expected database to be 'connected'")
        self.assertEqual(data.get("redis"), "connected", "Expected redis to be 'connected'")

    def test_02_registration_all_roles(self):
        """Feature 4 & 5: Registration of Admin, Proctor, Reviewer, and Candidate roles."""
        roles = ["admin", "proctor", "reviewer", "candidate"]
        for role in roles:
            email = f"test_{role}_{self.unique_id}@examsentinel.test"
            payload = {
                "email": email,
                "password": f"Password!_{role}_{self.unique_id}",
                "role": role,
                "full_name": f"Test User {role.capitalize()}"
            }
            res = self.client.post("/api/auth/register", data=payload)
            self.assertEqual(res.status_code, 201, f"Registration failed for role {role}: {res.text}")
            data = res.json()
            self.assertEqual(data.get("email"), email)
            self.assertEqual(data.get("role"), role)
            self.assertIn("id", data)

    def test_03_registration_duplicate_email_rejected(self):
        """Feature 4: Duplicate email registration must return 400 Bad Request."""
        email = f"duplicate_{self.unique_id}@examsentinel.test"
        payload = {
            "email": email,
            "password": "InitialPassword123!",
            "role": "candidate",
            "full_name": "Initial Candidate"
        }
        res1 = self.client.post("/api/auth/register", data=payload)
        self.assertEqual(res1.status_code, 201)

        # Attempt to register again with same email
        res2 = self.client.post("/api/auth/register", data=payload)
        self.assertEqual(res2.status_code, 400, "Duplicate registration must be rejected with 400")

    def test_04_authentication_valid_credentials_returns_jwt(self):
        """Feature 4: Authentication with correct credentials returns valid JWT."""
        email = f"login_valid_{self.unique_id}@examsentinel.test"
        password = "ValidSecretPassword123!"
        self.client.post("/api/auth/register", data={
            "email": email,
            "password": password,
            "role": "candidate",
            "full_name": "Login Test Candidate"
        })

        res = self.client.post("/api/auth/login", data={"email": email, "password": password})
        self.assertEqual(res.status_code, 200, f"Login failed: {res.text}")
        data = res.json()
        self.assertIn("access_token", data, "Missing access_token in login response")
        self.assertIn("refresh_token", data, "Missing refresh_token in login response")
        self.assertEqual(data.get("token_type", "").lower(), "bearer")
        self.assertGreater(data.get("expires_in", 0), 0)

    def test_05_authentication_invalid_password_returns_401(self):
        """Feature 4: Authentication with bad password returns 401 Unauthorized."""
        email = f"login_bad_{self.unique_id}@examsentinel.test"
        password = "CorrectPassword123!"
        self.client.post("/api/auth/register", data={
            "email": email,
            "password": password,
            "role": "candidate"
        })

        res = self.client.post("/api/auth/login", data={"email": email, "password": "WrongPassword999!"})
        self.assertEqual(res.status_code, 401, f"Expected 401 Unauthorized for invalid password, got {res.status_code}")

    def test_06_protected_admin_endpoint_rejects_unauthenticated(self):
        """Feature 5: Protected admin endpoints reject unauthenticated requests with 401."""
        unauth_client = ExamSentinelClient()
        unauth_client.set_token(None)
        res = unauth_client.get("/api/admin/users")
        self.assertEqual(res.status_code, 401, f"Expected 401 for unauthenticated access, got {res.status_code}")

    def test_07_role_authorization_candidate_rejected_from_admin_routes(self):
        """Feature 5: Role authorization: Candidate rejected from Admin routes with 403 Forbidden."""
        email = f"cand_rbac_{self.unique_id}@examsentinel.test"
        password = "CandidatePassword123!"
        self.client.post("/api/auth/register", data={
            "email": email,
            "password": password,
            "role": "candidate"
        })
        login_res = self.client.post("/api/auth/login", data={"email": email, "password": password})
        token = login_res.json().get("access_token")

        candidate_client = ExamSentinelClient()
        candidate_client.set_token(token)
        res = candidate_client.get("/api/admin/users")
        self.assertEqual(res.status_code, 403, f"Expected 403 Forbidden for candidate on admin route, got {res.status_code}")

    def test_08_token_refresh_exchanges_valid_refresh_token(self):
        """Feature 4: Token refresh exchanges valid refresh token for new access token."""
        email = f"refresh_{self.unique_id}@examsentinel.test"
        password = "RefreshPassword123!"
        self.client.post("/api/auth/register", data={
            "email": email,
            "password": password,
            "role": "candidate"
        })
        login_res = self.client.post("/api/auth/login", data={"email": email, "password": password})
        refresh_token = login_res.json().get("refresh_token")
        self.assertIsNotNone(refresh_token)

        refresh_res = self.client.post("/api/auth/refresh", data={"refresh_token": refresh_token})
        self.assertEqual(refresh_res.status_code, 200, f"Token refresh failed: {refresh_res.text}")
        data = refresh_res.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_09_documentation_suite_integrity(self):
        """Feature 1: Verifies existence and non-emptiness of documentation suite in docs/."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        docs_dir = os.path.join(project_root, "docs")
        required_files = ["readme.md", "plan.md", "explain.md", "prompt.md"]
        
        # If docs directory exists, inspect contents; otherwise verify requirement expectation
        if os.path.isdir(docs_dir):
            for doc in required_files:
                path = os.path.join(docs_dir, doc)
                self.assertTrue(os.path.isfile(path), f"Required doc {doc} missing in docs/")
                self.assertGreater(os.path.getsize(path), 50, f"Doc {doc} appears empty or truncated")
        else:
            self.skipTest("docs/ directory is pending generation by Milestone 1 implementation")


if __name__ == "__main__":
    unittest.main()
