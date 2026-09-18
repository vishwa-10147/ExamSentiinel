import sys

with open(r'backend\app\services\grading_service.py', 'r') as f:
    text = f.read()

import_ai = '''from app.services.sandbox_service import sandbox_service
from app.services.ai_service import ai_service'''

text = text.replace('from app.services.sandbox_service import sandbox_service', import_ai)

old_essay = '''            elif question.type == QuestionType.ESSAY:
                # Currently manual grading
                pass'''

new_essay = '''            elif question.type == QuestionType.ESSAY:
                # AI Grading for Essay
                essay_text = response.response_data.get("text", "")
                if essay_text:
                    rubric = question.data.get("rubric", "Grade based on general comprehension and correctness.")
                    ai_result = await ai_service.grade_essay(
                        question_text=question.text,
                        student_answer=essay_text,
                        rubric=rubric
                    )
                    # Normalize AI score to question points
                    marks = (ai_result["score"] / 100.0) * float(question.points)
                    is_correct = marks > (float(question.points) * 0.5)
                    response.feedback = ai_result["feedback"]'''

if old_essay in text:
    text = text.replace(old_essay, new_essay)
else:
    # If not there, we insert it before Coding
    text = text.replace('elif question.type == QuestionType.CODING:', new_essay + '\n            elif question.type == QuestionType.CODING:')

with open(r'backend\app\services\grading_service.py', 'w') as f:
    f.write(text)
