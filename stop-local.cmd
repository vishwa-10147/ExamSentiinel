@echo off
setlocal
cd /d "%~dp0"
rem Stops what start-local.cmd started: the backend and frontend and the Piston container.
rem The SQLite database (backend\examsentinel_dev.db) and installed runtimes are kept.

echo Stopping ExamSentinel ...
taskkill /FI "WINDOWTITLE eq ExamSentinel Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ExamSentinel Frontend*" /T /F >nul 2>&1

rem uvicorn's reloader and the Next.js server can outlive their console window, so also stop
rem whatever listens on 8000/3000 - but only if it is this app's uvicorn or Next.js process.
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
