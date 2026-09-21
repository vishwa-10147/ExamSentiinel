import httpx
import time
from dataclasses import dataclass
from app.core.logging import logger

@dataclass
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    wall_time_ms: int

class SandboxService:
    def __init__(self) -> None:
        self.piston_url = "https://emkc.org/api/v2/piston/execute"
        self.language_map = {
            "python": {"language": "python", "version": "3.10.0"},
            "javascript": {"language": "javascript", "version": "18.15.0"},
            "ruby": {"language": "ruby", "version": "3.0.1"},
            "java": {"language": "java", "version": "15.0.2"},
            "c++": {"language": "c++", "version": "10.2.0"},
            "cpp": {"language": "c++", "version": "10.2.0"},
            "c": {"language": "c", "version": "10.2.0"},
            "go": {"language": "go", "version": "1.16.2"},
            "rust": {"language": "rust", "version": "1.68.2"},
            "sql": {"language": "sqlite3", "version": "3.36.0"}
        }

    async def execute_async(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:
        if language not in self.language_map:
            raise ValueError(f"Unsupported language: {language}")

        lang_config = self.language_map[language]
        
        payload = {
            "language": lang_config["language"],
            "version": lang_config["version"],
            "files": [
                {
                    "name": f"main.{language}",
                    "content": source_code
                }
            ],
            "stdin": stdin,
            "compile_timeout": int(timeout_sec * 1000),
            "run_timeout": int(timeout_sec * 1000),
            "compile_memory_limit": memory_mb * 1024 * 1024,
            "run_memory_limit": memory_mb * 1024 * 1024
        }
        
        started = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=timeout_sec + 2.0) as client:
                response = await client.post(self.piston_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                wall_time_ms = int((time.perf_counter() - started) * 1000)
                
                run_data = data.get("run", {})
                compile_data = data.get("compile", {})
                
                stderr = run_data.get("stderr", "")
                if compile_data.get("stderr"):
                    stderr = compile_data["stderr"] + "\n" + stderr
                    
                stdout = run_data.get("stdout", "")
                exit_code = run_data.get("code", compile_data.get("code", 1))
                
                status = "success" if exit_code == 0 else "error"
                if run_data.get("signal") == "SIGKILL" or compile_data.get("signal") == "SIGKILL":
                    status = "timeout"
                
                return SandboxResult(
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    wall_time_ms=wall_time_ms
                )
                
        except Exception as e:
            logger.error(f"Piston execution failed: {str(e)}")
            wall_time_ms = int((time.perf_counter() - started) * 1000)
            return SandboxResult(
                status="system_error",
                stdout="",
                stderr=str(e),
                exit_code=-1,
                wall_time_ms=wall_time_ms
            )

sandbox_service = SandboxService()
