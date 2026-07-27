@echo off
title AuraQA - Stopping All Services...
color 0C

echo.
echo  ====================================================
echo    AuraQA - Stopping All Services
echo  ====================================================
echo.

:: ── Stop process on port 4000 (FastAPI Backend) ──
echo  [1/4] Stopping Backend (port 4000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo        Done.

:: ── Stop process on port 5000 (Next.js Frontend) ──
echo  [2/4] Stopping Frontend (port 5000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo        Done.

:: ── Stop Ollama ──
echo  [3/4] Stopping Ollama AI Engine...
taskkill /F /IM "ollama.exe" >nul 2>&1
taskkill /F /IM "ollama app.exe" >nul 2>&1
echo        Done.

:: ── Kill any leftover Node or Python holding ports ──
echo  [4/4] Cleaning up leftover Node.js and Python processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4000 :5000 :11434"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo        Done.

echo.
echo  ====================================================
echo    All AuraQA services have been stopped.
echo    You can now safely run run_servers.bat again.
echo  ====================================================
echo.
timeout /t 4
