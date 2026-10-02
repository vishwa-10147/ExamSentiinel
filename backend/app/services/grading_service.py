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
from sqlalchemy.orm import selectinload
from app.models.exam import Exam
from app.models.session import ExamSession
from app.models.response import ExamResponse
from app.models.question import ExamQuestion, Question, QuestionType
from app.services.sandbox_service import sandbox_service
from app.services.ai_service import ai_service
from app.core.logging import logger

class GradingService:
    async def grade_session(self, db: AsyncSession, session_id: uuid.UUID) -> ExamSession:
        """Grades an exam session and computes total score."""
        session = (await db.execute(
            select(ExamSession)
            .options(selectinload(ExamSession.exam).selectinload(Exam.exam_questions).selectinload(ExamQuestion.question))
            .where(ExamSession.id == session_id)
        )).scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")
        
        responses_query = await db.execute(select(ExamResponse).where(ExamResponse.session_id == session_id))
        responses = responses_query.scalars().all()
        
        total_score = 0.0
        exam_questions = session.exam.exam_questions if session.exam else []
        question_map = {eq.question_id: eq for eq in exam_questions}
        max_score = sum(
            float(eq.points_override if eq.points_override is not None else eq.question.points)
            for eq in exam_questions if eq.question is not None
        )
        
        for response in responses:
            exam_question = question_map.get(response.question_id)
            question = exam_question.question if exam_question else None
            if not question:
                continue
            question_points = float(exam_question.points_override if exam_question.points_override is not None else question.points)
            
            # Auto-grade based on question type
            marks = 0.0
            is_correct = False
            
            if question.type == QuestionType.MCQ_SINGLE:
                selected = response.response_data.get("selected_option_id") if "selected_option_id" in response.response_data else response.response_data.get("selected")
                correct = question.correct_answer.get("secret_key") if isinstance(question.correct_answer, dict) else question.correct_answer
                if selected is not None and correct is not None and str(selected).strip() == str(correct).strip():
                    marks = question_points
                    is_correct = True

            elif question.type == QuestionType.MCQ_MULTI:
                selected_list = response.response_data.get("selected_option_ids") or response.response_data.get("selected", [])
                correct_list = (
                    question.correct_answer.get("selected_option_ids", [])
                    if isinstance(question.correct_answer, dict)
                    else question.correct_answer if isinstance(question.correct_answer, list) else []
                )
                if selected_list and correct_list and set(map(str, selected_list)) == set(map(str, correct_list)):
                    marks = question_points
                    is_correct = True

            elif question.type == QuestionType.SHORT_ANSWER:
                student_text = (response.response_data.get("text") or "").strip().lower()
                correct_ans = question.correct_answer
                if isinstance(correct_ans, dict):
                    correct_ans = correct_ans.get("text") or correct_ans.get("answer") or ""
                if isinstance(correct_ans, list):
                    acceptable = [str(a).strip().lower() for a in correct_ans]
                else:
                    acceptable = [str(correct_ans).strip().lower()]
                
                if student_text and student_text in acceptable:
                    marks = question_points
                    is_correct = True
                else:
                    marks = 0.0
                    is_correct = False
                    
            elif question.type == QuestionType.ESSAY:
                essay_text = response.response_data.get("text", "")
                if essay_text:
                    rubric = question.rubric or "Grade based on general comprehension and correctness."
                    try:
                        ai_result = await ai_service.grade_essay(
                            question_text=question.content_rich_text,
                            student_answer=essay_text,
                            rubric=rubric,
                        )
                        marks = (ai_result["score"] / 100.0) * question_points
                        is_correct = marks > (question_points * 0.5)
                    except Exception:
                        logger.warning("Essay response requires manual grading", extra={"response_id": str(response.id)})
                        is_correct = None
            elif question.type == QuestionType.CODING:
                code = response.response_data.get("text") or response.response_data.get("code")
                language = response.response_data.get("language") or "python"
                if code and language:
                    # Async grading via Redis Sandbox Worker
                    test_cases = []
                    if isinstance(question.correct_answer, dict) and "test_cases" in question.correct_answer:
                        test_cases = question.correct_answer["test_cases"]
                        
                    job_id = str(uuid.uuid4())
                    r = None
                    try:
                        r = redis.from_url(str(settings.REDIS_URL))
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
                                        marks = question_points * (passed / total_tc)
                                        is_correct = (passed == total_tc)
                                    else:
                                        marks = question_points
                                        is_correct = True
                                elif res.get("status") == "success":
                                    marks = question_points
                                    is_correct = True
                                break
                            await asyncio.sleep(0.2)
                    except Exception:
                        logger.warning("Coding response requires manual grading because the execution worker is unavailable", extra={"response_id": str(response.id)})
                        is_correct = None
                    finally:
                        if r is not None:
                            await r.aclose()
            
            elif question.type in (QuestionType.ESSAY, QuestionType.SHORT_ANSWER):
                # Manual grading required
                marks = 0.0
                is_correct = None
            
            response.marks_awarded = marks if is_correct is not None else None
            response.is_correct = is_correct
            response.graded_at = datetime.datetime.now(datetime.timezone.utc) if is_correct is not None else None
            
            total_score += marks
            
        session.total_score = total_score
        session.max_score = max_score
        session.percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0
        # Rank is updated later periodically or by admin trigger
        
        await db.commit()
        await db.refresh(session)
        return session

grading_service = GradingService()
