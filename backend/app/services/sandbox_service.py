"""Code execution via a self-hosted Piston instance.

The public emkc.org Piston API became whitelist-only on 2026-02-15, so the
engine URL is configurable (``PISTON_URL``) and points at our own container
(``docker-compose.piston.yml``) by default.

``SandboxResult.status`` values:
    success        exited 0
    error          non-zero exit / runtime error
    compile_error  compilation stage failed (C, C++, Java)
    timeout        killed for exceeding the time limit
    memory_limit   killed for exceeding the memory limit
    output_limit   killed for printing more than the engine's output cap
    system_error   the engine itself was unreachable or rejected the job
"""

import asyncio
import base64
import os
import time
from dataclasses import dataclass

import httpx

from app.core.logging import logger


@dataclass
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    wall_time_ms: int
    compile_output: str = ""


# Our language key -> (Piston language, main file name)
LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "python": ("python", "main.py"),
    "javascript": ("javascript", "main.js"),
    "java": ("java", "Main.java"),
    "cpp": ("c++", "main.cpp"),
    "c++": ("c++", "main.cpp"),
    "c": ("c", "main.c"),
    "go": ("go", "main.go"),
    "rust": ("rust", "main.rs"),
    "sql": ("sqlite3", "main.sql"),
}

COMPILE_TIMEOUT_MS = 15_000


class SandboxService:
    def __init__(self) -> None:
        self.piston_url = os.getenv("PISTON_URL", "http://127.0.0.1:2000/api/v2/execute")
        self.language_map = LANGUAGE_MAP
        # Bound concurrent jobs per backend process so bursts queue here
        # instead of overwhelming the engine.
        self._slots = asyncio.Semaphore(int(os.getenv("PISTON_MAX_CONCURRENCY", "16")))
        # One pooled keep-alive client per event loop. Opening a new connection per job cost
        # 150-400 ms (and 10x the engine's own run time) in load tests.
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

    def _http(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self._client is None or self._client_loop is not loop or self._client.is_closed:
            self._client = httpx.AsyncClient(limits=httpx.Limits(max_connections=64, max_keepalive_connections=32))
            self._client_loop = loop
        return self._client

    async def execute_async(
        self,
        language: str,
        source_code: str,
        stdin: str,
        timeout_sec: float,
        memory_mb: int,
        database_setup: str = "",
        extra_files: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Run ``source_code``. ``extra_files`` are written next to it in the sandbox.

        Large inputs should go in a file: Piston truncates stdin beyond ~200 kB.
        """
        language = language.lower()
        if language not in self.language_map:
            raise ValueError(f"Unsupported language: {language}")

        piston_language, filename = self.language_map[language]
        if language == "sql" and database_setup:
            # sqlite3 runs a single script: schema/seed first, then the answer.
            source_code = f"{database_setup.rstrip().rstrip(';')};\n{source_code}"

        payload = {
            "language": piston_language,
            "version": "*",
            "files": [{"name": filename, "content": source_code}]
            # Data files are sent base64-encoded: Piston only hands utf8 files to
            # compile scripts, so gcc won't try to compile them as source.
            + [
                {"name": name, "content": base64.b64encode(content.encode()).decode(), "encoding": "base64"}
                for name, content in (extra_files or {}).items()
            ],
            "stdin": stdin,
            "compile_timeout": COMPILE_TIMEOUT_MS,
            "run_timeout": int(timeout_sec * 1000),
            "run_memory_limit": memory_mb * 1024 * 1024,
        }

        started = time.perf_counter()
        try:
            async with self._slots:
                response = await self._http().post(
                    self.piston_url, json=payload, timeout=timeout_sec + COMPILE_TIMEOUT_MS / 1000 + 5
                )
            wall_time_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code >= 400:
                message = response.json().get("message", response.text) if response.content else ""
                logger.error("piston.rejected", status_code=response.status_code, message=message)
                return SandboxResult("system_error", "", f"Execution engine error: {message}", -1, wall_time_ms)
            data = response.json()
            data["_memory_limit_bytes"] = payload["run_memory_limit"]
            return self._to_result(data, wall_time_ms)
        except Exception as exc:  # network failures, timeouts, bad JSON
            logger.error("piston.unreachable", error=str(exc), url=self.piston_url)
            return SandboxResult(
                "system_error",
                "",
                "Code execution engine is unavailable. Please try again shortly.",
                -1,
                int((time.perf_counter() - started) * 1000),
            )

    @staticmethod
    def _to_result(data: dict, wall_time_ms: int) -> SandboxResult:
        compile_data = data.get("compile") or {}
        run_data = data.get("run") or {}

        if compile_data and compile_data.get("code") not in (0, None):
            compile_output = (compile_data.get("stderr") or compile_data.get("output") or "").strip()
            return SandboxResult("compile_error", "", compile_output, compile_data.get("code"), wall_time_ms, compile_output)

        exit_code = run_data.get("code")
        engine_status = run_data.get("status")  # TO timeout, OL/EL stdout/stderr cap, SG signal, RE, XX
        signal = run_data.get("signal")
        stdout = run_data.get("stdout", "")
        stderr = run_data.get("stderr", "")
        memory_used = run_data.get("memory") or 0
        memory_cap = data.get("_memory_limit_bytes") or 0

        if engine_status == "TO" or (signal == "SIGKILL" and engine_status is None):
            status = "timeout"
        elif engine_status in ("OL", "EL"):
            status = "output_limit"
        elif (
            "MemoryError" in stderr
            or "std::bad_alloc" in stderr
            or "OutOfMemoryError" in stderr
            or "heap out of memory" in stderr
            or (memory_cap and memory_used >= 0.95 * memory_cap and exit_code != 0)
        ):
            status = "memory_limit"
        elif exit_code == 0 and not signal:
            status = "success"
        else:
            status = "error"
        return SandboxResult(status, stdout, stderr, exit_code, wall_time_ms)


sandbox_service = SandboxService()
