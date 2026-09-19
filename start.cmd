@echo off
title ExamSentinel Launcher
echo ====================================================
echo      ExamSentinel Local Development Launcher
echo ====================================================
echo.

echo [1/4] Starting Docker services (Postgres & Redis)...
:: Stop Docker frontend/backend to prevent port conflicts with native startup
docker compose stop frontend backend 2>nul
docker compose up -d postgres redis
if errorlevel 1 (
    echo.
    echo WARNING: Docker failed to start the database!
    echo Please ensure Docker Desktop is open and running in the background.
    echo.
)
echo.

echo [2/4] Forcefully clearing Ports 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a 2>nul
echo.

echo [3/4] Launching Backend Server (FastAPI)...
start "ExamSentinel - Backend API" cmd /k "cd backend && title Backend - FastAPI && if exist ..\.venv\Scripts\activate (call ..\.venv\Scripts\activate) && pip install -r requirements.txt && echo Starting API on Port 8000... && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait 3 seconds to let backend start
timeout /t 3 /nobreak >nul

echo [4/4] Launching Frontend Server (Next.js)...
start "ExamSentinel - Frontend UI" cmd /k "cd frontend && title Frontend - Next.js && npm install && echo Starting Frontend on Port 3000... && npm run dev -- -p 3000"

:: Wait 3 seconds to let frontend start before opening browser
timeout /t 3 /nobreak >nul

echo.
echo ====================================================
echo SUCCESS: ExamSentinel has been launched!
echo.
echo Opening your browser to the correct links automatically...
start "" "http://localhost:3000/auth/login"
start "" "http://localhost:8000/docs"
echo ====================================================
pause
