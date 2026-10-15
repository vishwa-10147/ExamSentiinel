"""Free-form code runner ("playground"): compile and run a program with custom stdin.

User code never runs in this process — it is sent to the self-hosted Piston engine
(see docs/CODE_EXECUTION.md for the isolation that engine provides).
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import RateLimiter, get_current_user
from app.core.logging import logger
from app.core.user_slots import UserSlot
from app.models.user import User
from app.services.practice_judge import _clean_compile_output
from app.services.sandbox_service import sandbox_service

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])

MAX_SOURCE_CHARS = 50_000
MAX_STDIN_CHARS = 64_000  # Piston truncates stdin past ~200 kB; keep custom input well below that
RUN_TIMEOUT_SEC = 5.0
RUN_MEMORY_MB = 256
PLAYGROUND_LANGUAGES = ("python", "javascript", "java", "c", "cpp", "sql")

class CodeExecutionRequest(BaseModel):
    language: str = Field(max_length=20)
    code: str = Field(max_length=MAX_SOURCE_CHARS)
    stdin: Optional[str] = Field(default=None, max_length=MAX_STDIN_CHARS)
    test_cases: Optional[List[str]] = None  # accepted for backwards compatibility; unused


class CodeExecutionResponse(BaseModel):
    status: str  # success | error | compile_error | timeout | memory_limit | output_limit | system_error
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    exit_code: Optional[int] = None
    test_results: Optional[List[Dict[str, Any]]] = None
    wall_time_ms: Optional[int] = 0
    time_limit_ms: int = int(RUN_TIMEOUT_SEC * 1000)
    memory_limit_mb: int = RUN_MEMORY_MB


@router.post("/execute", response_model=CodeExecutionResponse, dependencies=[Depends(RateLimiter(30, 60, local_fallback=True, per_user=True))])
async def execute_code(req: CodeExecutionRequest, current_user: User = Depends(get_current_user)):
    """Compile (C, C++, Java) and run the program in the sandbox with the given stdin."""
    if not req.code.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source code cannot be empty.")
    lang = req.language.lower()
    if lang == "c++":
        lang = "cpp"
    if lang not in PLAYGROUND_LANGUAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported language: {req.language}. Use one of {', '.join(PLAYGROUND_LANGUAGES)}.")
    async with UserSlot("playground", current_user.id):
        result = await sandbox_service.execute_async(
            language=lang, source_code=req.code, stdin=req.stdin or "", timeout_sec=RUN_TIMEOUT_SEC, memory_mb=RUN_MEMORY_MB,
        )
    if result.status == "system_error":
        logger.error("sandbox.system_error", detail=result.stderr[:300])
        return CodeExecutionResponse(status="system_error", stderr="The code execution engine is unavailable. Please try again shortly.")
    status_value, compile_output = result.status, result.compile_output
    if lang == "java" and result.status == "error" and "error: compilation failed" in (result.stderr or ""):
        status_value, compile_output = "compile_error", result.stderr  # Java's source launcher compiles at run time
    return CodeExecutionResponse(
        status=status_value,
        stdout=result.stdout,
        stderr="" if status_value == "compile_error" else result.stderr,
        compile_output=_clean_compile_output(compile_output) if status_value == "compile_error" else "",
        exit_code=result.exit_code,
        wall_time_ms=result.wall_time_ms,
    )
