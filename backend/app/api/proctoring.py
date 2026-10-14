"""API endpoints for proctoring event ingestion and risk score queries."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.proctoring_event import EventCategory, EventSeverity, ProctoringEvent
from app.models.review_case import ReviewAction, ReviewCase, ReviewStatus
from app.models.risk_weight import RiskWeight
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole
from app.schemas.proctoring import (
    EventCountByCategory,
    ProctoringEventCreate,
    ProctoringEventList,
    ProctoringEventResponse,
    RiskScoreResponse,
    RiskWeightConfig,
    RiskWeightCreate,
    RiskWeightUpdate,
)
from app.services.risk_engine import DEFAULT_RISK_WEIGHTS, risk_engine
from app.services.computer_vision import computer_vision_service
from app.services.storage_service import storage_service
from app.websocket.manager import manager

router = APIRouter(tags=["Proctoring"])


@router.post("/sessions/{session_id}/webcam/analyze")
async def analyze_webcam_frame(
    session_id: uuid.UUID,
    frame: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze one consented webcam frame and record reviewer-facing signals."""
    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        detections = computer_vision_service.analyze_frame(await frame.read())
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    recorded = []
    for detection in detections:
        if detection.event_type is None:
            continue
        event = ProctoringEvent(
            session_id=session.id,
            candidate_id=session.candidate_id,
            exam_id=session.exam_id,
            event_type=detection.event_type,
            category=EventCategory.WEBCAM,
            severity=_EVENT_SEVERITY_MAP[detection.event_type],
            details=detection.details,
        )
        db.add(event)
        recorded.append(event)
    await db.flush()
    score, risk_level = await risk_engine.recalculate_and_update(db, session.id)
    await db.commit()
    return {
        "session_id": session.id,
        "risk_score": score,
        "risk_level": risk_level,
        "signals": [{"event_type": event.event_type, "details": event.details} for event in recorded],
        "capabilities": {"face_detection": True, "phone_detection": bool(computer_vision_service.phone_model_path)},
    }


# ── Valid event types (for validation) ───────────────────────────────

_VALID_EVENT_TYPES = set(DEFAULT_RISK_WEIGHTS.keys())

# Mapping from event type prefix to category
_EVENT_CATEGORY_MAP: dict[str, EventCategory] = {
    "TAB_BLUR": EventCategory.BROWSER,
    "TAB_FOCUS": EventCategory.BROWSER,
    "FULLSCREEN_EXIT": EventCategory.BROWSER,
    "PASTE_ATTEMPT": EventCategory.BROWSER,
    "RIGHT_CLICK": EventCategory.BROWSER,
    "RESIZE": EventCategory.BROWSER,
    "COPY_ATTEMPT": EventCategory.BROWSER,
    "FACE_NOT_DETECTED": EventCategory.WEBCAM,
    "MULTIPLE_FACES": EventCategory.WEBCAM,
    "PHONE_DETECTED": EventCategory.WEBCAM,
    "OBJECT_DETECTED": EventCategory.WEBCAM,
    "LARGE_PASTE": EventCategory.CODE_INTEGRITY,
    "TYPING_CADENCE_ANOMALY": EventCategory.CODE_INTEGRITY,
    "CODE_SIMILARITY_HIGH": EventCategory.CODE_INTEGRITY,
    "NETWORK_DISCONNECT": EventCategory.NETWORK,
    "NETWORK_RECONNECT": EventCategory.NETWORK,
    "VPN_DETECTED": EventCategory.DEVICE,
    "MULTI_DEVICE": EventCategory.DEVICE,
    "MULTI_TAB": EventCategory.DEVICE,
    "SCREEN_SHARE_UNAUTHORIZED": EventCategory.INTERVIEW,
}

_EVENT_SEVERITY_MAP: dict[str, EventSeverity] = {
    "TAB_BLUR": EventSeverity.LOW,
    "TAB_FOCUS": EventSeverity.INFO,
    "FULLSCREEN_EXIT": EventSeverity.HIGH,
    "PASTE_ATTEMPT": EventSeverity.MEDIUM,
    "RIGHT_CLICK": EventSeverity.LOW,
    "RESIZE": EventSeverity.LOW,
    "COPY_ATTEMPT": EventSeverity.LOW,
    "FACE_NOT_DETECTED": EventSeverity.MEDIUM,
    "MULTIPLE_FACES": EventSeverity.CRITICAL,
    "PHONE_DETECTED": EventSeverity.HIGH,
    "OBJECT_DETECTED": EventSeverity.MEDIUM,
    "LARGE_PASTE": EventSeverity.HIGH,
    "TYPING_CADENCE_ANOMALY": EventSeverity.LOW,
    "CODE_SIMILARITY_HIGH": EventSeverity.HIGH,
    "NETWORK_DISCONNECT": EventSeverity.LOW,
    "NETWORK_RECONNECT": EventSeverity.INFO,
    "VPN_DETECTED": EventSeverity.LOW,
    "MULTI_DEVICE": EventSeverity.HIGH,
    "MULTI_TAB": EventSeverity.MEDIUM,
    "SCREEN_SHARE_UNAUTHORIZED": EventSeverity.HIGH,
}


# ── POST /events ─────────────────────────────────────────────────────


@router.post("/events", response_model=RiskScoreResponse, status_code=status.HTTP_201_CREATED)
async def submit_proctoring_event(
    payload: ProctoringEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a proctoring event (browser / webcam signal) and recalculate risk.

    Callable by candidates (for their own session) and by admins/proctors.
    """
    now = datetime.now(timezone.utc)

    # 1. Validate event type
    event_type = payload.event_type
    if event_type not in _VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown event type: {event_type}. "
                   f"Valid types: {sorted(_VALID_EVENT_TYPES)}",
        )

    # 2. Load session and authorise
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == payload.session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # 3. Store event & Track security violations
    category = payload.category if hasattr(payload, "category") and payload.category else _EVENT_CATEGORY_MAP.get(event_type, EventCategory.BROWSER)
    severity = payload.severity if hasattr(payload, "severity") and payload.severity else _EVENT_SEVERITY_MAP.get(event_type, EventSeverity.LOW)

    event = ProctoringEvent(
        session_id=session.id,
        candidate_id=session.candidate_id,
        exam_id=session.exam_id,
        event_type=event_type,
        category=category,
        severity=severity,
        details=payload.details,
        client_timestamp=payload.client_timestamp,
        snapshot_url=payload.snapshot_url if hasattr(payload, "snapshot_url") else None,
    )
    db.add(event)

    # Security violation triggers
    security_event_types = {
        "TAB_BLUR", "VISIBILITY_HIDDEN", "FULLSCREEN_EXIT", "PASTE_ATTEMPT",
        "SECURITY_KEY_BLOCKED", "MULTI_TAB", "MULTIPLE_FACES", "PHONE_DETECTED",
        "SCREEN_SHARE_UNAUTHORIZED"
    }

    if event_type in security_event_types:
        session.violation_count = (session.violation_count or 0) + 1

    is_terminated = False
    if (session.violation_count or 0) >= 4 and session.status != SessionStatus.SUBMITTED:
        from app.services.grading_service import grading_service
        session.status = SessionStatus.SUBMITTED
        session.risk_level = "CRITICAL"
        session.submitted_at = now
        session.results_published = True
        is_terminated = True
        await db.flush()
        await grading_service.grade_session(db, session.id)

    await db.flush()

    # 4. Recalculate risk score
    score, risk_level = await risk_engine.recalculate_and_update(db, session.id)
    if (session.violation_count or 0) >= 4:
        session.risk_level = "CRITICAL"
        risk_level = "CRITICAL"
        # An automatic submission must always reach a human reviewer.
        await risk_engine.ensure_review_case(db, session, score, risk_level)

    # 5. Count events by category for the response
    count_result = await db.execute(
        select(
            ProctoringEvent.category,
            func.count(ProctoringEvent.id),
        )
        .where(ProctoringEvent.session_id == session.id)
        .group_by(ProctoringEvent.category)
    )
    event_counts = [
        EventCountByCategory(category=cat, count=cnt)
        for cat, cnt in count_result.all()
    ]
    total_events_result = await db.execute(
        select(func.count(ProctoringEvent.id))
        .where(ProctoringEvent.session_id == session.id)
    )
    total_events = total_events_result.scalar_one()

    await db.commit()

    event_payload = {
        "id": str(event.id),
        "event_type": event.event_type,
        "category": event.category.value,
        "severity": event.severity.value,
        "details": event.details,
        "violation_count": session.violation_count,
        "is_terminated": is_terminated,
        "client_timestamp": event.client_timestamp.isoformat() if event.client_timestamp else None,
    }
    await manager.broadcast_event(str(session.id), str(session.exam_id), event_payload)
    await manager.broadcast_risk_update(
        str(session.id),
        str(session.exam_id),
        {
            "current_risk_score": score,
            "risk_level": risk_level,
            "violation_count": session.violation_count,
            "is_terminated": is_terminated,
            "total_events": total_events,
            "event_counts": [item.model_dump(mode="json") for item in event_counts],
        },
    )

    return RiskScoreResponse(
        session_id=session.id,
        event_type=event.event_type,
        current_risk_score=score,
        risk_level=risk_level,
        violation_count=session.violation_count or 0,
        is_terminated=is_terminated,
        event_counts=event_counts,
        total_events=total_events,
    )


# ── GET /events/{session_id} ─────────────────────────────────────────


@router.get("/events/{session_id}", response_model=ProctoringEventList)
async def get_session_events(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[EventCategory] = None,
    severity: Optional[EventSeverity] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER])
    ),
):
    """List proctoring events for a session (admin / proctor / reviewer only)."""
    # Build query
    base_filter = ProctoringEvent.session_id == session_id
    filters = [base_filter]
    if category is not None:
        filters.append(ProctoringEvent.category == category)
    if severity is not None:
        filters.append(ProctoringEvent.severity == severity)

    # Total count
    count_q = select(func.count(ProctoringEvent.id)).where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    events_q = (
        select(ProctoringEvent)
        .where(*filters)
        .order_by(ProctoringEvent.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    events = (await db.execute(events_q)).scalars().all()

    return ProctoringEventList(
        items=[ProctoringEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /risk/{session_id} ───────────────────────────────────────────


@router.get("/risk/{session_id}", response_model=RiskScoreResponse)
async def get_risk_score(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current risk score for a session."""
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )

    # Candidates can only see their own session
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build category counts
    count_result = await db.execute(
        select(
            ProctoringEvent.category,
            func.count(ProctoringEvent.id),
        )
        .where(ProctoringEvent.session_id == session_id)
        .group_by(ProctoringEvent.category)
    )
    event_counts = [
        EventCountByCategory(category=cat, count=cnt)
        for cat, cnt in count_result.all()
    ]
    total_result = await db.execute(
        select(func.count(ProctoringEvent.id))
        .where(ProctoringEvent.session_id == session_id)
    )
    total_events = total_result.scalar_one()

    return RiskScoreResponse(
        session_id=session.id,
        current_risk_score=session.current_risk_score,
        risk_level=session.risk_level,
        event_counts=event_counts,
        total_events=total_events,
    )


# ── PUT /risk/weights ────────────────────────────────────────────────


@router.put("/risk/weights", response_model=RiskWeightConfig)
async def update_risk_weight(
    payload: RiskWeightCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Create or update a risk weight entry (admin only).

    If a row with the same ``(institution_id, event_type)`` already exists
    it is updated; otherwise a new row is inserted.
    """
    # Validate event type
    if payload.event_type not in _VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown event type: {payload.event_type}",
        )

    # Upsert
    existing_q = select(RiskWeight).where(
        RiskWeight.event_type == payload.event_type,
        (
            RiskWeight.institution_id == payload.institution_id
            if payload.institution_id is not None
            else RiskWeight.institution_id.is_(None)
        ),
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    if existing:
        existing.weight = payload.weight
        existing.is_active = payload.is_active
        if payload.description is not None:
            existing.description = payload.description
        await db.flush()
        rw = existing
    else:
        rw = RiskWeight(
            institution_id=payload.institution_id,
            event_type=payload.event_type,
            weight=payload.weight,
            is_active=payload.is_active,
            description=payload.description,
        )
        db.add(rw)
        await db.flush()

    await log_audit_event(
        db=db,
        action="RISK_WEIGHT_UPDATED",
        resource_type="risk_weight",
        resource_id=str(rw.id),
        details={
            "event_type": rw.event_type,
            "weight": rw.weight,
            "institution_id": str(rw.institution_id) if rw.institution_id else None,
        },
        user_id=current_user.id,
        institution_id=current_user.institution_id,
    )
    await db.commit()
    await db.refresh(rw)

    return RiskWeightConfig.model_validate(rw)


# ── GET /risk/weights ────────────────────────────────────────────────


@router.get("/risk/weights", response_model=list[RiskWeightConfig])
async def get_risk_weights(
    institution_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER])
    ),
):
    """Get current risk weight configuration.

    If ``institution_id`` is provided or current user has an institution, returns institution-specific overrides
    plus global defaults. Otherwise returns only global rows.
    """
    target_inst_id = institution_id or current_user.institution_id
    filters = []
    if target_inst_id is not None:
        filters.append(
            or_(
                RiskWeight.institution_id == target_inst_id,
                RiskWeight.institution_id.is_(None),
            )
        )
    else:
        filters.append(RiskWeight.institution_id.is_(None))

    result = await db.execute(
        select(RiskWeight)
        .where(*filters, RiskWeight.is_active.is_(True))
        .order_by(RiskWeight.event_type)
    )
    rows = result.scalars().all()

    # Prefer institution-specific row over global default for each event_type
    merged: dict[str, RiskWeight] = {}
    for r in rows:
        if r.event_type not in merged or r.institution_id is not None:
            merged[r.event_type] = r

    return [RiskWeightConfig.model_validate(r) for r in merged.values()]

@router.post("/dev/analyze-frame")
async def dev_analyze_webcam_frame(
    frame: UploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    """DEV TOOL: Test the AI Computer Vision engine raw output without a session."""
    try:
        content = await frame.read()
        detections = computer_vision_service.analyze_frame(content)
        return {"success": True, "detections": detections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        candidate_id=session.candidate_id,
        exam_id=session.exam_id,
        event_type=payload.event_type,
        category=EventCategory.WEBCAM,
        severity=EventSeverity.INFO,
        details={"image_url": image_url, **(payload.metadata or {})},
        snapshot_url=image_url or None,
        client_timestamp=datetime.now(timezone.utc),
    )
    db.add(new_event)
    await db.commit()
    
    return {"status": "success", "image_url": image_url}


class InterveneRequest(BaseModel):
    message: Optional[str] = "Warning: Suspected unauthorized activity detected."

@router.post("/sessions/{session_id}/warning")
async def issue_proctor_warning(
    session_id: uuid.UUID,
    payload: InterveneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    """Issue a live warning to a candidate's exam session."""
    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    event = ProctoringEvent(
        id=uuid.uuid4(),
        session_id=session.id,
        candidate_id=session.candidate_id,
        exam_id=session.exam_id,
        event_type="PROCTOR_WARNING_ISSUED",
        category=EventCategory.INTERVIEW,
        severity=EventSeverity.HIGH,
        details={"message": payload.message, "issued_by": current_user.full_name},
        client_timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()

    await manager.broadcast_event(
        str(session.id),
        str(session.exam_id),
        {"event_type": "PROCTOR_WARNING_ISSUED", "message": payload.message},
    )

    return {"status": "success", "message": "Warning issued successfully"}


@router.post("/sessions/{session_id}/terminate")
async def terminate_session_by_proctor(
    session_id: uuid.UUID,
    payload: InterveneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    """Terminate an active candidate exam session immediately due to an integrity breach."""
    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    session.status = SessionStatus.EXPIRED
    session.risk_level = "CRITICAL"
    session.updated_at = datetime.now(timezone.utc)

    event = ProctoringEvent(
        id=uuid.uuid4(),
        session_id=session.id,
        candidate_id=session.candidate_id,
        exam_id=session.exam_id,
        event_type="PROCTOR_TERMINATED_SESSION",
        category=EventCategory.INTERVIEW,
        severity=EventSeverity.CRITICAL,
        details={"reason": payload.message, "terminated_by": current_user.full_name},
        client_timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await log_audit_event(
        db=db,
        action="SESSION_TERMINATED_BY_PROCTOR",
        resource_type="exam_session",
        resource_id=str(session.id),
        details={"reason": payload.message, "proctor_id": str(current_user.id)},
        user_id=current_user.id,
        institution_id=current_user.institution_id,
    )
    await db.commit()

    await manager.broadcast_event(
        str(session.id),
        str(session.exam_id),
        {"event_type": "PROCTOR_TERMINATED_SESSION", "reason": payload.message},
    )

    return {"status": "success", "message": "Exam session terminated successfully"}


# ---------------------------------------------------------------------------
# Reviewer queue (used by the /reviewer/dashboard page)
# ---------------------------------------------------------------------------

_REVIEWER_ROLES = [UserRole.ADMIN, UserRole.REVIEWER, UserRole.PROCTOR]
_QUEUE_STATUS = {
    ReviewStatus.PENDING: "PENDING_REVIEW",
    ReviewStatus.IN_REVIEW: "PENDING_REVIEW",
    ReviewStatus.ESCALATED: "PENDING_REVIEW",
    ReviewStatus.DISMISSED: "APPROVED",
    ReviewStatus.CONFIRMED: "FLAGGED_VIOLATION",
}


class ReviewDecisionRequest(BaseModel):
    notes: Optional[str] = None
    reason: Optional[str] = None


@router.get("/review-queue")
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REVIEWER_ROLES)),
):
    """List review cases as flat rows for the reviewer dashboard."""
    cases = (
        await db.execute(
            select(ReviewCase)
            .options(
                selectinload(ReviewCase.session),
                selectinload(ReviewCase.candidate),
                selectinload(ReviewCase.exam),
            )
            .order_by(ReviewCase.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    session_ids = [c.session_id for c in cases]
    event_counts: dict = {}
    if session_ids:
        rows = await db.execute(
            select(ProctoringEvent.session_id, func.count(ProctoringEvent.id))
            .where(ProctoringEvent.session_id.in_(session_ids))
            .group_by(ProctoringEvent.session_id)
        )
        event_counts = dict(rows.all())

    items = []
    for case in cases:
        session = case.session
        submitted = (session.submitted_at if session else None) or case.created_at
        items.append(
            {
                "session_id": str(case.session_id),
                "review_case_id": str(case.id),
                "candidate_name": case.candidate.full_name if case.candidate else "Unknown",
                "candidate_email": case.candidate.email if case.candidate else None,
                "exam_title": case.exam.title if case.exam else "Unknown exam",
                "exam_id": str(case.exam_id),
                "risk_score": session.current_risk_score if session else case.risk_score_at_creation,
                "risk_level": session.risk_level if session else case.risk_level_at_creation,
                "submitted_at": submitted.isoformat() if submitted else None,
                "flagged_events_count": event_counts.get(case.session_id, 0),
                "status": _QUEUE_STATUS.get(case.status, case.status.value),
            }
        )
    return items


async def _resolve_session_review(
    db: AsyncSession,
    session_id: uuid.UUID,
    reviewer: User,
    new_status: ReviewStatus,
    action: str,
    notes: Optional[str],
) -> dict:
    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    case = (
        await db.execute(
            select(ReviewCase)
            .where(ReviewCase.session_id == session_id)
            .order_by(ReviewCase.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if case is None:
        # Reviewers may act on a session the risk engine never escalated.
        case = ReviewCase(
            session_id=session.id,
            candidate_id=session.candidate_id,
            exam_id=session.exam_id,
            status=ReviewStatus.PENDING,
            risk_score_at_creation=session.current_risk_score or 0.0,
            risk_level_at_creation=session.risk_level or "LOW",
        )
        db.add(case)
        await db.flush()
    elif case.status in {ReviewStatus.DISMISSED, ReviewStatus.CONFIRMED}:
        raise HTTPException(status_code=409, detail="Review case is already resolved")

    previous_status = case.status
    now = datetime.now(timezone.utc)
    case.status = new_status
    case.assigned_reviewer_id = reviewer.id
    case.resolution_notes = notes
    case.resolved_at = now
    case.resolved_by = reviewer.id
    db.add(
        ReviewAction(
            review_case_id=case.id,
            reviewer_id=reviewer.id,
            action=action,
            notes=notes,
            previous_status=previous_status,
            new_status=new_status,
        )
    )
    await log_audit_event(
        db=db,
        action=f"REVIEW_{action}",
        resource_type="exam_session",
        resource_id=str(session.id),
        details={"review_case_id": str(case.id), "notes": notes},
        user_id=reviewer.id,
        institution_id=reviewer.institution_id,
    )
    await db.commit()
    return {"status": "success", "session_id": str(session.id), "review_status": new_status.value}


@router.post("/sessions/{session_id}/approve")
async def approve_session_review(
    session_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REVIEWER_ROLES)),
):
    """Mark a session's integrity review as cleared (case DISMISSED)."""
    return await _resolve_session_review(
        db, session_id, current_user, ReviewStatus.DISMISSED, "DISMISS", payload.notes
    )


@router.post("/sessions/{session_id}/flag-violation")
async def flag_session_violation(
    session_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REVIEWER_ROLES)),
):
    """Confirm an integrity violation for a session (case CONFIRMED)."""
    return await _resolve_session_review(
        db, session_id, current_user, ReviewStatus.CONFIRMED, "CONFIRM", payload.reason or payload.notes
    )
