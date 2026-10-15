"""Advisory grade suggestions for written answers, from Google Gemini.

A suggestion only: staff see it next to the answer and decide the grade. Without
``GEMINI_API_KEY`` the service says so and nothing leaves the server.

Calls the Gemini REST API directly with httpx (the deprecated ``google-generativeai`` SDK
added ~150 MB of Google API and gRPC clients to the image for this one request).
"""

import os
import re
from typing import Any, Dict, Optional

import httpx

from app.core.logging import logger

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 30.0


class AIGradingService:
    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._transport = transport  # tests inject a mock transport

    @property
    def model(self) -> Optional[str]:
        """The configured model, or None when AI grading is not configured."""
        return self.model_name if self.api_key else None

    async def _generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
            response = await client.post(
                GEMINI_URL.format(model=self.model_name),
                headers={"x-goog-api-key": self.api_key},  # in a header, never in the URL (logs)
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        response.raise_for_status()
        data = response.json()
        return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])

    async def suggest_grade(self, question_text: str, rubric: Dict[str, Any], max_points: float, answer_text: str) -> Dict[str, Any]:
        """Returns {"suggested_marks": float, "feedback": str}."""
        if not self.model:
            return {
                "suggested_marks": 0.0,
                "feedback": "AI grading is not configured. Grade this response manually."
            }

        prompt = f"""
You are an expert professor grading an exam.
Question: {question_text}
Max Points: {max_points}
Rubric: {rubric}

Student's Answer:
{answer_text}

Analyze the student's answer against the rubric.
Provide a suggested numerical score (between 0 and {max_points}) and brief feedback for the student.
Format your output exactly as:
SCORE: <number>
FEEDBACK: <text>
"""
        try:
            text = await self._generate(prompt)
            score_match = re.search(r"^\s*SCORE\s*:\s*([0-9]+(?:\.[0-9]+)?)", text, re.MULTILINE | re.IGNORECASE)
            feedback_match = re.search(r"^\s*FEEDBACK\s*:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.0
            feedback = feedback_match.group(1).strip() if feedback_match else "No feedback generated."
            return {"suggested_marks": max(0.0, min(score, max_points)), "feedback": feedback}
        except Exception as exc:
            logger.warning("ai_grading.failed", error=type(exc).__name__)
            return {
                "suggested_marks": 0.0,
                "feedback": "AI grading failed. Please grade this response manually."
            }


ai_grader = AIGradingService()
