import sys

with open(r'backend\app\services\grading_service.py', 'r') as f:
    text = f.read()

old_mcq = '''            if question.type == QuestionType.MCQ_SINGLE:
                selected = response.response_data.get("selected")
                if selected and question.correct_answer and selected == question.correct_answer:
                    marks = float(question.points)
                    is_correct = True'''

new_mcq = '''            if question.type == QuestionType.MCQ_SINGLE:
                # Handle both direct string matches and dict structures like {"secret_key": "opt_a"}
                selected = response.response_data.get("selected_option_id") or response.response_data.get("selected")
                correct = question.correct_answer.get("secret_key") if isinstance(question.correct_answer, dict) else question.correct_answer
                if selected and correct and str(selected) == str(correct):
                    marks = float(question.points)
                    is_correct = True'''

text = text.replace(old_mcq, new_mcq)

with open(r'backend\app\services\grading_service.py', 'w') as f:
    f.write(text)
