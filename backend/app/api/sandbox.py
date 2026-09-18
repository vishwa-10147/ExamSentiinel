import uuid
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()

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

@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(req: CodeExecutionRequest):
    """
    Submits code to the isolated execution engine and waits for the result.
    If test_cases is provided, runs the code against each test case input sequentially.
    """
    job_id = str(uuid.uuid4())
    queue_name = "examsentinel:sandbox:queue"
    result_key = f"examsentinel:sandbox:result:{job_id}"
    
    r = redis.from_url(str(settings.REDIS_URL))
    
    try:
        # Push to queue
        payload = json.dumps({
            "job_id": job_id,
            "language": req.language.lower(),
            "code": req.code,
            "test_cases": req.test_cases,
            "stdin": req.stdin
        })
        await r.rpush(queue_name, payload)
        
        # Poll for result (timeout 15s total, grading multiple cases might take longer)
        for _ in range(75):
            result_bytes = await r.get(result_key)
            if result_bytes:
                result = json.loads(result_bytes)
                return CodeExecutionResponse(
                    status=result.get("status", "error"),
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    test_results=result.get("test_results")
                )
            await asyncio.sleep(0.2)
            
        # If we exit the loop, it timed out waiting for the worker
        raise HTTPException(status_code=504, detail="Execution engine did not respond in time.")
    finally:
        await r.aclose()
