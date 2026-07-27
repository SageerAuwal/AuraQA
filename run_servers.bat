@echo off
title AuraQA - Starting...
color 0A

echo.
echo  ====================================================
echo    AuraQA - AI Document Assistant
echo  ====================================================
echo.

:: ── Step 1: Check and start Ollama only if not already running ──
echo  [1/4] Checking Ollama AI Engine...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo        Ollama is already running. Skipping.
) else (
    echo        Starting Ollama...
    start "AuraQA - Ollama" cmd /k "ollama serve"
    timeout /t 4 >nul
)

echo.

:: ── Step 2: Kill any existing backend on port 4000 then restart ──
echo  [2/4] Stopping old backend if running...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

echo  [3/4] Launching Backend FastAPI Server on port 4000...
start "AuraQA - Backend" cmd /k "cd /d "%~dp0backend" && "..\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 4000"
timeout /t 3 >nul

echo.

:: ── Step 3: Build frontend if needed, then start ──
echo  [4/4] Rebuilding and Launching Frontend on port 5000...

:: Kill any process already on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

start "AuraQA - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run build && npm run start"

echo.
echo  ====================================================
echo    AuraQA is starting! Please wait ~30 seconds.
echo.
echo    Frontend: http://localhost:5000
echo    Backend:  http://127.0.0.1:4000
echo.
echo    The Frontend window will show "Ready" when done.
echo  ====================================================
echo.
timeout /t 8
