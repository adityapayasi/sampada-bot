# Sampada 2.0 e-Registry Automation Bot

A desktop **Co-Pilot** for registry writers/typists to automate data entry on the **MPIGR Sampada 2.0** portal (`https://sampada.mpigr.gov.in/`).

## Features

| Phase | Feature | Status |
|-------|---------|--------|
| **1** | 🖼️ AI Vision OCR (Gemini 1.5 Flash) for ID cards & property docs | ✅ |
| **1** | 📝 English → Hindi phonetic transliteration | ✅ |
| **1** | 🗃️ SQLite state management (drafts, resume, checkpoints) | ✅ |
| **1** | 🖥️ Streamlit dark-mode dashboard (Upload, Review, Automate) | ✅ |
| **2** | 🎭 Playwright headed-browser automation (preserves login & biometrics) | ✅ |
| **3** | 📍 Nested dropdown sync (District → Tehsil → Halka → Ward) | ✅ |
| **3** | 🪪 Party form auto-fill (Buyer, Seller, Witness) | ✅ |
| **3** | 🏠 Property details & boundaries auto-fill | ✅ |
| **4** | ⏸️ HITL pause/resume at Captcha, OTP, KYC, Biometrics, Payment | ✅ |
| **4** | 🛡️ Error logging & retry logic | ✅ |

## Quick Start

### 1. Install Python dependencies
```bash
cd sampada-bot
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure API key
Copy `.env.example` to `.env` and add your **Google Gemini API key**:
```bash
cp .env.example .env
# Edit .env → GEMINI_API_KEY=your_key_here
```

### 3. Launch the dashboard
```bash
streamlit run app/streamlit_app.py
```

### 4. Workflow
1. **Sidebar** → click **"New Registry"** to create a case.
2. **Upload & Parse** tab → upload ID cards & property scans, assign roles, click **Parse**.
3. **Review & Edit** tab → verify Hindi/English fields, fix transliteration, mark **Verified**.
4. **Automation** tab → select Deed Category, click **Start Browser Automation**.
5. A **headed Chrome window** opens. Log in manually, solve captcha/OTP, then click **Resume** in the dashboard.
6. The bot fills dropdowns, party details, and property forms. It **pauses** at KYC/Biometrics and Payment for you to complete securely.

## Project Structure

```
sampada-bot/
├── app/
│   └── streamlit_app.py        # Main dashboard (tabs: Upload, Review, Automate)
├── modules/
│   ├── config.py               # Constants, URLs, state machine
│   ├── db_manager.py           # SQLite CRUD & persistence
│   ├── ai_parser.py            # Gemini Vision API wrapper
│   ├── transliterator.py       # English → Hindi phonetic helper
│   └── playwright_automation.py # Playwright bot logic
├── prompts/
│   └── vision_prompts.py       # Gemini system prompts
├── data/
│   ├── uploads/                # Scanned document storage
│   ├── db/                     # SQLite database
│   └── logs/                   # Screenshots & logs
├── requirements.txt
├── .env.example
└── run.py
```

## Tech Stack

- **UI:** Streamlit (dark theme, premium layout)
- **AI Engine:** Google Gemini 1.5 Flash/Pro Vision API
- **Browser Automation:** Playwright (Python) — headed mode with real Chrome profile
- **State:** SQLite (drafts, parties, properties, checkpoints)
- **OS:** Windows 10/11 (recommended for biometric RD Services)

## Important Notes

- **Headed browser is mandatory.** Government portals require real browser sessions, geolocation, and access to local `http://127.0.0.1:11100` RD Services for biometric scanners (Mantra, Morpho, Startek).
- **Human-in-the-Loop (HITL)** is enforced for:
  - Login + Captcha + OTP
  - e-KYC / Video KYC
  - Biometric fingerprint capture
  - Payment gateway (stamp duty)
- The bot **never** stores your portal password or processes payments automatically.
- Geolocation is set to **Indore, MP** by default; change in `modules/config.py` if needed.

## License

Internal use only. Not affiliated with MPIGR or Government of Madhya Pradesh.
