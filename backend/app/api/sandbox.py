from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.sandbox_service import sandbox_service

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])

class CodeExecutionRequest(BaseModel):
    language: str
    code: str
    test_cases: Optional[List[str]] = None
    stdin: Optional[str] = None

class CodeExecutionResponse(BaseModel):
    status: str
    stdout: str = ""
    stderr: str = ""
    test_results: Optional[List[Dict[str, Any]]] = None
    wall_time_ms: Optional[int] = 0

@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(req: CodeExecutionRequest):
    """
    Submits code to the isolated execution engine (Piston sandbox) and returns execution results.
    Enforces a strict 5.0 second timeout and 128MB memory limit per run.
    """
    if not req.code.trim():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    if len(req.code) > 10000:
        raise HTTPException(status_code=400, detail="Source code exceeds maximum allowed size (10,000 characters).")

    lang = req.language.lower()
    if lang not in ["python", "javascript", "java", "c", "cpp", "c++", "go", "rust", "sql"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {req.language}")

    try:
        result = await sandbox_service.execute_async(
            language=lang,
            source_code=req.code,
            stdin=req.stdin or "",
            timeout_sec=5.0,
            memory_mb=128
        )
        return CodeExecutionResponse(
            status=result.status,
            stdout=result.stdout,
            stderr=result.stderr,
            wall_time_ms=result.wall_time_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code execution failed: {str(e)}")

