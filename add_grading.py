import sys

new_code = '''
@router.get("/{exam_id}/grading", response_model=list)
async def get_grading_dashboard_data(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    """
    Fetch all submitted sessions and their responses for grading.
    """
    from app.models.response import ExamResponse
    from app.models.question import Question
    from sqlalchemy.orm import joinedload
    
    # Verify exam
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    # Fetch sessions
    sessions_query = select(ExamSession).options(
        joinedload(ExamSession.candidate)
    ).where(
        ExamSession.exam_id == exam_id,
        ExamSession.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    )
    
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()
    
    if not sessions:
        return []
        
    session_ids = [s.id for s in sessions]
    
    # Fetch responses with questions
    responses_query = select(ExamResponse).options(
        joinedload(ExamResponse.question)
    ).where(
        ExamResponse.session_id.in_(session_ids)
    )
    
    resp_result = await db.execute(responses_query)
    responses = resp_result.scalars().all()
    
    # Group by student
    student_data = {}
    for session in sessions:
        student_data[session.id] = {
            "session_id": str(session.id),
            "candidate_name": session.candidate.full_name,
            "candidate_email": session.candidate.email,
            "submitted_at": session.ended_at.isoformat() if session.ended_at else None,
            "responses": []
        }
        
    for r in responses:
        if r.session_id in student_data:
            student_data[r.session_id]["responses"].append({
                "response_id": str(r.id),
                "question_id": str(r.question_id),
                "question_title": r.question.title,
                "question_type": r.question.type.value,
                "question_points": r.question.points,
                "response_data": r.response_data,
                "marks_awarded": r.marks_awarded,
                "is_correct": r.is_correct
            })
            
    return list(student_data.values())
'''

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'get_grading_dashboard_data' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
