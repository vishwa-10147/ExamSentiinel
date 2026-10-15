"""One exam session per candidate and exam.

Concurrent starts (a double click, two tabs, a retried request) could create two sessions; the
candidate was then locked out ("Multiple rows were found"). The API now resumes the existing
session when the constraint rejects a second one.

Duplicates already in the database are not deleted automatically - each may hold answers. The
migration stops and lists them; keep one session per pair (normally the one with answers) and
run it again.

Revision ID: 017_exam_session_unique
Revises: 016_contests
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017_exam_session_unique"
down_revision: Union[str, None] = "016_contests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    duplicates = op.get_bind().execute(sa.text(
        "SELECT exam_id, candidate_id, count(*) AS sessions FROM exam_sessions "
        "GROUP BY exam_id, candidate_id HAVING count(*) > 1"
    )).fetchall()
    if duplicates:
        listing = "\n".join(f"  exam {d.exam_id} candidate {d.candidate_id}: {d.sessions} sessions" for d in duplicates[:50])
        raise RuntimeError(
            "exam_sessions has more than one session for these (exam, candidate) pairs:\n"
            f"{listing}\nKeep one session per pair (normally the one with answers) and run the migration again."
        )
    op.create_unique_constraint("uq_exam_session_candidate", "exam_sessions", ["exam_id", "candidate_id"])


def downgrade() -> None:
    op.drop_constraint("uq_exam_session_candidate", "exam_sessions", type_="unique")
