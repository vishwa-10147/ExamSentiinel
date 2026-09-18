"""Docker-isolated code execution for controlled development workers."""

from dataclasses import dataclass
import os
import shutil
import subprocess
import time
import tempfile
import uuid


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
        pass

    def execute(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:
        if shutil.which("docker") is None:
            raise SandboxUnavailableError("Sandbox runtime is unavailable: Docker CLI is not installed")
        
        import base64
        source_b64 = base64.b64encode(source_code.encode('utf-8')).decode('utf-8')
        stdin_b64 = base64.b64encode(stdin.encode('utf-8')).decode('utf-8') if stdin else ""

        # Use `head -c 1M` if possible to prevent stdout flooding, or limit it externally.
        wrapper_script = f"""
echo "{source_b64}" | base64 -d > source_file
echo "{stdin_b64}" | base64 -d > stdin_file
"""
        
        if language == "python":
            compile_run = "python source_file < stdin_file"
            image = os.getenv("SANDBOX_PYTHON_IMAGE", "python:3.11-slim")
        elif language == "javascript":
            compile_run = "node source_file < stdin_file"
            image = os.getenv("SANDBOX_NODE_IMAGE", "node:20-alpine")
        elif language == "ruby":
            compile_run = "ruby source_file < stdin_file"
            image = os.getenv("SANDBOX_RUBY_IMAGE", "ruby:3.3-slim")
        elif language == "java":
            compile_run = "mv source_file Main.java && javac Main.java && java Main < stdin_file"
            image = os.getenv("SANDBOX_JAVA_IMAGE", "openjdk:21-slim")
        elif language in ("c++", "cpp"):
            compile_run = "mv source_file main.cpp && g++ -O2 main.cpp && ./a.out < stdin_file"
            image = os.getenv("SANDBOX_CPP_IMAGE", "gcc:13")
        elif language == "c":
            compile_run = "mv source_file main.c && gcc -O2 main.c && ./a.out < stdin_file"
            image = os.getenv("SANDBOX_C_IMAGE", "gcc:13")
        elif language == "go":
            compile_run = "mv source_file main.go && go run main.go < stdin_file"
            image = os.getenv("SANDBOX_GO_IMAGE", "golang:1.22-alpine")
        elif language == "rust":
            compile_run = "mv source_file main.rs && rustc main.rs && ./main < stdin_file"
            image = os.getenv("SANDBOX_RUST_IMAGE", "rust:1.76-slim")
        else:
            raise ValueError(f"Unsupported language: {language}")

        full_script = wrapper_script + compile_run

        container_name = f"sandbox_{uuid.uuid4().hex}"

        docker_command = [
            "docker", "run", "--name", container_name,
            "--rm", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:exec,size=20m,mode=1777", "--workdir", "/tmp",
            "--cpus", "1.0", "--memory", f"{memory_mb}m", "--pids-limit", "64",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", "1000:1000",
            "-i", image, "sh", "-c", full_script
        ]

        started = time.perf_counter()
        
        # Limit output sizes by writing to TemporaryFiles
        with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
            try:
                process = subprocess.run(
                    docker_command,
                    stdout=stdout_f,
                    stderr=stderr_f,
                    timeout=timeout_sec,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                # Force kill the runaway container to prevent resource leaks
                subprocess.run(["docker", "kill", container_name], capture_output=True)
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
                
                wall_time_ms = int((time.perf_counter() - started) * 1000)
                
                # Retrieve whatever was outputted before timeout (up to limit)
                stdout_f.seek(0)
                partial_out = stdout_f.read(1024 * 1024).decode(errors="replace")
                
                return SandboxResult(
                    "TIME_LIMIT_EXCEEDED",
                    partial_out,
                    "Execution timed out",
                    None,
                    wall_time_ms,
                )

            # Ensure cleanup just in case
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

            wall_time_ms = int((time.perf_counter() - started) * 1000)
            status = "SUCCESS" if process.returncode == 0 else "RUNTIME_ERROR"
            
            stdout_f.seek(0)
            stderr_f.seek(0)
            
            # Read up to 1MB to prevent memory exhaustion on backend
            out_str = stdout_f.read(1024 * 1024).decode(errors="replace")
            err_str = stderr_f.read(1024 * 1024).decode(errors="replace")

            return SandboxResult(
                status,
                out_str,
                err_str,
                process.returncode,
                wall_time_ms,
            )


sandbox_service = SandboxService()
