import sys

with open(r'backend\app\api\reports.py', 'r') as f:
    text = f.read()

# Replace the bad import
text = text.replace('from app.models.submission import Submission', 'from app.models.response import ExamResponse')

# Update the query to use ExamResponse
old_query = '''    query = (
        select(Submission, User.full_name, Question.id.label("question_id"))
        .join(ExamSession, Submission.session_id == ExamSession.id)
        .join(User, ExamSession.candidate_id == User.id)
        .join(Question, Submission.question_id == Question.id)
        .where(ExamSession.exam_id == exam_id)
        .where(Question.type == QuestionType.CODE)
    )'''

new_query = '''    query = (
        select(ExamResponse, User.full_name, Question.id.label("question_id"))
        .join(ExamSession, ExamResponse.session_id == ExamSession.id)
        .join(User, ExamSession.candidate_id == User.id)
        .join(Question, ExamResponse.question_id == Question.id)
        .where(ExamSession.exam_id == exam_id)
        .where(Question.type == QuestionType.CODE)
    )'''
text = text.replace(old_query, new_query)

# Update the logic that reads the code text
old_logic = '''        # Ignore empty answers
        if not sub.answer_text or len(sub.answer_text.strip()) < 10:
            continue
            
        if q_id not in grouped_submissions:
            grouped_submissions[q_id] = []
            
        grouped_submissions[q_id].append({
            "id": str(sub.id),
            "student_name": student_name,
            "code": sub.answer_text
        })'''

new_logic = '''        # Try to extract the code from the JSON response
        # Typically the response_data dict contains {"code": "..."} or {"answer": "..."}
        code_text = ""
        if isinstance(sub.response_data, dict):
            code_text = sub.response_data.get("code") or sub.response_data.get("answer") or ""
        elif isinstance(sub.response_data, str):
            code_text = sub.response_data
            
        if not code_text or len(code_text.strip()) < 10:
            continue
            
        if q_id not in grouped_submissions:
            grouped_submissions[q_id] = []
            
        grouped_submissions[q_id].append({
            "id": str(sub.id),
            "student_name": student_name,
            "code": code_text
        })'''
text = text.replace(old_logic, new_logic)

with open(r'backend\app\api\reports.py', 'w') as f:
    f.write(text)
