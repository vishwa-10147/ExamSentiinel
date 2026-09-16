"""
Tier 2 Boundary & Corner Cases: Adaptive IRT Extremes & Cold Start
Tests extreme ability levels (theta +/- 5.0), cold-start empty history, and standard error bounds.
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB5AdaptiveExtremes(unittest.TestCase):
    """Tier 2 Boundary tests for 2PL IRT Model Boundaries."""

    def setUp(self):
        self.client = ExamSentinelClient()

    def test_01_cold_start_zero_questions_answered(self):
        """Boundary: Cold start with 0 answered questions returns valid initial item and baseline SE."""
        payload = {
            "current_theta": 0.0,
            "answered_questions": []
        }
        res = self.client.post("/api/adaptive/next-question", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("question_id", data)
        self.assertGreater(data.get("standard_error", 0), 0.5)

    def test_02_extreme_high_ability_boundary(self):
        """Boundary: Extreme high ability (theta = +5.0) selects appropriately difficult item."""
        payload = {
            "current_theta": 5.0,
            "answered_questions": [{"question_id": str(uuid.uuid4()), "difficulty_b": 4.0, "is_correct": True} for _ in range(10)]
        }
        res = self.client.post("/api/adaptive/next-question", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data.get("difficulty_b", 0), 2.0)

    def test_03_extreme_low_ability_boundary(self):
        """Boundary: Extreme low ability (theta = -5.0) selects appropriately low difficulty item."""
        payload = {
            "current_theta": -5.0,
            "answered_questions": [{"question_id": str(uuid.uuid4()), "difficulty_b": -4.0, "is_correct": False} for _ in range(10)]
        }
        res = self.client.post("/api/adaptive/next-question", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertLess(data.get("difficulty_b", 0), 0.0)


if __name__ == "__main__":
    unittest.main()
