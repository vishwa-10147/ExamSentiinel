import os
import re
from typing import Dict, Any

try:
    import google.generativeai as genai
except ImportError:  # Optional integration; the API remains usable without Gemini.
    genai = None

class AIGradingService:
    def __init__(self):
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None

    async def suggest_grade(self, question_text: str, rubric: Dict[str, Any], max_points: float, answer_text: str) -> Dict[str, Any]:
        """
        Calls Gemini to suggest a grade based on the rubric.
        Returns {"suggested_marks": float, "feedback": str}
        """
        if not self.model:
            # Fallback mock if no API key
            return {
                "suggested_marks": max_points * 0.8,
                "feedback": "[AI Mock] Good answer, but slightly incomplete."
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
            response = await self.model.generate_content_async(prompt)
            text = response.text
            
            score_match = re.search(r"^\\s*SCORE\\s*:\\s*([0-9]+(?:\\.[0-9]+)?)", text, re.MULTILINE | re.IGNORECASE)
            feedback_match = re.search(r"^\\s*FEEDBACK\\s*:\\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            
            score = float(score_match.group(1)) if score_match else 0.0
            feedback = feedback_match.group(1).strip() if feedback_match else "No feedback generated."
            
            # Clamp score
            score = max(0.0, min(float(score), max_points))
            
            return {
                "suggested_marks": score,
                "feedback": feedback
            }
        except Exception as e:
            return {
                "suggested_marks": 0.0,
                "feedback": "AI grading failed. Please grade this response manually."
            }

ai_grader = AIGradingService()
