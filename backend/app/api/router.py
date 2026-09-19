from fastapi import APIRouter, Depends
from app.api import auth, calendar, code_execution, compliance, dashboard, exams, health, imports, interviews, monitoring, proctoring, questions, reports, reviews, sessions, results, broadcast, usage, users
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole

api_router = APIRouter(prefix="/api")

# Mount auth routes (/api/auth/register, /login, /refresh, /me, /logout)
api_router.include_router(auth.router)

# Mount user management routes (/api/users)
api_router.include_router(users.router)

# Mount health routes (/api/health)
api_router.include_router(health.router)
api_router.include_router(imports.router)

# Mount exam management routes (/api/exams)
api_router.include_router(exams.router)

# Mount question management routes (/api/questions)
api_router.include_router(questions.router)

# Mount exam session routes (/api/exam/sessions and alias /api/sessions)
api_router.include_router(sessions.router, prefix="/exam/sessions")
api_router.include_router(sessions.router, prefix="/sessions", tags=["Exam Sessions (Alias)"])

# Mount proctoring telemetry under its named API and the legacy telemetry alias.
api_router.include_router(proctoring.router, prefix="/proctoring")
api_router.include_router(proctoring.router, prefix="/telemetry", tags=["Telemetry (Alias)"])
api_router.include_router(reviews.router)
api_router.include_router(reports.router)
api_router.include_router(code_execution.router)
api_router.include_router(interviews.router)
api_router.include_router(compliance.router)
api_router.include_router(usage.router)
api_router.include_router(results.router)
api_router.include_router(broadcast.router)
api_router.include_router(calendar.router)

# Mount admin dashboard routes (/api/dashboard)
api_router.include_router(dashboard.router)

# Mount WebSocket monitoring routes (/api/ws)
api_router.include_router(monitoring.router)

# RBAC verification endpoints for integration tests and role validation
rbac_test_router = APIRouter(prefix="/rbac-test", tags=["RBAC Test"])


@rbac_test_router.get("/admin-only")
async def admin_only_endpoint(current_user: User = Depends(require_roles([UserRole.ADMIN]))):
    return {"message": "Welcome Admin", "user_id": str(current_user.id), "role": current_user.role.value}


@rbac_test_router.get("/proctor-only")
async def proctor_only_endpoint(current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR]))):
    return {"message": "Welcome Proctor/Admin", "user_id": str(current_user.id), "role": current_user.role.value}


@rbac_test_router.get("/reviewer-only")
async def reviewer_only_endpoint(current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER]))):
    return {"message": "Welcome Reviewer/Admin", "user_id": str(current_user.id), "role": current_user.role.value}


@rbac_test_router.get("/candidate-only")
async def candidate_only_endpoint(current_user: User = Depends(require_roles([UserRole.CANDIDATE]))):
    return {"message": "Welcome Candidate", "user_id": str(current_user.id), "role": current_user.role.value}


api_router.include_router(rbac_test_router)

from app.api import sandbox
api_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox Execution"])
