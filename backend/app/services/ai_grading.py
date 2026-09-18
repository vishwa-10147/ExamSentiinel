import google.generativeai as genai
import os
from typing import Dict, Any

class AIGradingService:
    def __init__(self):
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
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
            # Note: For async, we should ideally use generate_content_async but wrapping sync for now
            response = self.model.generate_content(prompt)
            text = response.text
            
            score_line = [line for line in text.split('\\n') if line.startswith("SCORE:")]
            feedback_line = [line for line in text.split('\\n') if line.startswith("FEEDBACK:")]
            
            score = float(score_line[0].split("SCORE:")[1].strip()) if score_line else 0.0
            feedback = feedback_line[0].split("FEEDBACK:")[1].strip() if feedback_line else "No feedback generated."
            
            # Clamp score
            score = max(0.0, min(float(score), max_points))
            
            return {
                "suggested_marks": score,
                "feedback": feedback
            }
        except Exception as e:
            return {
                "suggested_marks": 0.0,
                "feedback": f"AI Grading Failed: {str(e)}"
            }

ai_grader = AIGradingService()
