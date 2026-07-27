@echo off
title AuraQA - Starting...
color 0A

echo.
echo  ====================================================
echo    AuraQA - AI Document Assistant
echo  ====================================================
echo.

:: ── Step 1: Check license validity ───────────────────────────────
echo  [1/5] Checking license...

:: Quick Python check — returns 0 if valid, 1 if invalid/missing
"%~dp0venv\Scripts\python.exe" -c "
import sys, json, hashlib, hmac, uuid, socket, platform, os
from pathlib import Path
from dotenv import load_dotenv

backend = Path(r'%~dp0backend')
load_dotenv(backend / '.env')
master_key = os.getenv('MASTER_KEY', '').strip()

if not master_key or len(master_key) < 16:
    sys.exit(1)

license_file = backend / '.license'
if not license_file.exists():
    sys.exit(1)

with open(license_file) as f:
    data = json.load(f)

mac = ':'.join(['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0,12,2)][::-1])
hw = hashlib.sha256(f'{mac}|{socket.gethostname()}|{platform.machine()}'.encode()).hexdigest()

if not hmac.compare_digest(hw, data.get('hardware_hash','')):
    sys.exit(1)

sig = hmac.new(master_key.encode(), data['hardware_hash'].encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(sig, data.get('signature','')):
    sys.exit(1)

sys.exit(0)
" >nul 2>&1

if %ERRORLEVEL% == 0 (
    echo        License valid. Proceeding...
    goto :start_services
)

:: ── License missing or invalid — show popup ──────────────────────
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
    timeout /t 5
    exit /b 1
)

if %KEY_RESULT% == 2 (
    echo.
    echo  Startup cancelled by user.
    timeout /t 3
    exit /b 2
)

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

:: ── Step 3: Kill stale backend on port 4000 ──────────────────────
echo.
echo  [3/5] Clearing port 4000 for Backend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

echo  [4/5] Launching Backend (port 4000)...
start "AuraQA - Backend" cmd /k "cd /d "%~dp0backend" && "..\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 4000"
timeout /t 3 >nul

:: ── Step 4: Kill stale frontend on port 5000 ─────────────────────
echo.
echo  [5/5] Clearing port 5000 and launching Frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

start "AuraQA - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run build && npm run start"

:: ── Done ─────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo    AuraQA is starting! Please wait ~30 seconds.
echo.
echo    Open browser at: http://localhost:5000
echo  ====================================================
echo.
timeout /t 8
