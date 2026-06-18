#!/usr/bin/env pwsh
# ============================================================
# Sampada 2.0 Bot — Quick Start Script for Windows PowerShell
# ============================================================
# Run this from the sampada-bot folder:
#   .\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   Sampada 2.0 e-Registry Co-Pilot" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right folder
if (-not (Test-Path "app\streamlit_app.py")) {
    Write-Host "  ERROR: This script must be run from the sampada-bot folder." -ForegroundColor Red
    Write-Host "  Please cd into the project directory first." -ForegroundColor Red
    exit 1
}

# Check Python
Write-Host "  Checking Python..." -NoNewline
$pythonVersion = python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "  ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host " OK ($pythonVersion)" -ForegroundColor Green

# Check / Create virtual environment
Write-Host "  Checking virtual environment..." -NoNewline
if (-not (Test-Path "venv")) {
    Write-Host " creating..." -NoNewline -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host " FAIL" -ForegroundColor Red
        exit 1
    }
}
Write-Host " OK" -ForegroundColor Green

# Activate
Write-Host "  Activating venv..." -NoNewline
.\venv\Scripts\Activate.ps1
Write-Host " OK" -ForegroundColor Green

# Install dependencies
Write-Host "  Installing dependencies..." -NoNewline
$pipOutput = pip install --upgrade pip -q 2>&1
$pipOutput = pip install -r requirements.txt -q 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "  ERROR: pip install failed. Check your internet connection." -ForegroundColor Red
    exit 1
}
Write-Host " OK" -ForegroundColor Green

# Check Playwright browsers
Write-Host "  Checking Playwright browsers..." -NoNewline
try {
    $null = python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True); p.stop()" 2>$null
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " MISSING" -ForegroundColor Yellow
    Write-Host "  Installing Chromium for Playwright..." -ForegroundColor Yellow
    playwright install chromium
}

# Check .env
Write-Host "  Checking .env file..." -NoNewline
if (-not (Test-Path ".env")) {
    Write-Host " NOT FOUND" -ForegroundColor Yellow
    "GEMINI_API_KEY=your_key_here" | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "  Created .env — please add your Gemini API key." -ForegroundColor Yellow
    Write-Host "  Get one at: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
} else {
    Write-Host " OK" -ForegroundColor Green
}

# Init database
Write-Host ""
Write-Host "  Initializing database..." -ForegroundColor Cyan
python run.py

# Done
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick commands:"
Write-Host "    Launch dashboard:  streamlit run app\streamlit_app.py" -ForegroundColor White
Write-Host "    Run tests:         python tests\test_integration.py" -ForegroundColor White
Write-Host "    Run pytest:        pytest tests\test_all.py -v" -ForegroundColor White
Write-Host ""

$launch = Read-Host "  Launch dashboard now? (Y/N)"
if ($launch -eq "Y" -or $launch -eq "y") {
    Write-Host "  Launching..." -ForegroundColor Cyan
    streamlit run app\streamlit_app.py
} else {
    Write-Host "  Done. Run 'streamlit run app\streamlit_app.py' when ready." -ForegroundColor Green
}
