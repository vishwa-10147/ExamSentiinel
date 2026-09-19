import sys

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_code = '''
@router.get("/my-results/detailed/{session_id}")
async def get_my_result_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
):
    from app.models.response import ExamResponse
    from app.models.session import ExamSession
    from sqlalchemy.orm import joinedload
    
    session = (await db.execute(select(ExamSession).where(
        ExamSession.id == session_id,
        ExamSession.candidate_id == current_user.id
    ))).scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    responses = (await db.execute(
        select(ExamResponse)
        .options(joinedload(ExamResponse.question))
        .where(ExamResponse.session_id == session_id)
    )).scalars().all()
    
    total_awarded = sum((r.marks_awarded or 0.0) for r in responses)
    total_possible = sum(r.question.points for r in responses)
    
    return {
        "session_id": session.id,
        "total_awarded": total_awarded,
        "total_possible": total_possible,
        "responses": [
            {
                "question_id": r.question_id,
                "question_title": r.question.title,
                "marks_awarded": r.marks_awarded,
                "is_correct": r.is_correct,
                "feedback": getattr(r, 'feedback', '')  # if we had a feedback field
            }
            for r in responses
        ]
    }
'''

if 'get_my_result_detail' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
