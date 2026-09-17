@echo off
SETLOCAL EnableDelayedExpansion

echo ===================================================
echo     ExamSentinel - Automated Setup ^& Build
echo ===================================================
echo.

REM 1. Check prerequisites and Auto-Install via Winget
echo [*] Checking prerequisites...

where git >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] Git is missing. Attempting automatic installation via winget...
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to install Git automatically. Please install manually: https://git-scm.com/
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Git has been installed! 
    echo [ACTION REQUIRED] Please close this window and double-click the script again to continue.
    pause
    exit /b 0
)

where docker >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] Docker is missing. Attempting automatic installation via winget...
    winget install --id Docker.DockerDesktop -e --source winget --accept-package-agreements --accept-source-agreements
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to install Docker automatically. Please install manually: https://docker.com/
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Docker Desktop has been installed!
    echo [ACTION REQUIRED] Docker usually requires a system restart to enable WSL2 virtualization.
    echo Please RESTART YOUR COMPUTER, ensure Docker is running, then double-click this script again.
    pause
    exit /b 0
)

where npm >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] npm is not installed locally. Docker will still work, but IDE autocomplete is limited.
)

where python >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] Python is not installed locally. Docker will still work, but IDE autocomplete is limited.
)

echo [OK] Core Prerequisites met.
echo.

REM 2. Clone repository if we aren't already in it
if not exist "docker-compose.yml" (
    echo [*] Cloning ExamSentinel repository...
    git clone https://github.com/vishwa-10147/ExamSentiinel.git
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to clone repository.
        pause
        exit /b 1
    )
    cd ExamSentiinel
) else (
    echo [*] Running from inside existing ExamSentinel repository.
)

REM 3. Set up environment variables
echo.
echo [*] Setting up environment variables...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env file from .env.example.
    ) else (
        echo [WARNING] .env.example not found. You may need to configure .env manually.
    )
) else (
    echo [INFO] .env file already exists.
)

REM 4. Build and start Docker containers
echo.
echo [*] Building and starting Docker containers...
docker-compose up -d --build
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Docker Compose failed to start containers. Make sure Docker Desktop is running!
    pause
    exit /b 1
)

REM 5. Wait for Database
echo.
echo [*] Waiting for the database to initialize (15 seconds)...
timeout /t 15 /nobreak >nul

REM 6. Run database migrations
echo.
echo [*] Running database migrations...
docker exec examsentinel-backend alembic upgrade head
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Database migrations failed. You may need to check the backend logs.
) else (
    echo [OK] Database migrations completed successfully.
)

REM 7. Setup Local Frontend (for IDE autocomplete)
echo.
if exist "frontend\package.json" (
    where npm >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo [*] Installing local Frontend dependencies (for VS Code/IDE support)...
        cd frontend
        call npm install
        cd ..
    )
)

REM 8. Setup Local Backend (for IDE autocomplete)
echo.
if exist "backend\requirements.txt" (
    where python >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo [*] Installing local Backend dependencies in a virtual environment...
        cd backend
        if not exist "venv" (
            python -m venv venv
        )
        call venv\Scripts\activate.bat
        pip install -r requirements.txt
        deactivate
        cd ..
    )
)

echo.
echo ===================================================
echo [SUCCESS] ExamSentinel is now fully built and running!
echo ===================================================
echo.
echo    Frontend URL : http://localhost:3000
echo    Backend API  : http://localhost:8000/docs
echo.
echo You can stop the servers at any time by running:
echo    docker-compose down
echo ===================================================
pause