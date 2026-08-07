@echo off
title AuraQA - Starting...
color 0A

echo.
echo  ====================================================
echo    AuraQA - AI Document Assistant
echo  ====================================================
echo.

:: ── Step 1: Check license validity ──────────────────────────────
echo  [1/5] Checking license...

"%~dp0venv\Scripts\python.exe" "%~dp0backend\check_license.py"

if %ERRORLEVEL% == 0 (
    echo        License valid. Proceeding...
    goto :start_services
)

:: ── License invalid or missing — show popup ──────────────────────
echo        License key required. Opening activation window...
echo.

"%~dp0venv\Scripts\python.exe" "%~dp0backend\key_prompt.py"
set KEY_RESULT=%ERRORLEVEL%

if %KEY_RESULT% == 0 (
    echo  [OK] Key accepted. Starting AuraQA...
    goto :start_services
)

if %KEY_RESULT% == 1 (
    echo.
    echo  ====================================================
    echo    ACCESS DENIED - Too many failed attempts.
    echo    Contact the system owner for a valid key.
    echo  ====================================================
    pause
    exit /b 1
)

echo.
echo  Startup cancelled by user.
pause
exit /b 2

:: ── Step 2: Start Ollama ─────────────────────────────────────────
:start_services
echo.
echo  [2/5] Checking Ollama AI Engine...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo        Ollama already running. Skipping.
) else (
    echo        Starting Ollama...
    start "AuraQA - Ollama" cmd /k "ollama serve"
    timeout /t 4 >nul
)

:: ── Step 3: Clear port 4000 and start backend ───────────────────
echo.
echo  [3/5] Clearing port 4000 for Backend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

echo  [4/5] Launching Backend (port 4000)...
start "AuraQA - Backend" cmd /k "cd /d "%~dp0backend" && "..\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 4000"
timeout /t 3 >nul

:: ── Step 4: Clear port 5000 and start frontend ───────────────────
echo.
echo  [5/5] Clearing port 5000 and launching Frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

start "AuraQA - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run build && npm run start"

:: ── Done ──────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo    AuraQA is starting! Please wait ~30 seconds.
echo.
echo    Open browser at: http://localhost:5000
echo.
echo    The Frontend window shows "Ready" when done.
echo  ====================================================
echo.
timeout /t 8
