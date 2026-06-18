# Sampada 2.0 e-Registry Bot — Complete Run Guide

> **Target OS:** Windows 10/11 (recommended for biometric RD Services). Linux/macOS also supported.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step-by-Step Installation](#step-by-step-installation)
3. [Environment Setup](#environment-setup)
4. [Launch the Dashboard](#launch-the-dashboard)
5. [Using the Bot (Workflow)](#using-the-bot-workflow)
6. [Run Tests](#run-tests)
7. [Troubleshooting](#troubleshooting)
8. [Quick Reference](#quick-reference)

---

## Prerequisites

| Requirement | Version | How to Check |
|-------------|---------|--------------|
| **Python** | 3.10 or higher | `python --version` |
| **pip** | 21.0+ | `pip --version` |
| **Node.js** | 18+ (for Playwright) | `node --version` |
| **Git** | Any (for cloning) | `git --version` |

### Check if you have them installed

**Windows (PowerShell):**
```powershell
python --version
pip --version
node --version
```

**If anything is missing:**
- **Python:** Download from [python.org](https://www.python.org/downloads/). **Check "Add Python to PATH" during install.**
- **Node.js:** Download from [nodejs.org](https://nodejs.org/)
- **Git:** Download from [git-scm.com](https://git-scm.com/download/win)

---

## Step-by-Step Installation

### Step 1: Navigate to the Project Folder

**If you already have the files:**
```powershell
# Windows PowerShell
cd C:\Users\Adity\Documents\kimi\workspace\sampada-bot
```

```bash
# Linux / macOS
cd ~/Documents/kimi/workspace/sampada-bot
```

### Step 2: Create a Virtual Environment (Recommended)

This isolates the bot's dependencies from your system Python.

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> You should see `(venv)` in your terminal prompt.

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**What gets installed:**
- `streamlit` — the web dashboard
- `google-generativeai` — Gemini AI API
- `playwright` — browser automation engine
- `Pillow` — image handling
- `python-dotenv` — environment variables
- `pydantic` — data validation

### Step 4: Install Playwright Browsers

Playwright needs to download its own browser binaries (Chromium, Firefox, WebKit).

```bash
playwright install chromium
```

> This downloads ~150MB of browser data. It may take a few minutes.

### Step 5: Verify Installation

```bash
python run.py
```

**Expected output:**
```
🏛️  Sampada 2.0 e-Registry Co-Pilot
========================================
Initialising database...
Database ready at: ...\sampada-bot\data\db\sampada_state.db

To launch the dashboard, run:
   streamlit run app/streamlit_app.py

Make sure you have:
  1. Set GEMINI_API_KEY in .env or environment
  2. Installed Playwright browsers:  playwright install chromium
  3. Installed Python deps:  pip install -r requirements.txt
```

If you see this, the core modules are working!

---

## Environment Setup

### Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"**
3. Copy the key (starts with `AIza...`)

### Create the `.env` File

In the `sampada-bot` folder, create a file named `.env`:

**Windows:**
```powershell
notepad .env
```

**Linux/macOS:**
```bash
nano .env
```

**Paste this (replace with your actual key):**
```env
GEMINI_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Save and close.**

> ⚠️ **Never share your `.env` file.** It contains your API key.

---

## Launch the Dashboard

### Method 1: Streamlit (Recommended)

```bash
streamlit run app/streamlit_app.py
```

**What happens:**
- Streamlit starts a local web server
- Your browser opens automatically at `http://localhost:8501`
- You see the dark-themed Sampada Co-Pilot dashboard

### Method 2: Direct Python

```bash
python -c "import streamlit.web.cli as stcli; import sys; sys.argv=['streamlit', 'run', 'app/streamlit_app.py']; stcli.main()"
```

### Access from Another Device (Optional)

By default, Streamlit only listens on `localhost`. To access from another computer on your network:

```bash
streamlit run app/streamlit_app.py --server.address 0.0.0.0
```

Then visit `http://YOUR_PC_IP:8501` from the other device.

---

## Using the Bot (Workflow)

### Step-by-Step User Guide

#### 1. Create a New Registry
- Look at the **left sidebar**
- Click **➕ New Registry**
- A new case appears in the sidebar list
- Click it to load it in the main panel

#### 2. Upload & Parse Documents
- Click the **📤 Upload & Parse** tab
- **Left column:** Upload ID card scans (Aadhaar, PAN, Voter ID)
  - For each file, select its role: **Buyer 1**, **Seller 1**, **Witness 1**, etc.
  - Click **🔍 Parse** — the AI reads the image and extracts data
- **Right column:** Upload property documents (deed, plan, tax receipt)
  - Click **🔍 Parse Property** — the AI extracts plot number, area, boundaries

> 💡 **Tip:** The AI may take 5–15 seconds per image. Wait for the success message.

#### 3. Review & Edit (Human-in-the-Loop)
- Click the **✍️ Review & Edit** tab
- You see a **side-by-side view**:
  - **Left:** Original scanned image
  - **Right:** Editable text fields (English + Hindi)
- **Check each field:**
  - Name spelling
  - Hindi transliteration (e.g., "Ramesh" → "रमेश")
  - Aadhaar number (12 digits, no spaces)
  - PAN format (ABCDE1234F)
  - Mobile number (10 digits)
  - Date format (DD-MM-YYYY)
- **Fix mistakes:** Edit any field directly
- **Re-transliterate:** Click **🔁 Transliterate Name** to ask AI for Hindi again
- **Mark Verified:** Check the **Verified** checkbox for each party
- **Save:** Click **💾 Save Party** after editing
- **Edit Property:** Expand the property section, fix plot number / area / boundaries, click **💾 Save Property**

> ⚠️ **You must mark all parties as "Verified" before automation can start.**

#### 4. Start Browser Automation
- Click the **🤖 Automation** tab
- Select **Deed Category** from the dropdown (e.g., "Sale Deed")
- Optionally enter **Instrument Type**
- Click **🤖 Start Browser Automation**

**What happens:**
1. A **real Chrome browser window** opens (headed mode)
2. It navigates to `https://sampada.mpigr.gov.in/#/clogin`
3. The bot **pauses** immediately — you must log in manually

#### 5. Log In Manually (Secure)
- In the Chrome window, enter your **Username** and **Password**
- Solve the **Captcha** (image or math)
- Enter the **OTP** sent to your mobile
- Click **Login**
- Wait for the **Dashboard** to load (`https://sampada.mpigr.gov.in/#/citizen/dashboard`)

#### 6. Resume the Bot
- Go back to the **Streamlit dashboard**
- Click **▶️ Resume Bot**
- The bot detects the dashboard and continues automatically

#### 7. Watch Automation Fill Forms
The bot will:
- Navigate to **e-Registry**
- Select your **Deed Category** and **Instrument**
- Fill **District → Tehsil → Patwari Halka → Ward** dropdowns (waits for each to load)
- Add and fill **Party Details** (Buyer, Seller, Witness) one by one
- Fill **Property Details** (plot number, area, boundaries)
- Navigate to the **Draft** section

#### 8. Pause at KYC / Biometrics
When the bot reaches the **e-KYC / Video KYC / Biometric** step:
- It **pauses** and shows a yellow notification
- You must:
  - Complete **Video KYC** (face the camera)
  - Place finger on **biometric scanner** (Mantra/Morpho/Startek)
  - Wait for the RD Service to capture and verify
- After completion, click **▶️ Resume Bot** in the dashboard

#### 9. Pause at Payment
When the bot reaches the **Payment Gateway**:
- It **pauses** again
- You manually pay the **stamp duty** and **registration fees**
- After payment success, click **▶️ Resume Bot**

#### 10. Completion
- The bot marks the registry as **completed**
- Status changes to green in the sidebar
- You can start a new registry anytime

---

## Run Tests

### Quick Test (No API Key Needed)
```bash
python tests/test_integration.py
```

**Expected:** 6 tests run, all pass. Tests database, data cleaning, mock AI, and imports.

### Full Test Suite (Requires pytest + Pillow)
```bash
pip install pytest Pillow
pytest tests/test_all.py -v
```

**Expected:** 30+ tests pass, covering all CRUD operations, data cleaning, JSON extraction, and mock Gemini responses.

### Test with Real Gemini API
```bash
# Set your key first
$env:GEMINI_API_KEY="AIzaSyB..."        # Windows PowerShell
export GEMINI_API_KEY="AIzaSyB..."      # Linux/macOS

# Run a quick OCR test
python -c "
from modules.ai_parser import parse_id_card
import json
result = parse_id_card('path/to/your/aadhaar.jpg', 'Buyer 1')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

---

## Troubleshooting

### Problem: `python` or `pip` not recognized
**Windows Fix:**
```powershell
# Add Python to PATH manually (adjust version)
$env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311"
$env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\Scripts"
```

**Or reinstall Python** and check **"Add Python to PATH"** during setup.

---

### Problem: `ModuleNotFoundError: No module named 'streamlit'`
**Fix:** Make sure your virtual environment is activated.
```powershell
# Windows
venv\Scripts\activate

# Then reinstall
pip install -r requirements.txt
```

---

### Problem: `playwright install chromium` fails
**Fix:** Install Node.js first, then retry:
```bash
node --version    # should show v18+ or v20+
playwright install chromium
```

If still failing, try:
```bash
# Force reinstall
pip install --force-reinstall playwright
playwright install chromium
```

---

### Problem: `GEMINI_API_KEY not set` warning in dashboard
**Fix:** Create the `.env` file in the **same folder** as `run.py`:
```powershell
# Windows PowerShell - create .env file
Set-Content -Path .env -Value 'GEMINI_API_KEY=AIzaSyB...'
```

Or set it as a system environment variable:
```powershell
# Windows PowerShell (temporary, for this session)
$env:GEMINI_API_KEY = "AIzaSyB..."

# Windows PowerShell (permanent)
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIzaSyB...", "User")
```

---

### Problem: Browser doesn't open / automation fails
**Checklist:**
1. Did you run `playwright install chromium`?
2. Is Chrome/Edge already running? Close all instances first.
3. Check if your antivirus is blocking Playwright.
4. Try running the bot as Administrator (Windows) if permission errors occur.

**Debug mode:**
```python
# Run this to see what Playwright sees
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=False)
page = browser.new_page()
page.goto("https://sampada.mpigr.gov.in")
page.screenshot(path="debug.png")
browser.close()
```

---

### Problem: Hindi transliteration is wrong
**Fix:** The AI makes mistakes. Use the **Review & Edit** tab to:
1. Manually correct the Hindi field
2. Click **🔁 Transliterate Name** to ask the AI again
3. The second prompt is specifically tuned for phonetic transliteration, not translation

---

### Problem: Bot can't find dropdowns / form fields on Sampada portal
**Fix:** The portal uses Angular with dynamic class names. The bot uses **heuristic matching** (placeholder text, aria-labels). If the portal UI changes:

1. Open Chrome DevTools (F12) on the Sampada portal
2. Inspect the input field you want to fill
3. Note its `placeholder`, `aria-label`, or nearby label text
4. Edit `modules/playwright_automation.py` → `_fill_party_form()` method
5. Add a new matching condition in the `combined` string check

**Example:**
```python
# If the portal changes "Father's Name" to "Parent Name"
if "parent" in combined and "hindi" in combined:
    inp.fill(fields["father_husband_name_hindi"])
```

---

### Problem: SQLite database is locked / corrupted
**Fix:**
```bash
# Delete the database and let it recreate
rm data/db/sampada_state.db        # Linux/macOS
Remove-Item data/db/sampada_state.db   # Windows PowerShell

# Then run
python run.py
```

All data will be lost, but the schema will be fresh.

---

### Problem: Streamlit port 8501 is already in use
**Fix:**
```bash
# Use a different port
streamlit run app/streamlit_app.py --server.port 8502
```

Or kill the existing process:
```powershell
# Windows
netstat -ano | findstr :8501
# Note the PID, then:
taskkill /PID <PID> /F
```

---

## Quick Reference

### One-Command Start (After First Setup)

**Windows PowerShell:**
```powershell
cd C:\Users\Adity\Documents\kimi\workspace\sampada-bot
venv\Scripts\activate
streamlit run app/streamlit_app.py
```

**Linux/macOS:**
```bash
cd ~/Documents/kimi/workspace/sampada-bot
source venv/bin/activate
streamlit run app/streamlit_app.py
```

### Common Commands

| Command | Purpose |
|---------|---------|
| `python run.py` | Verify setup & initialize database |
| `streamlit run app/streamlit_app.py` | Launch the dashboard |
| `python tests/test_integration.py` | Quick test (no API key) |
| `pytest tests/test_all.py -v` | Full test suite |
| `playwright install chromium` | Install browser for automation |
| `pip install -r requirements.txt` | Install all Python dependencies |
| `venv\Scripts\activate` | Activate virtual environment (Windows) |
| `source venv/bin/activate` | Activate virtual environment (Linux/macOS) |

### File Locations

| File | Path |
|------|------|
| Dashboard | `app/streamlit_app.py` |
| Database | `data/db/sampada_state.db` |
| Uploaded scans | `data/uploads/` |
| Logs & screenshots | `data/logs/` |
| Environment config | `.env` |
| AI prompts | `prompts/vision_prompts.py` |

---

## Need Help?

If you encounter an issue not covered here:
1. Check the **Automation Logs** tab in the dashboard for error messages
2. Look at `data/logs/` for any screenshots the bot saved at failure points
3. Run the integration test: `python tests/test_integration.py`
4. Check if your API key is valid at [Google AI Studio](https://aistudio.google.com/app/apikey)

**Happy automating! 🏛️**
