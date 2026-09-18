"""ExamSentinel Execution Worker Runner (Professional Judge)."""
import os
import sys
import time
import json
import uuid
import structlog
import redis
import docker
import tarfile
import io
from typing import Dict, Any, List

logger = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SANDBOX_QUEUE = os.getenv("SANDBOX_REDIS_QUEUE", "examsentinel:sandbox:queue")
CPU_LIMIT = float(os.getenv("SANDBOX_CPU_LIMIT", "1.0"))
MEMORY_LIMIT_MB = int(os.getenv("SANDBOX_MEMORY_LIMIT_MB", "256"))
TIMEOUT_SEC = float(os.getenv("SANDBOX_TIMEOUT_SEC", "5.0"))

client = docker.from_env()

LANG_CONFIG = {
    "python": {
        "image": "python:3.12-alpine",
        "filename": "main.py",
        "compile_cmd": None,
        "run_cmd": "python main.py"
    },
    "javascript": {
        "image": "node:20-alpine",
        "filename": "main.js",
        "compile_cmd": None,
        "run_cmd": "node main.js"
    },
    "java": {
        "image": "eclipse-temurin:21-jdk-alpine",
        "filename": "Main.java",
        "compile_cmd": "javac Main.java",
        "run_cmd": "java Main"
    },
    "c": {
        "image": "gcc:13",
        "filename": "main.c",
        "compile_cmd": "gcc main.c -o main",
        "run_cmd": "./main"
    },
    "cpp": {
        "image": "gcc:13",
        "filename": "main.cpp",
        "compile_cmd": "g++ main.cpp -o main",
        "run_cmd": "./main"
    }
}

def create_tar_archive(files: Dict[str, str]) -> bytes:
    """Creates a tar archive containing the given files."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        for name, content in files.items():
            content_bytes = content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=name)
            tarinfo.size = len(content_bytes)
            tar.addfile(tarinfo, io.BytesIO(content_bytes))
    return out.getvalue()

def execute_code(job_id: str, language: str, code: str, test_cases: List[str] = None, stdin: str = None) -> Dict[str, Any]:
    if language not in LANG_CONFIG:
        return {"status": "error", "stderr": f"Unsupported language: {language}"}
    
    config = LANG_CONFIG[language]
    image = config["image"]
    filename = config["filename"]
    compile_cmd = config["compile_cmd"]
    run_cmd = config["run_cmd"]
    
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        logger.info("pulling_image", image=image)
        client.images.pull(image)

    # Initialize results
    is_grading_mode = test_cases is not None
    result = {
        "status": "success",
        "stdout": "",
        "stderr": "",
        "test_results": []
    }
    
    # Run a sleeping container to serve as our sandbox
    container = None
    try:
        container = client.containers.run(
            image,
            command=["sleep", "60"],  # Keep alive for 60 seconds max
            working_dir='/app',
            mem_limit=f"{MEMORY_LIMIT_MB}m",
            nano_cpus=int(CPU_LIMIT * 1e9),
            network_mode="none",
            detach=True
        )

        # 1. Put the source code into the container
        tar_bytes = create_tar_archive({filename: code})
        container.put_archive("/app", tar_bytes)

        # 2. Compile (if applicable)
        if compile_cmd:
            compile_exit, compile_out = container.exec_run(
                ["sh", "-c", compile_cmd],
                workdir="/app"
            )
            if compile_exit != 0:
                result["status"] = "error"
                result["stderr"] = compile_out.decode("utf-8", errors="replace")
                return result

        # 3. Execute
        if not is_grading_mode:
            # Standard single execution (Code Sandbox mode)
            if stdin is not None:
                stdin_tar = create_tar_archive({"stdin.txt": stdin})
                container.put_archive("/app", stdin_tar)
                cmd_str = f"timeout {TIMEOUT_SEC}s {run_cmd} < stdin.txt"
            else:
                cmd_str = f"timeout {TIMEOUT_SEC}s {run_cmd}"
            
            exec_res = container.exec_run(
                ["sh", "-c", cmd_str],
                workdir="/app"
            )
            out_str = exec_res.output.decode("utf-8", errors="replace")
            if exec_res.exit_code == 124 or exec_res.exit_code == 137: # Timeout exit codes
                result["status"] = "error"
                result["stderr"] = f"Execution timed out after {TIMEOUT_SEC} seconds."
            elif exec_res.exit_code != 0:
                result["stderr"] = out_str
            else:
                result["stdout"] = out_str
        else:
            # Grading mode (Multiple test cases)
            for i, stdin_data in enumerate(test_cases):
                # Put the stdin data into a file
                tc_tar = create_tar_archive({f"input_{i}.txt": stdin_data})
                container.put_archive("/app", tc_tar)
                
                # Run the code against this input
                start_time = time.time()
                exec_res = container.exec_run(
                    ["sh", "-c", f"timeout {TIMEOUT_SEC}s {run_cmd} < input_{i}.txt"],
                    workdir="/app"
                )
                wall_time = (time.time() - start_time) * 1000
                out_str = exec_res.output.decode("utf-8", errors="replace")
                
                tc_result = {
                    "index": i,
                    "stdout": "",
                    "stderr": "",
                    "wall_time_ms": round(wall_time, 2),
                    "status": "success"
                }
                
                if exec_res.exit_code == 124 or exec_res.exit_code == 137:
                    tc_result["status"] = "timeout"
                    tc_result["stderr"] = f"Timeout after {TIMEOUT_SEC}s"
                elif exec_res.exit_code != 0:
                    tc_result["status"] = "error"
                    tc_result["stderr"] = out_str
                else:
                    tc_result["stdout"] = out_str
                    
                result["test_results"].append(tc_result)

    except Exception as e:
        logger.error("execution_error", error=str(e))
        result["status"] = "error"
        result["stderr"] = str(e)
    finally:
        if container:
            try:
                container.remove(force=True)
            except:
                pass
                
    return result

def main():
    logger.info("starting_professional_sandbox_worker")
    r = redis.from_url(REDIS_URL)
    
    while True:
        try:
            item = r.blpop(SANDBOX_QUEUE, timeout=0)
            if item:
                _, data_bytes = item
                data = json.loads(data_bytes)
                job_id = data.get("job_id", str(uuid.uuid4()))
                language = data.get("language")
                code = data.get("code")
                test_cases = data.get("test_cases", None)
                stdin = data.get("stdin", None)
                
                logger.info("processing_job", job_id=job_id, language=language, is_grading=bool(test_cases))
                result = execute_code(job_id, language, code, test_cases, stdin)
                
                result_key = f"examsentinel:sandbox:result:{job_id}"
                r.setex(result_key, 60, json.dumps(result))
                logger.info("job_completed", job_id=job_id)
                
        except Exception as e:
            logger.error("worker_loop_error", error=str(e))
            time.sleep(2)

if __name__ == "__main__":
    main()
