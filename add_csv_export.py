import sys

new_code = '''
@router.get("/{exam_id}/export")
async def export_exam_grades_csv(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    from app.models.response import ExamResponse
    from sqlalchemy.orm import joinedload
    
    # Fetch sessions
    sessions_query = select(ExamSession).options(
        joinedload(ExamSession.candidate)
    ).where(
        ExamSession.exam_id == exam_id,
        ExamSession.status.in_(["SUBMITTED", "AUTO_SUBMITTED"])
    )
    
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()
    
    session_ids = [s.id for s in sessions]
    
    # Fetch responses
    responses_query = select(ExamResponse).where(ExamResponse.session_id.in_(session_ids))
    resp_result = await db.execute(responses_query)
    responses = resp_result.scalars().all()
    
    student_scores = {}
    for r in responses:
        if r.session_id not in student_scores:
            student_scores[r.session_id] = 0.0
        if r.marks_awarded:
            student_scores[r.session_id] += r.marks_awarded
            
    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session ID", "Candidate Name", "Candidate Email", "Roll Number", "Status", "Risk Level", "Risk Score", "Total Score"])
    
    for s in sessions:
        score = student_scores.get(s.id, 0.0)
        writer.writerow([
            str(s.id),
            s.candidate.full_name,
            s.candidate.email,
            getattr(s.candidate, "roll_number", "N/A"),
            s.status.value,
            s.risk_level,
            s.current_risk_score,
            score
        ])
        
    output.seek(0)
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_grades.csv"})
'''

with open(r'backend\app\api\reports.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'export_exam_grades_csv' not in text:
    with open(r'backend\app\api\reports.py', 'w', encoding='utf-8') as f:
        f.write(text + new_code)
