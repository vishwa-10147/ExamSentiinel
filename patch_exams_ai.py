import sys

with open(r'backend\app\api\exams.py', 'r') as f:
    text = f.read()

import_statement = '''from app.services.ai_service import ai_service
from pydantic import BaseModel

class AIGenerateRequest(BaseModel):
    syllabus_text: str
    question_count: int = 5
'''

endpoint = '''
@router.post("/{exam_id}/generate-ai")
async def generate_ai_questions(
    exam_id: uuid.UUID,
    request: AIGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR]))
):
    """Generates questions using AI based on provided syllabus/topics and attaches them to the exam."""
    
    # Verify exam exists and belongs to institution
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    questions_data = await ai_service.generate_questions_from_syllabus(
        syllabus_text=request.syllabus_text,
        question_count=request.question_count
    )
    
    # Save them to the DB
    from app.models.question import Question, QuestionType
    created_questions = []
    for idx, q_data in enumerate(questions_data):
        new_q = Question(
            exam_id=exam_id,
            type=QuestionType.MULTIPLE_CHOICE,
            text=q_data["text"],
            points=q_data.get("points", 10),
            order_index=idx,
            data=q_data["data"],
            correct_answer=q_data["correct_answer"]
        )
        db.add(new_q)
        created_questions.append(new_q)
        
    await db.commit()
    
    return {"message": f"Successfully generated and added {len(created_questions)} questions via AI.", "count": len(created_questions)}
'''

if 'generate-ai' not in text:
    text = text.replace('from app.api.deps import get_current_user, require_roles', 'from app.api.deps import get_current_user, require_roles\n' + import_statement)
    text = text + '\n' + endpoint
    with open(r'backend\app\api\exams.py', 'w') as f:
        f.write(text)
