FROM python:3.12-slim

# WITH_AI=true adds CPU PyTorch + ultralytics and bakes in the YOLO weights
# for server-side phone / person detection (larger image).
ARG WITH_AI=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CV_MODEL_PATH=/app/models/yolo11n.pt \
    WEB_CONCURRENCY=2 \
    RUN_MIGRATIONS_ON_START=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl libglib2.0-0 \
    && if [ "$WITH_AI" = "true" ]; then apt-get install -y --no-install-recommends libgl1; fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt \
    && if [ "$WITH_AI" = "true" ]; then \
         pip install -r requirements-ai.txt \
         && mkdir -p /app/models && cd /app/models \
         && python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"; \
       fi

COPY . .

# /data/evidence: webcam evidence when stored on disk (EVIDENCE_DIR), owned by the app user
RUN useradd --create-home --uid 1001 app && mkdir -p /data/evidence && chown -R app /app /data && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000

# Liveness only: DB/Redis outages must not make the orchestrator kill the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fsS http://localhost:8000/api/health/live || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
