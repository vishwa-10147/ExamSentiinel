import os
import json
import httpx
from typing import List, Dict, Any
from app.core.logging import logger

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def generate_questions_from_syllabus(self, syllabus_text: str, question_count: int) -> List[Dict[str, Any]]:
        """
        Takes a raw syllabus/topic list and asks the LLM to generate `question_count` 
        multiple-choice questions formatted as JSON.
        """
        if not self.api_key:
            raise RuntimeError("AI question generation is not configured. Set OPENAI_API_KEY to enable it.")

        prompt = (
            f"Create exactly {question_count} multiple-choice questions from this syllabus:\n{syllabus_text}\n"
            "Return only a JSON object with a 'questions' array. Each item must contain:\n"
            "- title: short question title (e.g. 'Binary Search Trees')\n"
            "- text: the full question statement\n"
            "- points: numerical points (e.g. 1.0)\n"
            "- options: array of objects like [{\"id\": \"A\", \"text\": \"Option A\"}, {\"id\": \"B\", \"text\": \"Option B\"}, {\"id\": \"C\", \"text\": \"Option C\"}, {\"id\": \"D\", \"text\": \"Option D\"}]\n"
            "- correct_answer: option string id corresponding to the correct option (e.g. \"A\")\n"
        )
        content = await self._chat(prompt)
        parsed = json.loads(content)
        questions = parsed.get("questions") if isinstance(parsed, dict) else parsed
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("AI returned an invalid question set")
        return questions

    async def grade_essay(self, question_text: str, student_answer: str, rubric: str) -> Dict[str, Any]:
        """
        Takes the essay prompt, the student's answer, and an optional rubric, 
        and returns a score and feedback string.
        """
        if not self.api_key:
            raise RuntimeError("AI essay grading is not configured. Set OPENAI_API_KEY to enable it.")

        content = await self._chat(
            "Grade this answer and return only JSON with numeric score from 0 to 100 and feedback string.\n"
            f"Question: {question_text}\nRubric: {rubric}\nAnswer: {student_answer}"
        )
        result = json.loads(content)
        return {"score": max(0.0, min(float(result["score"]), 100.0)), "feedback": str(result["feedback"])}

    async def _chat(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]

ai_service = AIService()
