@echo off
REM ============================================================
REM Sampada 2.0 Bot — Quick Start Script for Windows
REM ============================================================
REM This script sets up the environment and launches the bot.
REM Run this from the sampada-bot folder.
REM ============================================================

echo.
echo  ============================================
echo   Sampada 2.0 e-Registry Co-Pilot
echo  ============================================
echo.

REM Check if we're in the right folder
if not exist "app\streamlit_app.py" (
    echo  ERROR: This script must be run from the sampada-bot folder.
    echo  Please cd into the project directory first.
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo  [OK] Python found.

REM Check / Create virtual environment
if not exist "venv" (
    echo.
    echo  Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
) else (
    echo  [OK] Virtual environment exists.
)

REM Activate virtual environment
echo.
echo  Activating virtual environment...
call venv\Scripts\activate

REM Install / Upgrade dependencies
echo.
echo  Installing Python dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo  ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo  [OK] Dependencies installed.

REM Check Playwright browsers
echo.
echo  Checking Playwright browsers...
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo  Playwright browsers not found. Installing...
    playwright install chromium
    if errorlevel 1 (
        echo  WARNING: Failed to install Chromium. You may need to run: playwright install chromium
    )
) else (
    echo  [OK] Playwright browsers ready.
)

REM Check .env file
echo.
if not exist ".env" (
    echo  WARNING: .env file not found.
    echo  Creating .env.example for you to edit...
    echo  GEMINI_API_KEY=your_key_here > .env
    echo  ^# Open .env in Notepad and add your real Gemini API key.
    echo  ^# Get one at: https://aistudio.google.com/app/apikey
) else (
    echo  [OK] .env file found.
)

REM Initialize database
echo.
echo  Initializing database...
python run.py

REM Done
echo.
echo  ============================================
echo   Setup complete!
echo  ============================================
echo.
echo  To launch the dashboard, run:
echo    streamlit run app\streamlit_app.py
echo.
echo  Or run tests:
echo    python tests\test_integration.py
echo.

set /p choice="Launch dashboard now? (Y/N): "
if /i "%choice%"=="Y" (
    echo.
    echo  Launching Streamlit dashboard...
    streamlit run app\streamlit_app.py
) else (
    echo.
    echo  You can launch anytime with: streamlit run app\streamlit_app.py
    pause
)
