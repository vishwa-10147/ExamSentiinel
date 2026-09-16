"""
Tier 2 Boundary & Corner Cases: Sandboxed Code Execution & Malicious Payloads
Tests infinite loops, memory bombs, socket access attempts, and unsupported runtimes.
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB4SandboxAttacks(unittest.TestCase):
    """Tier 2 Boundary tests for Isolated Code Sandbox Execution."""

    def setUp(self):
        self.client = ExamSentinelClient()

    def test_01_infinite_loop_timeout_containment(self):
        """Boundary: Code with infinite loop triggers TIME_LIMIT_EXCEEDED without hanging runner."""
        payload = {
            "language": "python",
            "source_code": "while True:\n    pass",
            "time_limit_sec": 1.0
        }
        res = self.client.post("/api/code/submit", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("status"), ["TIME_LIMIT_EXCEEDED", "TIMEOUT"])

    def test_02_network_socket_attempt_containment(self):
        """Boundary: Code attempting outbound socket connection is blocked (--net=none)."""
        payload = {
            "language": "python",
            "source_code": "import socket\ns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\ns.connect(('8.8.8.8', 53))",
            "time_limit_sec": 2.0
        }
        res = self.client.post("/api/code/submit", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("status"), ["RUNTIME_ERROR", "PERMISSION_DENIED"])

    def test_03_unsupported_language_rejected(self):
        """Boundary: Submission with unsupported language (e.g. 'cobol', 'brainfuck') returns 422."""
        payload = {
            "language": "unsupported_xyz",
            "source_code": "PRINT 'HELLO'",
            "time_limit_sec": 2.0
        }
        res = self.client.post("/api/code/submit", data=payload)
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
