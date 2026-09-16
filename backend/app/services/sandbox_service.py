"""Docker-isolated code execution for controlled development workers."""

from dataclasses import dataclass
import os
import shutil
import subprocess
import time


@dataclass
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    wall_time_ms: int


class SandboxUnavailableError(RuntimeError):
    pass


class SandboxService:
    def __init__(self) -> None:
        self.python_image = os.getenv("SANDBOX_PYTHON_IMAGE", "python:3.11-slim")
        self.node_image = os.getenv("SANDBOX_NODE_IMAGE", "node:20-alpine")

    def execute(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:
        if shutil.which("docker") is None:
            raise SandboxUnavailableError("Sandbox runtime is unavailable: Docker CLI is not installed")
        image, command = self._command(language)
        docker_command = [
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--cpus", "1.0", "--memory", f"{memory_mb}m", "--pids-limit", "64",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            image, *command,
        ]
        started = time.perf_counter()
        try:
            process = subprocess.run(
                docker_command,
                input=source_code.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                "TIME_LIMIT_EXCEEDED",
                (exc.stdout or b"").decode(errors="replace"),
                "Execution timed out",
                None,
                int((time.perf_counter() - started) * 1000),
            )
        wall_time_ms = int((time.perf_counter() - started) * 1000)
        status = "SUCCESS" if process.returncode == 0 else "RUNTIME_ERROR"
        return SandboxResult(
            status,
            process.stdout.decode(errors="replace"),
            process.stderr.decode(errors="replace"),
            process.returncode,
            wall_time_ms,
        )

    def _command(self, language: str) -> tuple[str, list[str]]:
        if language == "python":
            return self.python_image, ["python", "-"]
        if language == "javascript":
            return self.node_image, ["node", "-"]
        raise ValueError(f"Unsupported language: {language}")


sandbox_service = SandboxService()
