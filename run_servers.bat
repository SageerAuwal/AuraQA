@echo off
title AuraQA Control Panel

echo ===================================================
echo   Starting AuraQA Application Services...
echo ===================================================

echo [1/3] Starting Ollama AI Engine...
start "AuraQA - Ollama" cmd /k "ollama serve"

timeout /t 3 >nul

echo [2/3] Launching Backend FastAPI Server (Port 4000)...
start "AuraQA - Backend" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 4000"

timeout /t 2 >nul

echo [3/3] Launching Frontend Next.js Server (Port 5000)...
start "AuraQA - Frontend" cmd /k "cd /d %~dp0frontend && npm run start"

echo.
echo ===================================================
echo   AuraQA is starting up!
echo   - Ollama AI:  http://localhost:11434
echo   - Backend:    http://127.0.0.1:4000
echo   - Frontend:   http://localhost:5000
echo.
echo   Open your browser at: http://localhost:5000
echo ===================================================
timeout /t 5
