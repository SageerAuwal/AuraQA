@echo off
title ChatBot Control Panel

echo ===================================================
echo   Starting ChatBot Application Services...
echo ===================================================

echo [1/2] Launching Backend FastAPI Server (Port 4000)...
start "ChatBot Backend" cmd /k "cd backend && ..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload"

echo [2/2] Launching Frontend Next.js Server (Port 5000)...
start "ChatBot Frontend" cmd /k "cd frontend && npm run start"

echo ===================================================
echo   Both services have been triggered in new windows!
echo   - Backend:  http://127.0.0.1:4000
echo   - Frontend: http://localhost:5000
echo ===================================================
timeout /t 5
