import sys

new_code = '''
from pydantic import BaseModel

class GradeSubmit(BaseModel):
    marks_awarded: float
    is_correct: bool

@router.post("/grade/{response_id}")
async def submit_grade(
    response_id: uuid.UUID,
    payload: GradeSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER])),
):
    from app.models.response import ExamResponse
    
    result = await db.execute(select(ExamResponse).where(ExamResponse.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
        
    resp.marks_awarded = payload.marks_awarded
    resp.is_correct = payload.is_correct
    
    from datetime import datetime, timezone
    resp.graded_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {"status": "success", "marks_awarded": resp.marks_awarded}
'''

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'submit_grade' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
