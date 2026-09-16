"""
Tier 2 Boundary & Corner Cases: Authentication & Security Hardening
Tests boundary conditions, malformed tokens, injection payloads, extreme payload sizes, and Unicode.
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB1AuthSecurity(unittest.TestCase):
    """Tier 2 Boundary tests for Authentication and Security."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

    def test_01_expired_jwt_rejected_with_401(self):
        """Boundary: Expired JWT token is strictly rejected with 401 Unauthorized."""
        client = ExamSentinelClient()
        client.set_token("expired.jwt.token")
        res = client.get("/api/admin/users")
        self.assertEqual(res.status_code, 401, f"Expected 401 for expired token, got {res.status_code}")

    def test_02_malformed_jwt_rejected_with_401(self):
        """Boundary: Malformed JWT token strings are rejected with 401 Unauthorized."""
        malformed_tokens = [
            "malformed.jwt",
            "eyNotAValidHeader.eyNotAValidPayload.NoSig",
            "Bearer invalid",
            "!!!@@@###$$$%%%"
        ]
        for token in malformed_tokens:
            client = ExamSentinelClient()
            client.set_token(token)
            res = client.get("/api/admin/users")
            self.assertEqual(res.status_code, 401, f"Expected 401 for malformed token '{token}', got {res.status_code}")

    def test_03_sql_injection_payloads_in_auth_fields(self):
        """Boundary: SQL injection strings in login/registration fields must not bypass auth or leak 500s."""
        sqli_payloads = [
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT id, password, role FROM users--",
            "'; DROP TABLE users;--"
        ]
        for sqli in sqli_payloads:
            res = self.client.post("/api/auth/login", data={"email": sqli, "password": sqli})
            # Must safely reject with 401 or 422, never 500 Internal Server Error
            self.assertIn(res.status_code, [401, 422], f"SQLi payload '{sqli}' returned unexpected status {res.status_code}")

    def test_04_empty_and_whitespace_credentials(self):
        """Boundary: Empty strings or pure whitespace in credentials must be rejected with 422."""
        invalid_credentials = [
            {"email": "", "password": "Password123!"},
            {"email": "valid@test.com", "password": ""},
            {"email": "   ", "password": "   "},
            {"email": None, "password": None}
        ]
        for creds in invalid_credentials:
            res = self.client.post("/api/auth/register", data=creds)
            self.assertIn(res.status_code, [400, 422], f"Empty creds {creds} returned {res.status_code}")

    def test_05_oversized_payload_handling(self):
        """Boundary: Excessively oversized email or password inputs (>64KB) must not crash the service."""
        oversized_email = "a" * 70000 + "@example.com"
        oversized_pwd = "b" * 70000
        res = self.client.post("/api/auth/login", data={"email": oversized_email, "password": oversized_pwd})
        self.assertIn(res.status_code, [400, 401, 413, 422], f"Oversized payload returned unexpected {res.status_code}")

    def test_06_unicode_passwords_and_special_characters(self):
        """Boundary: UTF-8 multilingual, emoji, and special character passwords must be preserved and matched."""
        email = f"unicode_{self.unique_id}@examsentinel.test"
        unicode_password = "🔑P@sswørd_日本語_Русский_مرحبا_123!🚀"
        reg_res = self.client.post("/api/auth/register", data={
            "email": email,
            "password": unicode_password,
            "role": "candidate"
        })
        self.assertEqual(reg_res.status_code, 201)

        # Login with exact Unicode password must succeed
        login_res = self.client.post("/api/auth/login", data={"email": email, "password": unicode_password})
        self.assertEqual(login_res.status_code, 200, "Login with valid Unicode password failed")

        # Login with subtle variation must fail (401)
        subtle_fail = self.client.post("/api/auth/login", data={"email": email, "password": unicode_password[:-1]})
        self.assertEqual(subtle_fail.status_code, 401)


if __name__ == "__main__":
    unittest.main()
