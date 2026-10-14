import asyncio
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


def _normalize_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in (text or "").strip().splitlines())


class GradingService:
    async def _grade_code(self, code: str, language: str, test_cases: list, points: float) -> tuple[float, Optional[bool]]:
        """Run a coding answer against stdin/stdout test cases on the sandbox.

        Returns (marks, is_correct). is_correct is None when the engine is
        unavailable, so the answer falls back to manual grading.
        """
        language = "cpp" if language.lower() in ("c++", "cpp") else language.lower()
        results = await asyncio.gather(*[
            sandbox_service.execute_async(language, code, str(tc.get("input", "")), 5.0, 128) for tc in test_cases
        ])
        if any(r.status == "system_error" for r in results):
            return 0.0, None
        passed = sum(
            1
            for tc, r in zip(test_cases, results)
            if r.status == "success" and _normalize_output(r.stdout) == _normalize_output(str(tc.get("output", "")))
        )
        return points * passed / len(test_cases), passed == len(test_cases)

    async def _grade_practice_problem(
        self, db: AsyncSession, problem_id: str, code: str, language: str, points: float
    ) -> tuple[float, Optional[bool]]:
        """Grade against every test of a linked practice problem (hidden ones included)."""
        from app.models.practice import PracticeProblem, Verdict
        from app.services.practice_judge import JudgeCase, JudgeSpecError, judge

        problem = (await db.execute(
            select(PracticeProblem).options(selectinload(PracticeProblem.test_cases))
            .where(PracticeProblem.id == uuid.UUID(problem_id))
        )).scalar_one_or_none()
        if problem is None or not problem.test_cases:
            return 0.0, None
        cases = [JudgeCase(tc.input_data, tc.expected_output, tc.is_sample) for tc in problem.test_cases]
        try:
            outcome = await judge(problem, language.lower(), code, cases)
        except JudgeSpecError:
            return 0.0, False  # e.g. a language this problem doesn't support
        if outcome.verdict == Verdict.SYSTEM_ERROR:
            return 0.0, None
        return points * outcome.passed_count / len(cases), outcome.verdict == Verdict.ACCEPTED

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
            elif question.type in (QuestionType.CODING, QuestionType.SQL):
                code = response.response_data.get("text") or response.response_data.get("code")
                default_language = "sql" if question.type == QuestionType.SQL else "python"
                language = response.response_data.get("language") or default_language
                linked_problem = (
                    question.correct_answer.get("practice_problem_id")
                    if isinstance(question.correct_answer, dict) else None
                )
                test_cases = []
                if isinstance(question.correct_answer, dict):
                    test_cases = question.correct_answer.get("test_cases") or []
                elif isinstance(question.correct_answer, list):
                    test_cases = question.correct_answer
                if code and linked_problem:
                    marks, is_correct = await self._grade_practice_problem(db, linked_problem, code, language, question_points)
                    if is_correct is None:
                        logger.warning("Coding response requires manual grading because the execution engine is unavailable", extra={"response_id": str(response.id)})
                elif code and test_cases and question.type == QuestionType.CODING:
                    marks, is_correct = await self._grade_code(code, language, test_cases, question_points)
                    if is_correct is None:
                        logger.warning("Coding response requires manual grading because the execution engine is unavailable", extra={"response_id": str(response.id)})
                else:
                    # Nothing to run against (or no code): an instructor grades it.
                    is_correct = None
            
            elif question.type == QuestionType.ESSAY:
                # Manual grading required for essay
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
