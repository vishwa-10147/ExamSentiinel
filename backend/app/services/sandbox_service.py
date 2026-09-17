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
        pass

    def execute(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:
        if shutil.which("docker") is None:
            raise SandboxUnavailableError("Sandbox runtime is unavailable: Docker CLI is not installed")
        
        # If stdin is provided, we should probably pass it. But currently the docker command takes source_code via stdin.
        # Wait, if we use `cat > main.cpp && ...`, we consume the entire stdin for source_code. 
        # How does the user's program read stdin?
        # A better approach: pass source_code via environment variable or wrap it.
        # Actually, since we need to pass both source_code and stdin, let's use a bash wrapper:
        
        import base64
        source_b64 = base64.b64encode(source_code.encode('utf-8')).decode('utf-8')
        stdin_b64 = base64.b64encode(stdin.encode('utf-8')).decode('utf-8') if stdin else ""

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
            # For Java, the class name must match the file name if it's public.
            # We'll assume the public class is Main, or we just don't make it public.
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

        docker_command = [
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:exec", "--workdir", "/tmp",
            "--cpus", "1.0", "--memory", f"{memory_mb}m", "--pids-limit", "64",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "-i", image, "sh", "-c", full_script
        ]

        started = time.perf_counter()
        try:
            process = subprocess.run(
                docker_command,
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


sandbox_service = SandboxService()
