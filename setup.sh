#!/usr/bin/env bash
# ============================================================
# Sampada 2.0 Bot — Quick Start Script for Linux / macOS
# ============================================================
# Run this from the sampada-bot folder:
#   chmod +x setup.sh
#   ./setup.sh
# ============================================================

set -e

echo ""
echo "  ============================================"
echo "   Sampada 2.0 e-Registry Co-Pilot"
echo "  ============================================"
echo ""

# Check if we're in the right folder
if [ ! -f "app/streamlit_app.py" ]; then
    echo "  ERROR: This script must be run from the sampada-bot folder."
    exit 1
fi

# Check Python
echo "  Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: Python 3 is not installed."
    echo "  Please install Python 3.10+ from your package manager."
    exit 1
fi
python3 --version

# Check / Create virtual environment
echo ""
echo "  Checking virtual environment..."
if [ ! -d "venv" ]; then
    echo "  Creating venv..."
    python3 -m venv venv
fi

# Activate
echo "  Activating venv..."
source venv/bin/activate

# Install dependencies
echo ""
echo "  Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Check Playwright browsers
echo ""
echo "  Checking Playwright browsers..."
if ! python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True); p.stop()" 2>/dev/null; then
    echo "  Installing Chromium..."
    playwright install chromium
fi

# Check .env
echo ""
echo "  Checking .env file..."
if [ ! -f ".env" ]; then
    echo "GEMINI_API_KEY=your_key_here" > .env
    echo "  Created .env — please add your Gemini API key."
    echo "  Get one at: https://aistudio.google.com/app/apikey"
else
    echo "  .env found."
fi

# Init database
echo ""
echo "  Initializing database..."
python3 run.py

# Done
echo ""
echo "  ============================================"
echo "   Setup Complete!"
echo "  ============================================"
echo ""
echo "  Quick commands:"
echo "    Launch dashboard:  streamlit run app/streamlit_app.py"
echo "    Run tests:         python3 tests/test_integration.py"
echo "    Run pytest:        pytest tests/test_all.py -v"
echo ""

read -p "  Launch dashboard now? (Y/N): " launch
if [ "$launch" = "Y" ] || [ "$launch" = "y" ]; then
    streamlit run app/streamlit_app.py
else
    echo "  Done. Run 'streamlit run app/streamlit_app.py' when ready."
fi
