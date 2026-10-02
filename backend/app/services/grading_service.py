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

def extract_option_val(val) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        for key in ["selected_option_id", "secret_key", "id", "text", "label", "value", "answer"]:
            if key in val and val[key] is not None:
                res = val[key]
                if isinstance(res, list) and len(res) > 0:
                    return str(res[0]).strip()
                return str(res).strip()
        if "selected_option_ids" in val and isinstance(val["selected_option_ids"], list) and len(val["selected_option_ids"]) > 0:
            return str(val["selected_option_ids"][0]).strip()
        return str(val).strip()
    if isinstance(val, list) and len(val) > 0:
        return extract_option_val(val[0])
    return str(val).strip()


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
                raw_selected = (
                    response.response_data.get("selected_option_id")
                    if "selected_option_id" in response.response_data
                    else (
                        response.response_data.get("selected")
                        if "selected" in response.response_data
                        else response.response_data.get("text")
                    )
                )
                raw_correct = question.correct_answer

                selected_str = extract_option_val(raw_selected)
                correct_str = extract_option_val(raw_correct)

                is_match = False
                if selected_str and correct_str:
                    if selected_str.strip().lower() == correct_str.strip().lower():
                        is_match = True
                    elif question.options and isinstance(question.options, list):
                        opts = [extract_option_val(o) for o in question.options]
                        try:
                            sel_idx = int(selected_str)
                            if 0 <= sel_idx < len(opts) and opts[sel_idx].strip().lower() == correct_str.strip().lower():
                                is_match = True
                        except ValueError:
                            pass
                        try:
                            cor_idx = int(correct_str)
                            if 0 <= cor_idx < len(opts) and opts[cor_idx].strip().lower() == selected_str.strip().lower():
                                is_match = True
                        except ValueError:
                            pass

                if is_match:
                    marks = question_points
                    is_correct = True

            elif question.type == QuestionType.MCQ_MULTI:
                raw_selected = (
                    response.response_data.get("selected_option_ids")
                    if "selected_option_ids" in response.response_data
                    else response.response_data.get("selected", [])
                )
                if not isinstance(raw_selected, list):
                    raw_selected = [raw_selected] if raw_selected is not None else []

                raw_correct = question.correct_answer
                if isinstance(raw_correct, dict):
                    raw_correct = (
                        raw_correct.get("selected_option_ids")
                        or raw_correct.get("correct_options")
                        or raw_correct.get("selected")
                        or []
                    )
                if not isinstance(raw_correct, list):
                    raw_correct = [raw_correct] if raw_correct is not None else []

                sel_set = {extract_option_val(x).strip().lower() for x in raw_selected if extract_option_val(x)}
                cor_set = {extract_option_val(x).strip().lower() for x in raw_correct if extract_option_val(x)}

                if sel_set and cor_set and sel_set == cor_set:
                    marks = question_points
                    is_correct = True

            elif question.type == QuestionType.SHORT_ANSWER:
                student_text = extract_option_val(
                    response.response_data.get("text")
                    or response.response_data.get("answer")
                    or response.response_data.get("selected")
                    or ""
                ).strip().lower()
                
                correct_ans = question.correct_answer
                if isinstance(correct_ans, dict):
                    ans_list = (
                        correct_ans.get("acceptable")
                        or correct_ans.get("text")
                        or correct_ans.get("answer")
                        or []
                    )
                    if not isinstance(ans_list, list):
                        ans_list = [ans_list]
                elif isinstance(correct_ans, list):
                    ans_list = correct_ans
                else:
                    ans_list = [correct_ans]

                acceptable = [extract_option_val(a).strip().lower() for a in ans_list if extract_option_val(a)]

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
        session.results_published = True
        
        await db.commit()
        await db.refresh(session)
        return session

grading_service = GradingService()
