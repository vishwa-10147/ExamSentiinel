import json
import uuid
import asyncio
import redis.asyncio as redis
from app.core.config import settings
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
                code = response.response_data.get("text") or response.response_data.get("code")
                language = response.response_data.get("language") or "python"
                if code and language:
                    # Async grading via Redis Sandbox Worker
                    test_cases = []
                    if isinstance(question.correct_answer, dict) and "test_cases" in question.correct_answer:
                        test_cases = question.correct_answer["test_cases"]
                        
                    job_id = str(uuid.uuid4())
                    r = redis.from_url(str(settings.REDIS_URL))
                    try:
                        payload = json.dumps({
                            "job_id": job_id,
                            "language": language.lower(),
                            "code": code,
                            "test_cases": test_cases if test_cases else None
                        })
                        await r.rpush("examsentinel:sandbox:queue", payload)
                        
                        # Wait for execution to complete
                        for _ in range(75):
                            result_bytes = await r.get(f"examsentinel:sandbox:result:{job_id}")
                            if result_bytes:
                                res = json.loads(result_bytes)
                                
                                if res.get("status") == "success" and "test_results" in res:
                                    passed = sum(1 for tr in res["test_results"] if tr.get("status") == "success")
                                    total_tc = len(res["test_results"])
                                    if total_tc > 0:
                                        marks = float(question.points) * (passed / total_tc)
                                        is_correct = (passed == total_tc)
                                    else:
                                        marks = float(question.points)
                                        is_correct = True
                                elif res.get("status") == "success":
                                    marks = float(question.points)
                                    is_correct = True
                                break
                            await asyncio.sleep(0.2)
                    finally:
                        await r.aclose()
            
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
