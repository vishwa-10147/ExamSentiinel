import sys

with open(r'backend\app\api\reports.py', 'r') as f:
    text = f.read()

new_endpoint = '''
from app.models.submission import Submission
from app.models.question import Question, QuestionType
from app.services.plagiarism_service import plagiarism_service

@router.get("/{exam_id}/plagiarism", response_model=list)
async def generate_plagiarism_report(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    """
    Analyzes all coding submissions for a specific exam and identifies highly similar code.
    Returns a list of student pairs who likely plagiarized.
    """
    # 1. Verify exam
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    # 2. Get all CODE submissions for this exam
    # We join Submission -> Question (to filter by type) and Submission -> ExamSession -> User
    query = (
        select(Submission, User.full_name, Question.id.label("question_id"))
        .join(ExamSession, Submission.session_id == ExamSession.id)
        .join(User, ExamSession.candidate_id == User.id)
        .join(Question, Submission.question_id == Question.id)
        .where(ExamSession.exam_id == exam_id)
        .where(Question.type == QuestionType.CODE)
    )
    
    submissions_result = await db.execute(query)
    rows = submissions_result.all()
    
    if not rows:
        return []

    # Group submissions by question_id so we only compare apples to apples
    grouped_submissions = {}
    for sub, student_name, q_id in rows:
        # Ignore empty answers
        if not sub.answer_text or len(sub.answer_text.strip()) < 10:
            continue
            
        if q_id not in grouped_submissions:
            grouped_submissions[q_id] = []
            
        grouped_submissions[q_id].append({
            "id": str(sub.id),
            "student_name": student_name,
            "code": sub.answer_text
        })
        
    all_plagiarism_flags = []
    
    # Run similarity engine per question
    for q_id, subs in grouped_submissions.items():
        if len(subs) > 1:
            flags = plagiarism_service.run_batch_comparison(subs, threshold=0.80)
            for flag in flags:
                all_plagiarism_flags.append({
                    "question_id": str(q_id),
                    "submission_id_a": flag.submission_id_a,
                    "submission_id_b": flag.submission_id_b,
                    "student_a": flag.student_a_name,
                    "student_b": flag.student_b_name,
                    "similarity_score": round(flag.similarity_score * 100, 2)
                })
                
    return all_plagiarism_flags
'''

with open(r'backend\app\api\reports.py', 'w') as f:
    f.write(text + new_endpoint)
