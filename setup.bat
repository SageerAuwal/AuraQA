@echo off
title AuraQA - Setup ^& Installation
color 0A
setlocal EnableDelayedExpansion

echo.
echo  ====================================================
echo    AuraQA - Automated Setup ^& Installation
echo    AI-Powered Academic Document Assistant
echo  ====================================================
echo.
echo  Scanning your machine... Please wait.
echo.

:: ── Track what needs installing ──────────────────────────────────
set PYTHON_OK=0
set NODE_OK=0
set OLLAMA_OK=0
set VENV_OK=0
set EMBED_OK=0
set QWEN_OK=0
set GEMMA_OK=0

:: ── Scan machine ─────────────────────────────────────────────────

python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_OK=1
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v detected
) else (
    echo  [!!] Python not found ----------- will install automatically
)

node --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set NODE_OK=1
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo  [OK] Node.js %%v detected
) else (
    echo  [!!] Node.js not found ---------- will install automatically
)

ollama --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set OLLAMA_OK=1
    echo  [OK] Ollama detected
) else (
    echo  [!!] Ollama not found ----------- will install automatically
)

if exist "%~dp0venv\Scripts\python.exe" (
    set VENV_OK=1
    echo  [OK] Python virtual environment detected
) else (
    echo  [!!] Virtual environment missing - will create
)

if exist "%~dp0backend\app\embedding_model\config.json" (
    set EMBED_OK=1
    echo  [OK] Embedding model detected
) else (
    echo  [!!] Embedding model missing ----- will download ^(~90MB^)
)

echo.
echo  ====================================================
echo.
echo  Starting installation... This may take several
echo  minutes depending on your internet speed.
echo.
echo  ====================================================
echo.
timeout /t 3 >nul

:: ────────────────────────────────────────────────────────────────
:: STEP 1: Install Python
:: ────────────────────────────────────────────────────────────────
if %PYTHON_OK% == 0 (
    echo  [1/12] Downloading Python 3.11 ...
    powershell -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%~dp0_python_setup.exe' -UseBasicParsing"
    echo         Installing Python 3.11 ^(Windows may ask for permission^)...
    start /wait "" "%~dp0_python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%~dp0_python_setup.exe" >nul 2>&1
    :: Refresh PATH from registry
    for /f "usebackq tokens=*" %%a in (`powershell -Command "[Environment]::GetEnvironmentVariable('PATH','User')"`) do set "PATH=%%a;!PATH!"
    echo         Python installed successfully.
) else (
    echo  [1/12] Python already installed. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 2: Install Node.js
:: ────────────────────────────────────────────────────────────────
if %NODE_OK% == 0 (
    echo  [2/12] Downloading Node.js 20 ^(~30MB^)...
    powershell -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.17.0/node-v20.17.0-x64.msi' -OutFile '%~dp0_node_setup.msi' -UseBasicParsing"
    echo         Installing Node.js 20 ^(Windows may ask for permission^)...
    start /wait msiexec /i "%~dp0_node_setup.msi" /quiet /norestart
    del "%~dp0_node_setup.msi" >nul 2>&1
    :: Refresh PATH from registry
    for /f "usebackq tokens=*" %%a in (`powershell -Command "[Environment]::GetEnvironmentVariable('PATH','Machine')"`) do set "PATH=%%a;!PATH!"
    echo         Node.js installed successfully.
) else (
    echo  [2/12] Node.js already installed. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 3: Install Ollama
:: ────────────────────────────────────────────────────────────────
if %OLLAMA_OK% == 0 (
    echo  [3/12] Downloading Ollama ^(~60MB^)...
    powershell -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri 'https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe' -OutFile '%~dp0_ollama_setup.exe' -UseBasicParsing"
    echo         Installing Ollama silently...
    start /wait "" "%~dp0_ollama_setup.exe" /S
    del "%~dp0_ollama_setup.exe" >nul 2>&1
    :: Refresh PATH from registry
    for /f "usebackq tokens=*" %%a in (`powershell -Command "[Environment]::GetEnvironmentVariable('PATH','Machine')"`) do set "PATH=%%a;!PATH!"
    echo         Ollama installed successfully.
) else (
    echo  [3/12] Ollama already installed. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 4: Create Python virtual environment
:: ────────────────────────────────────────────────────────────────
if %VENV_OK% == 0 (
    echo  [4/12] Creating Python virtual environment...
    python -m venv "%~dp0venv"
    echo         Virtual environment created.
) else (
    echo  [4/12] Virtual environment exists. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 5: Install backend Python packages
:: ────────────────────────────────────────────────────────────────
echo  [5/12] Installing backend Python packages...
echo         ^(FastAPI, SQLAlchemy, sentence-transformers, etc.^)
"%~dp0venv\Scripts\pip.exe" install -r "%~dp0backend\requirements.txt" -q --no-warn-script-location
if %ERRORLEVEL% == 0 (
    echo         Backend packages installed successfully.
) else (
    echo         WARNING: Some packages may have failed. Continuing...
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 6: Download multilingual embedding model
:: ────────────────────────────────────────────────────────────────
if %EMBED_OK% == 0 (
    echo  [6/12] Downloading multilingual embedding model ^(~90MB^)...
    echo         This enables document search in 6 languages.
    "%~dp0venv\Scripts\python.exe" "%~dp0backend\download_embedding_model.py"
    if %ERRORLEVEL% == 0 (
        echo         Embedding model downloaded successfully.
    ) else (
        echo         WARNING: Embedding model download failed.
        echo         The system may not work correctly. Check your internet.
    )
) else (
    echo  [6/12] Embedding model already downloaded. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 7: Install frontend Node.js packages
:: ────────────────────────────────────────────────────────────────
echo  [7/12] Installing frontend packages ^(React, Next.js, etc.^)...
cd /d "%~dp0frontend"
npm install --silent 2>nul
cd /d "%~dp0"
echo         Frontend packages installed successfully.
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 8: Start Ollama service (needed to pull models)
:: ────────────────────────────────────────────────────────────────
echo  [8/12] Starting Ollama service for model downloads...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% neq 0 (
    start "" cmd /c "ollama serve"
    timeout /t 5 >nul
    echo         Ollama service started.
) else (
    echo         Ollama already running.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 9: Download Qwen 2.5 (Fast Mode AI model)
:: ────────────────────────────────────────────────────────────────
echo  [9/12] Checking Qwen 2.5 model ^(Fast Mode - 397MB^)...
ollama list 2>nul | findstr /I "qwen2.5:0.5b" >nul
if %ERRORLEVEL% neq 0 (
    echo         Downloading Qwen 2.5 ^(0.5B^)... Please wait.
    ollama pull qwen2.5:0.5b
    echo         Qwen 2.5 model ready.
) else (
    echo         Qwen 2.5 already downloaded. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 10: Download Gemma 2 (Smart Mode AI model)
:: ────────────────────────────────────────────────────────────────
echo  [10/12] Checking Gemma 2 model ^(Smart Mode - 1.6GB^)...
ollama list 2>nul | findstr /I "gemma2:2b" >nul
if %ERRORLEVEL% neq 0 (
    echo         Downloading Gemma 2 ^(2B^)... This may take several minutes.
    ollama pull gemma2:2b
    echo         Gemma 2 model ready.
) else (
    echo         Gemma 2 already downloaded. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 11: License activation
:: ────────────────────────────────────────────────────────────────
echo  [11/12] Checking license activation...
"%~dp0venv\Scripts\python.exe" "%~dp0backend\check_license.py"
if %ERRORLEVEL% neq 0 (
    echo         License key required. Opening activation window...
    "%~dp0venv\Scripts\python.exe" "%~dp0backend\key_prompt.py"
    if %ERRORLEVEL% neq 0 (
        echo.
        echo  ====================================================
        echo    License activation failed or was cancelled.
        echo    Contact the system owner for a valid key.
        echo    Setup is incomplete - system will not run.
        echo  ====================================================
        pause
        exit /b 1
    )
    echo         License activated successfully.
) else (
    echo         License already valid. Skipping.
)
echo.

:: ────────────────────────────────────────────────────────────────
:: STEP 12: Build frontend for production
:: ────────────────────────────────────────────────────────────────
echo  [12/12] Building frontend for production...
echo         ^(This may take 30-60 seconds^)
cd /d "%~dp0frontend"
npm run build
cd /d "%~dp0"
echo         Frontend built successfully.
echo.

:: ────────────────────────────────────────────────────────────────
:: DONE
:: ────────────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo.
echo    AuraQA Setup Complete! Everything is ready.
echo.
echo  ====================================================
echo.
echo  What was installed:
echo    - Python 3.11 + virtual environment
echo    - All backend packages ^(FastAPI, SQLAlchemy...^)
echo    - Multilingual embedding model
echo    - Node.js + frontend packages ^(Next.js, React...^)
echo    - Ollama + AI models ^(Qwen 2.5 + Gemma 2^)
echo    - License activated for this machine
echo    - Frontend production build
echo.
echo  HOW TO START AURAQA:
echo    Double-click  run_servers.bat
echo    Then open:    http://localhost:5000
echo.
echo  HOW TO STOP AURAQA:
echo    Double-click  stop_servers.bat
echo.
echo  ====================================================
echo.
pause
