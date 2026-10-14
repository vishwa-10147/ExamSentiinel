"""API endpoints for proctoring event ingestion and risk score queries."""

import asyncio
import base64
from datetime import datetime, timedelta, timezone
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


# ── Event catalogue ───────────────────────────────────────────────────

_VALID_EVENT_TYPES = set(DEFAULT_RISK_WEIGHTS.keys())

_EVENT_CATEGORY_MAP: dict[str, EventCategory] = {
    "TAB_BLUR": EventCategory.BROWSER,
    "TAB_FOCUS": EventCategory.BROWSER,
    "VISIBILITY_HIDDEN": EventCategory.BROWSER,
    "FULLSCREEN_EXIT": EventCategory.BROWSER,
    "PASTE_ATTEMPT": EventCategory.BROWSER,
    "RIGHT_CLICK": EventCategory.BROWSER,
    "RESIZE": EventCategory.BROWSER,
    "COPY_ATTEMPT": EventCategory.BROWSER,
    "CUT_ATTEMPT": EventCategory.BROWSER,
    "SECURITY_KEY_BLOCKED": EventCategory.BROWSER,
    "FACE_NOT_DETECTED": EventCategory.WEBCAM,
    "MULTIPLE_FACES": EventCategory.WEBCAM,
    "PHONE_DETECTED": EventCategory.WEBCAM,
    "OBJECT_DETECTED": EventCategory.WEBCAM,
    "CAMERA_DENIED": EventCategory.WEBCAM,
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
    "VISIBILITY_HIDDEN": EventSeverity.INFO,
    "FULLSCREEN_EXIT": EventSeverity.HIGH,
    "PASTE_ATTEMPT": EventSeverity.MEDIUM,
    "RIGHT_CLICK": EventSeverity.LOW,
    "RESIZE": EventSeverity.LOW,
    "COPY_ATTEMPT": EventSeverity.LOW,
    "CUT_ATTEMPT": EventSeverity.LOW,
    "SECURITY_KEY_BLOCKED": EventSeverity.LOW,
    "FACE_NOT_DETECTED": EventSeverity.MEDIUM,
    "MULTIPLE_FACES": EventSeverity.CRITICAL,
    "PHONE_DETECTED": EventSeverity.HIGH,
    "OBJECT_DETECTED": EventSeverity.MEDIUM,
    "CAMERA_DENIED": EventSeverity.HIGH,
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

# Events that count toward the automatic-submission limit. Switching tabs
# fires both TAB_BLUR and VISIBILITY_HIDDEN, so only TAB_BLUR counts.
_SECURITY_EVENT_TYPES = {
    "TAB_BLUR", "FULLSCREEN_EXIT", "PASTE_ATTEMPT", "SECURITY_KEY_BLOCKED", "MULTI_TAB",
    "MULTIPLE_FACES", "PHONE_DETECTED", "SCREEN_SHARE_UNAUTHORIZED",
}
AUTO_SUBMIT_VIOLATIONS = 4

# Repeated signals of the same type within this window describe one incident:
# a phone held up for a minute is one violation, not one per video frame.
_DEDUPE_WINDOW_SECONDS: dict[str, int] = {
    "FACE_NOT_DETECTED": 30,
    "MULTIPLE_FACES": 30,
    "PHONE_DETECTED": 30,
    "OBJECT_DETECTED": 30,
    "CAMERA_DENIED": 60,
    "TAB_BLUR": 3,
    "VISIBILITY_HIDDEN": 3,
    "FULLSCREEN_EXIT": 3,
    "PASTE_ATTEMPT": 5,
    "COPY_ATTEMPT": 5,
    "CUT_ATTEMPT": 5,
    "SECURITY_KEY_BLOCKED": 5,
    "RIGHT_CLICK": 5,
    "RESIZE": 10,
}


async def _is_duplicate(db: AsyncSession, session_id: uuid.UUID, event_type: str, now: datetime) -> bool:
    window = _DEDUPE_WINDOW_SECONDS.get(event_type)
    if not window:
        return False
    recent = await db.execute(
        select(ProctoringEvent.id)
        .where(
            ProctoringEvent.session_id == session_id,
            ProctoringEvent.event_type == event_type,
            ProctoringEvent.created_at >= now - timedelta(seconds=window),
        )
        .limit(1)
    )
    return recent.scalar_one_or_none() is not None


async def _ingest_signals(
    db: AsyncSession,
    session: ExamSession,
    signals: list[dict],
) -> tuple[RiskScoreResponse, list[ProctoringEvent]]:
    """Record proctoring signals for *session*, then update risk and enforcement.

    Each signal: ``event_type`` plus optional ``category``, ``severity``,
    ``details``, ``client_timestamp``, ``snapshot_url``. Duplicates within the
    de-duplication window and signals for sessions that are no longer in
    progress are not recorded. Shared by browser telemetry and server-side
    webcam analysis so both follow identical rules.
    """
    now = datetime.now(timezone.utc)
    active = session.status in (SessionStatus.READY, SessionStatus.IN_PROGRESS)
    recorded: list[ProctoringEvent] = []
    if active:
        for signal in signals:
            event_type = signal["event_type"]
            if await _is_duplicate(db, session.id, event_type, now):
                continue
            event = ProctoringEvent(
                session_id=session.id,
                candidate_id=session.candidate_id,
                exam_id=session.exam_id,
                event_type=event_type,
                category=signal.get("category") or _EVENT_CATEGORY_MAP.get(event_type, EventCategory.BROWSER),
                severity=signal.get("severity") or _EVENT_SEVERITY_MAP.get(event_type, EventSeverity.LOW),
                details=signal.get("details") or {},
                client_timestamp=signal.get("client_timestamp"),
                snapshot_url=signal.get("snapshot_url"),
                created_at=now,
            )
            db.add(event)
            recorded.append(event)
            if event_type in _SECURITY_EVENT_TYPES:
                session.violation_count = (session.violation_count or 0) + 1

    is_terminated = False
    if active and (session.violation_count or 0) >= AUTO_SUBMIT_VIOLATIONS:
        from app.services.grading_service import grading_service

        session.status = SessionStatus.SUBMITTED
        session.submitted_at = now
        is_terminated = True
        await db.flush()
        await grading_service.grade_session(db, session.id)
        # An automatic submission is held for a human: results stay
        # unpublished until a reviewer/admin acts on the review case.
        session.results_published = False

    await db.flush()
    score, risk_level = await risk_engine.recalculate_and_update(db, session.id)
    if is_terminated:
        session.risk_level = risk_level = "CRITICAL"
        await risk_engine.ensure_review_case(db, session, score, risk_level)

    count_rows = await db.execute(
        select(ProctoringEvent.category, func.count(ProctoringEvent.id))
        .where(ProctoringEvent.session_id == session.id)
        .group_by(ProctoringEvent.category)
    )
    event_counts = [EventCountByCategory(category=cat, count=cnt) for cat, cnt in count_rows.all()]
    total_events = sum(item.count for item in event_counts)
    await db.commit()

    for event in recorded:
        await manager.broadcast_event(str(session.id), str(session.exam_id), {
            "id": str(event.id),
            "event_type": event.event_type,
            "category": event.category.value,
            "severity": event.severity.value,
            "details": storage_service.presign_details(event.details),
            "snapshot_url": storage_service.presign(event.snapshot_url),
            "violation_count": session.violation_count,
            "is_terminated": is_terminated,
            "client_timestamp": event.client_timestamp.isoformat() if event.client_timestamp else None,
        })
    if recorded or is_terminated:
        await manager.broadcast_risk_update(str(session.id), str(session.exam_id), {
            "current_risk_score": score,
            "risk_level": risk_level,
            "violation_count": session.violation_count,
            "is_terminated": is_terminated,
            "total_events": total_events,
            "event_counts": [item.model_dump(mode="json") for item in event_counts],
        })

    return RiskScoreResponse(
        session_id=session.id,
        event_type=signals[0]["event_type"] if signals else None,
        current_risk_score=score,
        risk_level=risk_level,
        violation_count=session.violation_count or 0,
        is_terminated=is_terminated or session.status == SessionStatus.SUBMITTED,
        recorded=bool(recorded),
        event_counts=event_counts,
        total_events=total_events,
    ), recorded


async def _load_session_for(db: AsyncSession, session_id: uuid.UUID, user: User) -> ExamSession:
    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if user.role == UserRole.CANDIDATE and session.candidate_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return session


# ── POST /sessions/{session_id}/webcam/analyze ──────────────────────

MAX_FRAME_BYTES = 2 * 1024 * 1024


@router.post("/sessions/{session_id}/webcam/analyze")
async def analyze_webcam_frame(
    session_id: uuid.UUID,
    frame: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyse one consented webcam frame (phones, people) and record any signals.

    A snapshot is stored as evidence only when a new signal is recorded.
    """
    session = await _load_session_for(db, session_id, current_user)
    data = await frame.read()
    if len(data) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Frame exceeds 2 MB")
    try:
        detections = await asyncio.to_thread(computer_vision_service.analyze_frame, data)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    signals = [
        {"event_type": d.event_type, "category": EventCategory.WEBCAM, "details": d.details}
        for d in detections
        if d.event_type is not None
    ]
    # Store the evidence frame only if at least one signal is new.
    now = datetime.now(timezone.utc)
    fresh = [s for s in signals if not await _is_duplicate(db, session.id, s["event_type"], now)]
    if fresh:
        image_url = await asyncio.to_thread(
            storage_service.upload_base64_image, base64.b64encode(data).decode(), f"evidence/{session_id}"
        )
        for s in signals:
            s["snapshot_url"] = image_url or None
            s["details"] = {**s["details"], "evidence_stored": bool(image_url)}

    result, recorded = await _ingest_signals(db, session, signals)
    return {
        **result.model_dump(mode="json"),
        "signals": [{"event_type": e.event_type, "details": e.details} for e in recorded],
        "detections": [{"event_type": d.event_type, "details": d.details} for d in detections],
        "capabilities": computer_vision_service.capabilities,
    }


# ── POST /events ─────────────────────────────────────────────────────

@router.post("/events", response_model=RiskScoreResponse, status_code=status.HTTP_201_CREATED)
async def submit_proctoring_event(
    payload: ProctoringEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a browser / webcam signal and recalculate risk.

    Callable by candidates (for their own session) and by admins/proctors.
    """
    if payload.event_type not in _VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown event type: {payload.event_type}. Valid types: {sorted(_VALID_EVENT_TYPES)}",
        )
    session = await _load_session_for(db, payload.session_id, current_user)
    result, _ = await _ingest_signals(db, session, [{
        "event_type": payload.event_type,
        "category": payload.category,
        "severity": payload.severity,
        "details": payload.details,
        "client_timestamp": payload.client_timestamp,
        # Only references to our own evidence bucket: a client-supplied URL
        # would otherwise be rendered to reviewers as-is.
        "snapshot_url": payload.snapshot_url if storage_service.is_own_reference(payload.snapshot_url) else None,
    }])
    return result


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
        items=[
            ProctoringEventResponse.model_validate(e).model_copy(update={
                "snapshot_url": storage_service.presign(e.snapshot_url),
                "details": storage_service.presign_details(e.details),
            })
            for e in events
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /risk/{session_id} ───────────────────────────────────────────


@router.get("/risk/{session_id:uuid}", response_model=RiskScoreResponse)
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
    content = await frame.read()
    if len(content) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Frame exceeds 2 MB")
    try:
        detections = await asyncio.to_thread(computer_vision_service.analyze_frame, content)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return {"success": True, "detections": detections, "capabilities": computer_vision_service.capabilities}


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
    
    return {"status": "success", "image_url": storage_service.presign(image_url)}


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
