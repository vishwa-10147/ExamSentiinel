@echo off
title ExamSentinel Launcher
echo ====================================================
echo      ExamSentinel Local Development Launcher
echo ====================================================
echo.

:: Check if Redis is running (optional warning)
echo Tip: Ensure Redis and PostgreSQL are running via Docker if not installed locally!
echo You can run: docker compose up -d redis db
echo.

echo [1/2] Starting Python FastAPI Backend on Port 8000...
start "ExamSentinel - Backend API" cmd /k "cd backend && title Backend - FastAPI && echo Starting FastAPI Server... && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait 2 seconds to give backend a head start
timeout /t 2 /nobreak >nul

echo [2/2] Starting Next.js Frontend on Port 3000...
start "ExamSentinel - Frontend UI" cmd /k "cd frontend && title Frontend - Next.js && echo Starting Next.js Server... && npm run dev"

echo.
echo ====================================================
echo All services launched in separate windows!
echo - Backend API Docs: http://localhost:8000/docs
echo - Frontend App:     http://localhost:3000
echo ====================================================
echo.
echo Note: If port 3000 is blocked, Next.js will automatically try 3001.
echo.
pause
