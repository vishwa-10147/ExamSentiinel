import datetime
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.exam import Exam
from app.models.session import ExamSession
from app.models.response import ExamResponse
from app.models.question import Question, QuestionType
from app.services.sandbox_service import sandbox_service

class GradingService:
    async def grade_session(self, db: AsyncSession, session_id: uuid.UUID) -> ExamSession:
        """Grades an exam session and computes total score."""
        session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")
        
        responses_query = await db.execute(select(ExamResponse).where(ExamResponse.session_id == session_id))
        responses = responses_query.scalars().all()
        
        total_score = 0.0
        max_score = 0.0
        
        for response in responses:
            question = (await db.execute(select(Question).where(Question.id == response.question_id))).scalar_one_or_none()
            if not question:
                continue
                
            max_score += float(question.points)
            
            # Auto-grade based on question type
            marks = 0.0
            is_correct = False
            
            if question.question_type == QuestionType.MCQ_SINGLE:
                selected = response.response_data.get("selected")
                if selected and question.correct_answer and selected == question.correct_answer:
                    marks = float(question.points)
                    is_correct = True
                    
            elif question.question_type == QuestionType.MCQ_MULTI:
                selected_list = response.response_data.get("selected", [])
                correct_list = question.correct_answer if isinstance(question.correct_answer, list) else []
                # Exact match required for full points
                if set(selected_list) == set(correct_list):
                    marks = float(question.points)
                    is_correct = True
                else:
                    # Optional: Add partial marks logic here
                    pass
                    
            elif question.question_type == QuestionType.CODING:
                # Compile & run in sandbox if code exists
                code = response.response_data.get("code")
                language = response.response_data.get("language")
                if code and language:
                    # Very simple grading: check if it runs without error.
                    # In a real scenario, you would run test cases.
                    res = sandbox_service.execute(language, code, "", 5.0, 128)
                    if res.status == "SUCCESS":
                        marks = float(question.points)
                        is_correct = True
            
            elif question.question_type in (QuestionType.ESSAY, QuestionType.SHORT_ANSWER):
                # Manual grading required
                marks = 0.0
                is_correct = None
            
            response.marks_awarded = marks
            response.is_correct = is_correct
            response.graded_at = datetime.datetime.now(datetime.timezone.utc)
            
            total_score += marks
            
        session.total_score = total_score
        session.max_score = max_score
        session.percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0
        # Rank is updated later periodically or by admin trigger
        
        await db.commit()
        await db.refresh(session)
        return session

grading_service = GradingService()
