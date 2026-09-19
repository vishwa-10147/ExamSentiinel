import sys
import re

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_code = '''
@router.get("/my-results")
async def get_my_results(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
):
    """Fetch graded exam sessions for the authenticated candidate."""
    from app.models.session import ExamSession, SessionStatus
    from sqlalchemy.orm import joinedload
    
    # We want sessions that are submitted and graded
    query = select(ExamSession).options(
        joinedload(ExamSession.exam)
    ).where(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED])
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "session_id": s.id,
            "exam_id": s.exam_id,
            "exam_title": s.exam.title,
            "submitted_at": s.ended_at,
            "total_score": s.current_risk_score, # We might need a separate 'total_score' field, but for now just basic output
            "status": s.status.value
        }
        for s in sessions
    ]
'''

if 'get_my_results' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
