import sys

new_code = '''
@router.post("/autograde/{response_id}")
async def autograde_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER])),
):
    from app.models.response import ExamResponse
    from app.services.ai_grading import ai_grader
    from sqlalchemy.orm import joinedload
    
    result = await db.execute(
        select(ExamResponse)
        .options(joinedload(ExamResponse.question))
        .where(ExamResponse.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
        
    answer_text = resp.response_data.get("code") or resp.response_data.get("text") or str(resp.response_data)
    
    suggestion = await ai_grader.suggest_grade(
        question_text=resp.question.content_rich_text,
        rubric=resp.question.rubric or {},
        max_points=resp.question.points,
        answer_text=answer_text
    )
    
    return suggestion
'''

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'autograde_response' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
