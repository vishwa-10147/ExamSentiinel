"""ExamSentinel Execution Worker Runner.

Scaffolded worker daemon connecting to Redis queue for isolated code execution.
"""

import os
import signal
import sys
import time
import structlog

logger = structlog.get_logger()

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SANDBOX_QUEUE = os.getenv("SANDBOX_REDIS_QUEUE", "examsentinel:sandbox:queue")
CPU_LIMIT = float(os.getenv("SANDBOX_CPU_LIMIT", "1.0"))
MEMORY_LIMIT_MB = int(os.getenv("SANDBOX_MEMORY_LIMIT_MB", "256"))
TIMEOUT_SEC = float(os.getenv("SANDBOX_TIMEOUT_SEC", "5.0"))

RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logger.info("Shutdown signal received", signal=signum)
    RUNNING = False


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info(
        "ExamSentinel execution worker started",
        redis_url=REDIS_URL,
        queue=SANDBOX_QUEUE,
        cpu_limit=CPU_LIMIT,
        memory_limit_mb=MEMORY_LIMIT_MB,
        timeout_sec=TIMEOUT_SEC,
    )

    while RUNNING:
        try:
            # Heartbeat loop awaiting Milestone 4 execution queue jobs
            time.sleep(5)
        except KeyboardInterrupt:
            break

    logger.info("ExamSentinel execution worker stopped cleanly")
    sys.exit(0)


if __name__ == "__main__":
    main()
