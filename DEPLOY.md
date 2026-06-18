# Deploy Sampada 2.0 Bot to Streamlit Cloud (Live)

> **Hybrid Deployment:** Cloud dashboard for AI parsing + data prep. Local runner for actual browser automation.

---

## Why Hybrid?

| Feature | Cloud | Local Machine | Reason |
|---------|-------|---------------|--------|
| AI Document Parsing | ✅ | ✅ | Gemini API works anywhere |
| Hindi/English Review UI | ✅ | ✅ | Streamlit runs in browser |
| Data Storage | ✅ | ⚠️ | Cloud uses session state + JSON export |
| Headed Chrome Browser | ❌ | ✅ | Cloud servers have no GUI |
| Biometric RD Service | ❌ | ✅ | localhost:11100 needs local loopback |
| Browser Profile / Cookies | ❌ | ✅ | Must use your local Chrome profile |
| Captcha / OTP / Video KYC | ❌ | ✅ | Needs human interaction + camera |

**Conclusion:** Deploy the dashboard to the cloud, but run the browser automation on your local Windows machine.

---

## Deployment Option A: Streamlit Community Cloud (Recommended)

### Step 1: Push to GitHub

Create a new GitHub repository and upload the project:

```bash
cd sampada-bot
git init
git add .
git commit -m "Initial Sampada 2.0 Bot"
# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/sampada-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository: `YOUR_USERNAME/sampada-bot`
5. **Main file path:** `app/streamlit_cloud.py`
6. Click **"Deploy"**

### Step 3: Add Secrets (Gemini API Key)

In the Streamlit Cloud dashboard for your app:
1. Click **"Settings"** (gear icon)
2. Go to **"Secrets"** tab
3. Add:
```toml
GEMINI_API_KEY = "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```
4. Click **"Save"**
5. The app will restart automatically

> **Never commit your `.env` or API keys to GitHub.** Streamlit Cloud secrets are stored securely server-side.

### Step 4: Access Your Live App

After deployment, you get a URL like:
```
https://sampada-bot-abc123.streamlit.app
```

Share this URL with anyone who needs to upload and parse documents. The data is session-based (refreshing the page clears it), so users should **export JSON** before closing.

---

## Deployment Option B: Local Network (No Cloud)

If you don't want to use Streamlit Cloud, run the app on your machine and access it from other devices on your Wi-Fi:

```bash
cd sampada-bot
pip install -r requirements.txt
streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Then access from any device on your network:
```
http://YOUR_PC_IP:8501
```

Find your PC IP:
```powershell
# Windows
ipconfig
# Look for "IPv4 Address" under your Wi-Fi adapter
```

> ⚠️ **Security:** This exposes the app to your local network. Don't use this on public Wi-Fi without authentication.

---

## Using the Deployed Cloud App

### Workflow: Cloud → Local

#### Phase 1: Prepare Data in the Cloud
1. Open the deployed app URL in your browser
2. Enter your **Gemini API Key** in the sidebar
3. Click **"New Registry"** to create a case
4. Go to **"Upload & Parse"** tab
5. Upload ID card scans (Aadhaar, PAN) → click **Parse** for each
6. Upload property documents → click **Parse Property**
7. Go to **"Review & Edit"** tab
8. Verify and correct all Hindi/English fields
9. Mark each party as **Verified**
10. Save property boundaries

#### Phase 2: Export JSON
1. Go to **"Export for Local Runner"** tab
2. Click **"Download JSON for Local Runner"**
3. Save the file (e.g., `registry_1_for_local.json`)

#### Phase 3: Run Local Automation
1. On your **Windows machine**, download the JSON file
2. Open PowerShell / CMD in the `sampada-bot` folder
3. Run:
```powershell
python local_runner.py --registry "C:\Users\You\Downloads\registry_1_for_local.json"
```
4. A **headed Chrome window** opens at the Sampada login page
5. **Log in manually** (username, password, captcha, OTP)
6. Press **ENTER** in the terminal to resume the bot
7. The bot fills:
   - Deed category and instrument
   - District → Tehsil → Halka → Ward dropdowns
   - All party details (Buyer, Seller, Witness)
   - Property plot number, area, boundaries
8. Bot **pauses** at KYC/Biometrics — complete them, then press ENTER
9. Bot **pauses** at Payment — pay stamp duty, then press ENTER
10. Done!

---

## What Gets Exported in the JSON

```json
{
  "registry": {
    "id": 1,
    "title": "Registry #1",
    "deed_category": "Sale Deed",
    "status": "draft"
  },
  "parties": [
    {
      "role": "Buyer 1",
      "name_english": "Ramesh Kumar",
      "name_hindi": "रमेश कुमार",
      "father_husband_name_english": "Suresh Kumar",
      "father_husband_name_hindi": "सुरेश कुमार",
      "dob": "15-08-1985",
      "gender": "Male",
      "category": "General",
      "address_english": "123 Scheme 54, Indore",
      "address_hindi": "123 स्कीम 54, इंदौर",
      "id_type": "Aadhaar",
      "id_number": "123456789012",
      "pan_number": "ABCDE1234F",
      "mobile_number": "9876543210",
      "verified": 1
    }
  ],
  "property": {
    "district": "Indore",
    "tehsil": "Indore",
    "area_type": "Urban",
    "ward_colony_name": "Scheme 54",
    "plot_number": "123",
    "total_area_sqmt": 150.0,
    "constructed_area_sqmt": 120.0,
    "road_width_mt": 9.0,
    "boundaries": {
      "east": "Plot 124",
      "west": "Road",
      "north": "Plot 122",
      "south": "Plot 126"
    }
  },
  "documents": [
    {"doc_type": "id_scan", "role_hint": "Buyer 1", "file_name": "aadhaar.jpg"}
  ]
}
```

---

## Files for Deployment

| File | Purpose | Deploy to Cloud? |
|------|---------|------------------|
| `app/streamlit_cloud.py` | Cloud dashboard (upload, parse, review, export) | ✅ Yes |
| `local_runner.py` | Local Playwright automation (reads JSON export) | ❌ No — runs on user's PC |
| `requirements.txt` | Python dependencies | ✅ Yes |
| `.streamlit/config.toml` | Streamlit theme config | ✅ Yes |
| `app/streamlit_app.py` | Original desktop version (SQLite-based) | ❌ No — use `streamlit_cloud.py` instead |
| `modules/` | Core modules (config, db, AI parser) | ✅ Partial (cloud version doesn't use SQLite) |

---

## Troubleshooting

### "No module named 'playwright'" when running local_runner.py
```bash
pip install playwright
playwright install chromium
```

### "Gemini API key not set" in cloud app
- Add the key in the sidebar text box
- Or add it to Streamlit Cloud Secrets (Settings → Secrets)

### Exported JSON doesn't load in local_runner
- Make sure the JSON is saved with UTF-8 encoding
- The file should have `"registry"`, `"parties"`, and `"property"` keys

### Chrome doesn't open (local_runner)
- Close all existing Chrome windows first
- Run as Administrator if permission denied
- Check `playwright install chromium` completed successfully

### Dropdowns not filling on Sampada portal
- The portal UI may have changed. The local runner uses **heuristic matching** (placeholder text).
- If selectors fail, open the Chrome DevTools (F12) on the Sampada page, inspect the input fields, and update `local_runner.py` with the correct placeholder/label text.

---

## Security Checklist

| Concern | Mitigation |
|---------|------------|
| API Key exposed | Use Streamlit Cloud Secrets (never commit to GitHub) |
| Registry data | Exported JSON is saved on user's device only |
| Portal credentials | User types them manually — bot never stores passwords |
| Biometric data | Never leaves the local RD Service / browser |
| Payment | User pays manually — bot doesn't process payments |

---

## Quick Reference

```bash
# Deploy to Streamlit Cloud
git push origin main
# Then: https://streamlit.io/cloud → New app → Select repo

# Run local automation
python local_runner.py --registry registry_1_for_local.json

# Run local dashboard (no cloud)
streamlit run app/streamlit_app.py --server.address 0.0.0.0
```

**Happy deploying! 🚀**
