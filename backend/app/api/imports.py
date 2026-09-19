import csv
import io
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.question import Question, QuestionType, ExamQuestion
from app.models.user import User, UserRole
from app.services.roll_parser import default_parser

router = APIRouter(prefix="/imports", tags=["Imports"])

@router.post("/questions/{exam_id}")
async def import_questions(
    exam_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        
        imported_count = 0
        for row in reader:
            # Expected columns: title, type, content, points, difficulty
            q_type_str = row.get("type", "SHORT_ANSWER").upper()
            try:
                q_type = QuestionType(q_type_str)
            except ValueError:
                q_type = QuestionType.SHORT_ANSWER
                
            question = Question(
                title=row.get("title", "Imported Question"),
                type=q_type,
                content_rich_text=row.get("content", ""),
                points=float(row.get("points", 1.0)),
                difficulty=row.get("difficulty", "MEDIUM").upper(),
            )
            db.add(question)
            await db.flush() # flush to get question.id
            
            exam_q = ExamQuestion(
                exam_id=exam_id,
                question_id=question.id,
                order_index=imported_count,
            )
            db.add(exam_q)
            imported_count += 1
            
        await db.commit()
        return {"status": "success", "imported": imported_count}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")

@router.post("/students")
async def import_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        
        imported_count = 0
        for row in reader:
            # Expected columns: email, full_name, roll_number
            email = row.get("email")
            if not email:
                continue
                
            # Check if exists
            exists = await db.execute(select(User).where(User.email == email))
            if exists.scalar_one_or_none():
                continue
                
            roll_number = row.get("roll_number", "")
            
            user = User(
                email=email,
                full_name=row.get("full_name", email.split("@")[0]),
                role=UserRole.CANDIDATE,
                roll_number=roll_number
            )
            
            # Use default password for bulk imports (in real app, trigger email reset)
            from app.core.security import get_password_hash
            user.hashed_password = get_password_hash("Student123!")
            
            db.add(user)
            imported_count += 1
            
            from app.services.email_service import email_service
            email_service.send_welcome_email(user.email, user.full_name, "Student123!")
            
        await db.commit()
        return {"status": "success", "imported": imported_count}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")
