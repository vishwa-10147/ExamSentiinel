@echo off
setlocal

cd /d "%~dp0"

echo ExamSentinel local startup

echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker was not found in PATH.
    echo Install and start Docker Desktop, then run this file again.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running.
    echo Start Docker Desktop, wait until it is ready, then run this file again.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Creating .env from .env.example...
    copy /Y ".env.example" ".env" >nul
)

echo Building and starting PostgreSQL, Redis, backend, frontend, and worker...
docker compose up -d --build
if errorlevel 1 (
    echo ERROR: Docker Compose failed to start the services.
    docker compose ps
    pause
    exit /b 1
)

echo Applying database migrations...
docker compose exec -T backend python -m alembic upgrade head
if errorlevel 1 (
    echo WARNING: Migrations could not be applied automatically.
    echo Run this command after the backend is healthy:
    echo docker compose exec backend python -m alembic upgrade head
)

echo.
echo ExamSentinel is starting.
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo API docs: http://localhost:8000/docs
echo Health:   http://localhost:8000/api/health
echo.
echo To view logs: docker compose logs -f backend frontend

echo Opening the frontend...
start "" "http://localhost:3000"

endlocal
exit /b 0
