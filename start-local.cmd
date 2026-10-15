@echo off
setlocal EnableDelayedExpansion
title ExamSentinel - Local Launcher
cd /d "%~dp0"

rem ---------------------------------------------------------------------------
rem  ExamSentinel local launcher (SQLite + Piston code runner in Docker).
rem    start-local.cmd           start everything (first run also installs and seeds)
rem    start-local.cmd --seed    also re-run the seeders (idempotent)
rem    start-local.cmd stop      stop the API, web app and code runner (data is kept)
rem  Set NO_BROWSER=1 to skip opening the browser.
rem ---------------------------------------------------------------------------

set "PY=%~dp0.venv\Scripts\python.exe"
set "RESEED=0"
if /i "%~1"=="--seed" set "RESEED=1"
if /i "%~1"=="stop" goto :stop

echo ====================================================
echo      ExamSentinel - starting locally
echo ====================================================
echo.

rem ---- 1. Python environment ------------------------------------------------
echo [1/7] Python environment
if not exist "%PY%" (
    echo       Creating .venv with Python 3.12 ...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Python 3.12 not found. Install it with:  py install 3.12
        goto :fail
    )
    "%PY%" -m pip install --upgrade pip >nul
    "%PY%" -m pip install -r backend\requirements-dev.txt
    if errorlevel 1 goto :fail
) else (
    echo       OK
)

rem ---- 2. Configuration -----------------------------------------------------
echo [2/7] Configuration
if not exist "backend\.env" (
    copy /Y ".env.example" "backend\.env" >nul
    rem Replace the placeholder SECRET_KEY with a random one.
    "%PY%" -c "import secrets,pathlib; p=pathlib.Path('backend/.env'); p.write_text(p.read_text(encoding='utf-8').replace('replace-with-output-of-openssl-rand-hex-32', secrets.token_hex(32)), encoding='utf-8')"
    echo       Created backend\.env from .env.example
) else (
    echo       backend\.env exists
)
if not exist "frontend\.env.local" (
    > "frontend\.env.local" echo NEXT_PUBLIC_API_URL=http://localhost:8000
    >> "frontend\.env.local" echo NEXT_PUBLIC_SITE_URL=http://localhost:3000
    echo       Created frontend\.env.local
)

rem ---- 3. Frontend dependencies ----------------------------------------------
echo [3/7] Frontend dependencies
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js/npm not found. Install Node.js LTS:  winget install -e --id OpenJS.NodeJS.LTS
    goto :fail
)
if not exist "frontend\node_modules" (
    pushd frontend
    call npm install
    popd
) else (
    echo       OK
)

rem ---- 4. Docker + Piston code runner -----------------------------------------
echo [4/7] Code runner (Piston in Docker)
docker info >nul 2>&1
if errorlevel 1 (
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        echo       Starting Docker Desktop ...
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        for /l %%i in (1,1,60) do (
            docker info >nul 2>&1 && goto :docker_ready
            timeout /t 3 /nobreak >nul
        )
    )
    echo [WARNING] Docker is not running - the app will start, but Run/Submit will not work.
    goto :skip_piston
)
:docker_ready
docker compose -f docker-compose.piston.yml up -d
if errorlevel 1 (
    echo [WARNING] Could not start the Piston container - Run/Submit will not work.
    goto :skip_piston
)
"%PY%" -c "import time,urllib.request as u;exec('for _ in range(60):\n try:\n  u.urlopen(\'http://localhost:2000/api/v2/runtimes\',timeout=2);break\n except Exception:\n  time.sleep(1)')"
"%PY%" scripts\install_piston_runtimes.py >nul
if errorlevel 1 (
    echo [WARNING] Installing Piston runtimes failed. Retry:  .venv\Scripts\python scripts\install_piston_runtimes.py
) else (
    echo       OK - python, node, java, gcc, sqlite3
)
:skip_piston

rem ---- 5. Backend ----------------------------------------------------------
echo [5/7] Backend  (http://localhost:8000)
set "FIRST_RUN=0"
if not exist "backend\examsentinel_dev.db" set "FIRST_RUN=1"
call :port_in_use 8000
if "!IN_USE!"=="1" (
    echo       Port 8000 already in use - assuming the backend is running
) else (
    start "ExamSentinel Backend" /D "%~dp0backend" cmd /k ""%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)
"%PY%" -c "import sys,time,urllib.request as u;exec('for _ in range(90):\n try:\n  u.urlopen(\'http://localhost:8000/api/health/live\',timeout=2);sys.exit(0)\n except Exception:\n  time.sleep(1)\nsys.exit(1)')"
if errorlevel 1 (
    echo [ERROR] Backend did not become healthy - check the "ExamSentinel Backend" window.
    goto :fail
)
echo       Healthy

rem ---- 6. Seed data ----------------------------------------------------------
echo [6/7] Seed data
if "!FIRST_RUN!!RESEED!"=="00" (
    echo       Already seeded  ^(use  start-local.cmd --seed  to re-run^)
) else (
    pushd backend
    "%PY%" seed_admin.py
    echo       Seeding the practice problem bank ^(about 30 s^) ...
    "%PY%" seed_practice.py 2>nul | findstr /b /c:"Seeded"
    popd
)

rem ---- 7. Frontend ---------------------------------------------------------
echo [7/7] Frontend (http://localhost:3000)
call :port_in_use 3000
if "!IN_USE!"=="1" (
    echo       Port 3000 already in use - assuming the frontend is running
) else (
    start "ExamSentinel Frontend" /D "%~dp0frontend" cmd /k "npm run dev"
)
"%PY%" -c "import sys,time,urllib.request as u;exec('for _ in range(120):\n try:\n  u.urlopen(\'http://localhost:3000/auth/login\',timeout=5);sys.exit(0)\n except Exception:\n  time.sleep(1)\nsys.exit(1)')"
if errorlevel 1 (
    echo [WARNING] Frontend is still compiling - give it a moment.
) else (
    echo       Ready
)

rem Leave the delayed-expansion scope so "!" in the password below prints literally.
endlocal
echo.
echo ====================================================
echo  ExamSentinel is running
echo    App       http://localhost:3000
echo    API docs  http://localhost:8000/docs
echo.
echo  Demo logins (development only), password: DemoPass123!
echo    admin@sentinel.edu      Admin
echo    proctor@sentinel.edu    Proctor
echo    reviewer@sentinel.edu   Reviewer
echo    candidate@sentinel.edu  Candidate
echo.
echo  Stop everything with  start-local.cmd stop
echo ====================================================
if not "%NO_BROWSER%"=="1" start "" "http://localhost:3000/auth/login"
exit /b 0

:stop
rem Stops the backend and frontend windows and the Piston container (data is kept). uvicorn's
rem reloader and the Next.js server can outlive their console window, so also stop whatever
rem listens on 8000/3000 - but only if it is this app's uvicorn or Next.js process.
echo Stopping ExamSentinel ...
taskkill /FI "WINDOWTITLE eq ExamSentinel Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ExamSentinel Frontend*" /T /F >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ids = Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique;" ^
  "foreach ($id in $ids) {" ^
  "  $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $id);" ^
  "  if ($p.CommandLine -match 'uvicorn app\.main:app|next[\\/]dist') { taskkill /PID $id /T /F | Out-Null; Write-Output ('  Stopped ' + $p.Name + ' (pid ' + $id + ')') }" ^
  "  else { Write-Output ('  Port in use by another program, left running: ' + $p.Name + ' (pid ' + $id + ')') }" ^
  "}"
docker info >nul 2>&1
if not errorlevel 1 (
    docker compose -f docker-compose.piston.yml stop >nul 2>&1 && echo   Code runner stopped
)
echo Done.
endlocal
exit /b 0

:port_in_use
set "IN_USE=0"
netstat -ano | findstr /r /c:":%~1 .*LISTENING" >nul && set "IN_USE=1"
exit /b 0

:fail
echo.
echo Startup failed - see the messages above.
pause
endlocal
exit /b 1
