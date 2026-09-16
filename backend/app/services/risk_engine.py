"""Core risk calculation service for ExamSentinel.

The risk engine aggregates proctoring event signals into a composite
risk score per session. All scores are *reviewer-facing signals* and
never trigger automatic verdicts.
"""

from typing import Dict, List, Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.proctoring_event import ProctoringEvent
from app.models.review_case import ReviewCase, ReviewStatus
from app.models.risk_weight import RiskWeight
from app.models.risk_score_history import RiskScoreHistory
from app.models.session import ExamSession


# ---------------------------------------------------------------------------
# Default risk weights – used when no institution-specific override exists
# ---------------------------------------------------------------------------

DEFAULT_RISK_WEIGHTS: Dict[str, float] = {
    # Browser events
    "TAB_BLUR": 2.0,
    "TAB_FOCUS": 0.0,  # informational only
    "FULLSCREEN_EXIT": 5.0,
    "PASTE_ATTEMPT": 3.0,
    "RIGHT_CLICK": 1.0,
    "RESIZE": 1.5,
    "COPY_ATTEMPT": 2.0,
    # Webcam events
    "FACE_NOT_DETECTED": 4.0,
    "MULTIPLE_FACES": 8.0,
    "PHONE_DETECTED": 7.0,
    "OBJECT_DETECTED": 3.0,
    # Code integrity events
    "LARGE_PASTE": 5.0,
    "TYPING_CADENCE_ANOMALY": 2.0,
    "CODE_SIMILARITY_HIGH": 6.0,
    # Network events
    "NETWORK_DISCONNECT": 2.0,
    "NETWORK_RECONNECT": 0.0,
    # Device events
    "VPN_DETECTED": 1.5,
    "MULTI_DEVICE": 6.0,
    "MULTI_TAB": 4.0,
    # Interview events
    "SCREEN_SHARE_UNAUTHORIZED": 5.0,
}

RISK_THRESHOLDS = {
    "LOW": 0.0,
    "MEDIUM": 15.0,
    "HIGH": 35.0,
    "CRITICAL": 60.0,
}

# A review case is auto-created when the score first crosses MEDIUM
_REVIEW_CASE_THRESHOLD = RISK_THRESHOLDS["MEDIUM"]


class RiskEngine:
    """Stateless service that calculates risk scores from proctoring events."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_risk_score(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> tuple[float, str]:
        """Calculate the cumulative risk score for a session.

        1. Fetches all proctoring events for *session_id*.
        2. Resolves effective weights (institution overrides → defaults).
        3. Sums weighted scores.
        4. Determines the risk level.

        Returns:
            ``(score, risk_level)``
        """
        # Resolve institution_id through the session → exam path
        session = await self._load_session(db, session_id)
        if session is None:
            logger.warning("risk_engine.session_not_found", session_id=str(session_id))
            return 0.0, "LOW"

        institution_id = await self._get_institution_id_for_session(db, session)
        weights = await self.get_weights_for_institution(db, institution_id)

        # Fetch all events for the session
        result = await db.execute(
            select(ProctoringEvent.event_type)
            .where(ProctoringEvent.session_id == session_id)
        )
        event_types: List[str] = list(result.scalars().all())

        score = 0.0
        for et in event_types:
            score += weights.get(et, 0.0)

        risk_level = self.determine_risk_level(score)

        logger.info(
            "risk_engine.score_calculated",
            session_id=str(session_id),
            score=score,
            risk_level=risk_level,
            event_count=len(event_types),
        )

        return score, risk_level

    async def get_weights_for_institution(
        self,
        db: AsyncSession,
        institution_id: Optional[uuid.UUID],
    ) -> Dict[str, float]:
        """Get effective risk weights, merging institution overrides with defaults.

        Resolution order:
        1. Start with ``DEFAULT_RISK_WEIGHTS``.
        2. Layer on any *global* DB rows (``institution_id IS NULL``).
        3. Layer on institution-specific DB rows (if *institution_id* given).
        """
        weights = dict(DEFAULT_RISK_WEIGHTS)

        # Global DB overrides (institution_id IS NULL, is_active=True)
        global_rows = await db.execute(
            select(RiskWeight)
            .where(
                RiskWeight.institution_id.is_(None),
                RiskWeight.is_active.is_(True),
            )
        )
        for row in global_rows.scalars().all():
            weights[row.event_type] = row.weight

        # Institution-specific overrides
        if institution_id is not None:
            inst_rows = await db.execute(
                select(RiskWeight)
                .where(
                    RiskWeight.institution_id == institution_id,
                    RiskWeight.is_active.is_(True),
                )
            )
            for row in inst_rows.scalars().all():
                weights[row.event_type] = row.weight

        return weights

    async def recalculate_and_update(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> tuple[float, str]:
        """Recalculate risk score, persist to the session record, and
        auto-create a review case if the MEDIUM threshold is crossed for
        the first time.

        Returns:
            ``(score, risk_level)``
        """
        score, risk_level = await self.calculate_risk_score(db, session_id)

        # Update the session record
        session = await self._load_session(db, session_id)
        if session is not None:
            previous_level = session.risk_level
            session.current_risk_score = score
            session.risk_level = risk_level
            latest_event = await db.execute(
                select(ProctoringEvent.id)
                .where(ProctoringEvent.session_id == session_id)
                .order_by(ProctoringEvent.created_at.desc())
                .limit(1)
            )
            db.add(
                RiskScoreHistory(
                    session_id=session_id,
                    event_id=latest_event.scalar_one_or_none(),
                    risk_score=score,
                    risk_level=risk_level,
                )
            )
            await db.flush()

            # Auto-create a review case when crossing the threshold for the
            # first time (the previous risk level was below MEDIUM).
            if (
                score >= _REVIEW_CASE_THRESHOLD
                and previous_level == "LOW"
            ):
                await self._ensure_review_case(db, session, score, risk_level)

        return score, risk_level

    def determine_risk_level(self, score: float) -> str:
        """Map a numeric score to LOW / MEDIUM / HIGH / CRITICAL."""
        if score >= RISK_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        if score >= RISK_THRESHOLDS["HIGH"]:
            return "HIGH"
        if score >= RISK_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        return "LOW"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_session(
        self, db: AsyncSession, session_id: uuid.UUID
    ) -> Optional[ExamSession]:
        result = await db.execute(
            select(ExamSession).where(ExamSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _get_institution_id_for_session(
        self, db: AsyncSession, session: ExamSession
    ) -> Optional[uuid.UUID]:
        """Resolve institution_id from exam → institution."""
        from app.models.exam import Exam  # deferred to avoid circular imports

        result = await db.execute(
            select(Exam.institution_id).where(Exam.id == session.exam_id)
        )
        return result.scalar_one_or_none()

    async def _ensure_review_case(
        self,
        db: AsyncSession,
        session: ExamSession,
        score: float,
        risk_level: str,
    ) -> None:
        """Create a review case if one does not already exist for the session."""
        existing = await db.execute(
            select(ReviewCase.id).where(ReviewCase.session_id == session.id).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return  # case already exists

        review_case = ReviewCase(
            session_id=session.id,
            candidate_id=session.candidate_id,
            exam_id=session.exam_id,
            status=ReviewStatus.PENDING,
            risk_score_at_creation=score,
            risk_level_at_creation=risk_level,
        )
        db.add(review_case)
        await db.flush()

        logger.info(
            "risk_engine.review_case_created",
            session_id=str(session.id),
            review_case_id=str(review_case.id),
            score=score,
            risk_level=risk_level,
        )


# Singleton instance
risk_engine = RiskEngine()
