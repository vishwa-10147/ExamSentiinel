"""API endpoints for proctoring event ingestion and risk score queries."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.proctoring_event import EventCategory, EventSeverity, ProctoringEvent
from app.models.risk_weight import RiskWeight
from app.models.session import ExamSession
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

    # 3. Store event
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
    await db.flush()

    # 4. Recalculate risk score
    score, risk_level = await risk_engine.recalculate_and_update(db, session.id)

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
        "client_timestamp": event.client_timestamp.isoformat() if event.client_timestamp else None,
    }
    await manager.broadcast_event(str(session.id), str(session.exam_id), event_payload)
    await manager.broadcast_risk_update(
        str(session.id),
        str(session.exam_id),
        {
            "current_risk_score": score,
            "risk_level": risk_level,
            "total_events": total_events,
            "event_counts": [item.model_dump(mode="json") for item in event_counts],
        },
    )

    return RiskScoreResponse(
        session_id=session.id,
        event_type=event.event_type,
        current_risk_score=score,
        risk_level=risk_level,
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

    If ``institution_id`` is provided, returns institution-specific overrides
    plus global defaults.  Otherwise returns only global rows.
    """
    filters = []
    if institution_id is not None:
        filters.append(
            or_(
                RiskWeight.institution_id == institution_id,
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

    return [RiskWeightConfig.model_validate(r) for r in rows]

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
