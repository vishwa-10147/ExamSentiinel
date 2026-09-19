@echo off
title ExamSentinel Launcher
echo ====================================================
echo      ExamSentinel Local Development Launcher
echo ====================================================
echo.

echo [1/3] Cleaning up ghost processes on Port 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000 " ^| find "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000 " ^| find "LISTENING"') do taskkill /F /PID %%a 2>nul
echo.

echo [2/3] Starting Database and Redis (Docker)...
docker compose up -d postgres redis
echo.

echo [3/3] Launching Backend and Frontend Servers...
:: Open a new window for the Python Backend (auto-activates venv and installs dependencies)
start "ExamSentinel - Backend API" cmd /k "cd backend && title Backend - FastAPI && if exist .venv\Scripts\activate (call .venv\Scripts\activate) else (echo WARNING: No .venv found. Using global python.) && echo Installing backend dependencies... && pip install -r requirements.txt && echo Starting FastAPI Server... && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait 3 seconds to give the backend a head start
timeout /t 3 /nobreak >nul

:: Open a new window for the Next.js Frontend (auto-installs dependencies)
start "ExamSentinel - Frontend UI" cmd /k "cd frontend && title Frontend - Next.js && echo Installing frontend dependencies... && npm install && echo Starting Next.js Server... && npm run dev -- -p 3000"

echo.
echo ====================================================
echo SUCCESS: All services have been launched!
echo.
echo You should see two new terminal windows open:
echo 1. Backend Server (FastAPI)
echo 2. Frontend Server (Next.js)
echo.
echo - Backend API Docs: http://localhost:8000/docs
echo - Frontend App:     http://localhost:3000
echo ====================================================
echo.
pause
