"""
ExamSentinel E2E Test Configuration
Centralizes endpoints, timeouts, and credentials for opaque-box testing.
"""
import os

# Target Endpoints
BASE_URL = os.getenv("EXAMSENTINEL_BASE_URL", "http://localhost:8000")
WS_URL = os.getenv("EXAMSENTINEL_WS_URL", "ws://localhost:8000")
FRONTEND_URL = os.getenv("EXAMSENTINEL_FRONTEND_URL", "http://localhost:3000")

# Timeouts (in seconds)
DEFAULT_TIMEOUT = float(os.getenv("EXAMSENTINEL_TIMEOUT", "10.0"))
SHORT_TIMEOUT = 3.0
LONG_TIMEOUT = 30.0

# Execution Modes
# When LIVE_BACKEND is False or unreachable, tests verify contract specifications & mock responses
MOCK_HARNESS = os.getenv("EXAMSENTINEL_MOCK_HARNESS", "false").lower() in ("true", "1", "yes")

# Standard Test Credentials
ADMIN_USER = {
    "email": "admin@examsentinel.test",
    "password": "AdminSecurePassword123!",
    "full_name": "Test System Administrator",
    "role": "admin",
}

PROCTOR_USER = {
    "email": "proctor@examsentinel.test",
    "password": "ProctorSecurePassword123!",
    "full_name": "Test Chief Proctor",
    "role": "proctor",
}

REVIEWER_USER_1 = {
    "email": "reviewer1@examsentinel.test",
    "password": "ReviewerSecurePassword123!",
    "full_name": "Primary Integrity Reviewer",
    "role": "reviewer",
}

REVIEWER_USER_2 = {
    "email": "reviewer2@examsentinel.test",
    "password": "ReviewerSecurePassword123!",
    "full_name": "Appeals Secondary Reviewer",
    "role": "reviewer",
}

CANDIDATE_USER = {
    "email": "candidate@examsentinel.test",
    "password": "CandidateSecurePassword123!",
    "full_name": "Test Exam Candidate",
    "role": "candidate",
}
