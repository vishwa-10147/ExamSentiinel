"""Provider-neutral iCalendar fallback for interview scheduling."""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/calendar", tags=["Calendar"])


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/interviews/{interview_id}.ics")
async def interview_calendar_file(interview_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    body = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ExamSentinel//Interview Scheduler//EN",
        "BEGIN:VEVENT",
        f"UID:{interview_id}@examsentinel",
        f"DTSTAMP:{now}",
        "SUMMARY:ExamSentinel interview",
        "DESCRIPTION:Interview details are available in ExamSentinel.",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])
    return Response(content=body, media_type="text/calendar", headers={"Content-Disposition": f'attachment; filename="{interview_id}.ics"'})
