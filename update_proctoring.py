import re

filepath = 'backend/app/api/proctoring.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import_storage = "from app.services.storage_service import storage_service\n"
if "storage_service" not in content:
    content = content.replace("from app.services.risk_engine import risk_engine", import_storage + "from app.services.risk_engine import risk_engine")

evidence_endpoint = '''
class EvidenceRequest(BaseModel):
    image_base64: str
    event_type: str
    metadata: Optional[dict] = None

@router.post("/evidence/{session_id}")
async def upload_evidence(
    session_id: uuid.UUID,
    payload: EvidenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.CANDIDATE]))
):
    # Verify session belongs to user
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id, ExamSession.candidate_id == current_user.id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    import asyncio
    # Upload to S3 in background thread
    image_url = await asyncio.to_thread(storage_service.upload_base64_image, payload.image_base64, f"evidence/{session_id}")
    
    # Create proctoring event with image URL
    new_event = ProctoringEvent(
        id=uuid.uuid4(),
        session_id=session_id,
        event_type=payload.event_type,
        timestamp=datetime.now(timezone.utc),
        details={"image_url": image_url, **(payload.metadata or {})},
        risk_score_delta=0.0
    )
    db.add(new_event)
    await db.commit()
    
    return {"status": "success", "image_url": image_url}
'''

if '@router.post("/evidence' not in content:
    content += '\n' + evidence_endpoint

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated proctoring.py")
