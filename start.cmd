@echo off
title ExamSentinel Launcher
echo ====================================================
echo      ExamSentinel Local Development Launcher
echo ====================================================
echo.

echo Cleaning up ghost processes on Port 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000 " ^| find "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000 " ^| find "LISTENING"') do taskkill /F /PID %%a 2>nul
echo.

echo Tip: Ensure Redis and PostgreSQL are running via Docker if not installed locally!
echo You can run: docker compose up -d redis db
echo.

echo [1/2] Starting Python FastAPI Backend on Port 8000...
start "ExamSentinel - Backend API" cmd /k "cd backend && title Backend - FastAPI && echo Starting FastAPI Server... && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait 3 seconds to give backend a head start
timeout /t 3 /nobreak >nul

echo [2/2] Starting Next.js Frontend on Port 3000...
start "ExamSentinel - Frontend UI" cmd /k "cd frontend && title Frontend - Next.js && echo Starting Next.js Server... && npm run dev -p 3000"

echo.
echo ====================================================
echo All services launched in separate windows!
echo - Backend API Docs: http://localhost:8000/docs
echo - Frontend App:     http://localhost:3000
echo ====================================================
echo.
pause
