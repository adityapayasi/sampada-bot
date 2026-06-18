# Sampada 2.0 Bot — Testing Guide

## Quick Start

Run the **no-API-key integration test**:
```bash
cd sampada-bot
python tests/test_integration.py
```

Run the **full pytest suite** (requires pytest + Pillow):
```bash
cd sampada-bot
pip install pytest Pillow
pytest tests/test_all.py -v
```

---

## Test Layers

### Layer 1: Unit Tests (`tests/test_all.py`)
| Test Class | What It Tests |
|------------|---------------|
| `TestRegistryCRUD` | Create, read, update, list registries |
| `TestPartyCRUD` | Add, update, delete parties; multiple roles |
| `TestPropertyCRUD` | Save/overwrite property with boundaries |
| `TestDocumentCRUD` | Upload tracking by type and role |
| `TestAutomationLog` | Step-by-step logging with screenshots |
| `TestCleanIdData` | Data normalization (dates, IDs, gender, mobile) |
| `TestExtractJson` | Markdown-fenced JSON vs raw JSON parsing |
| `TestTransliterator` | Mocked Gemini transliteration call |
| `TestConfig` | Constants, paths, regex validation |
| `TestAIParserIntegration` | End-to-end mock Gemini ID + property parsing |
| `TestEndToEndFlow` | Full lifecycle without external APIs |

### Layer 2: Integration Tests (`tests/test_integration.py`)
Runs without `pytest` — just plain Python. Covers:
- Config validation
- SQLite full CRUD chain
- Data cleaning pipelines
- Mock Gemini responses (no real API call)
- Module import smoke tests

### Layer 3: Manual UI Testing

#### Step 1 — Environment Setup
```bash
cd sampada-bot
pip install -r requirements.txt
playwright install chromium
```

Create `.env`:
```env
GEMINI_API_KEY=your_actual_key_here
```

#### Step 2 — Launch Dashboard
```bash
streamlit run app/streamlit_app.py
```

#### Step 3 — Test Checklist

| # | Test | Expected Result |
|---|------|-----------------|
| 1 | Click **"New Registry"** in sidebar | New registry appears in list, main panel shows empty state |
| 2 | Click a registry from sidebar | Main panel shows that registry's tabs |
| 3 | Upload an ID image (JPG/PNG) | File appears in upload area; role selector visible |
| 4 | Select role "Buyer 1" and click **Parse** | After spinner, success message shows extracted name; party saved to DB |
| 5 | Go to **Review & Edit** tab | Image shown on left; editable fields on right; Hindi/English side-by-side |
| 6 | Edit a name field and click **Save Party** | Field updates; database reflects change |
| 7 | Click **Transliterate Name** | If API key is set, Hindi field updates; if not, shows error |
| 8 | Mark party as **Verified** | Check box saves `verified=1` to DB |
| 9 | Upload property document and **Parse** | Property JSON shown; saved to DB |
| 10 | In Review tab, edit property boundaries | North/South/East/West fields save correctly |
| 11 | All parties verified + property saved | Dashboard shows green "Ready for automation" message |
| 12 | Click **Confirm & Go to Automation** | Switches to Automation tab (or sets state flag) |
| 13 | Select Deed Category, click **Start Browser Automation** | Chrome window opens; portal login page loads; bot pauses |
| 14 | Click **Resume Bot** without logging in | Bot checks for dashboard; if not found, may log error |
| 15 | Log in manually, then click **Resume** | Bot detects dashboard, continues to e-Registry |
| 16 | Click **Stop Bot** during automation | Stop signal propagates; browser may close depending on state |
| 17 | Check **Automation Logs** in UI | Logs show success/pause/error entries with timestamps |
| 18 | Close dashboard, restart Streamlit | Previously created registries persist in sidebar |
| 19 | Create 3+ parties (Buyer, Seller, Witness) | All appear in Review tab; can be edited independently |
| 20 | Upload PDF instead of image | Parser attempts; may fail gracefully with error message |

---

## Mock Testing Without API Keys

If you don't have a Gemini API key, you can still test everything:

```bash
# Run integration test (no API key needed)
python tests/test_integration.py

# Run pytest with mocked AI (no API key needed)
pytest tests/test_all.py -v
```

The mock tests use `unittest.mock` to simulate Gemini responses. Real API tests are in `TestAIParserIntegration` and `test_mock_gemini_parsing` — they also use mocks.

---

## Testing with Real Gemini API

> ⚠️ This costs API credits. Use small test images.

```bash
# Set your key
export GEMINI_API_KEY="your_key"

# Run a quick real test
python -c "
from modules.ai_parser import parse_id_card
from PIL import Image
import tempfile

# Create a fake 'ID card' image (white background with text won't fool real OCR, but tests the pipeline)
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    img = Image.new('RGB', (400, 250), color='white')
    img.save(f.name)
    result = parse_id_card(f.name, 'Test Buyer')
    print(result)
"
```

For a **real OCR test**, scan an actual Aadhaar/PAN card (or a printed mockup) and run:
```python
from modules.ai_parser import parse_id_card
result = parse_id_card("/path/to/your/aadhaar_scan.jpg", "Buyer 1")
print(json.dumps(result, indent=2, ensure_ascii=False))
```

Verify:
- ✅ `name_english` matches the card exactly
- ✅ `name_hindi` is phonetically correct (e.g., "Ramesh" → "रमेश")
- ✅ `id_number` has no spaces or dashes (Aadhaar = 12 digits)
- ✅ `dob` is `DD-MM-YYYY`
- ✅ `gender` is one of: Male, Female, Other
- ✅ `address_hindi` transliterates proper nouns; translates "Road" → "मार्ग"

---

## Testing Playwright Automation (Manual)

> ⚠️ Requires a real Sampada 2.0 account. Do NOT automate on production data without permission.

```bash
# Launch the automation manually
python -c "
from modules.playwright_automation import SampadaAutomation
bot = SampadaAutomation(1)  # use your registry ID
bot.start_automation()
"
```

What to observe:
1. **Browser opens** in headed mode (not headless)
2. **Geolocation** is set to Indore (22.7196, 75.8577)
3. **Login page** loads; bot pauses immediately
4. **Resume** button in dashboard triggers `bot.resume()`
5. If dashboard not detected within 60s, bot logs error
6. After login, bot navigates to e-Registry
7. Dropdown filling happens with 2-3 second delays between selections
8. Party forms are filled using placeholder heuristics
9. At KYC step, bot pauses and waits for human
10. At payment step, bot pauses again

**Debugging selectors:** If the bot fails to find elements:
```python
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=False)
page = browser.new_page()
page.goto("https://sampada.mpigr.gov.in/#/clogin")
# Inspect page manually, then use page.content() or page.screenshot()
```

---

## Edge Cases to Test

| Scenario | Expected Behavior |
|----------|-------------------|
| Blurry / low-res ID scan | Gemini may return null fields; parser logs warning; user must correct in Review tab |
| Handwritten document | OCR may fail; parser returns null; user enters manually |
| Missing mobile number on ID | `mobile_number` = null; user fills in Review tab |
| Aadhaar with spaces/dashes | Parser strips to 12 digits |
| PAN in lowercase | Parser uppercases |
| Hindi text missing from AI response | Transliterator button or user manual entry |
| Duplicate party role (two Buyers) | DB allows; UI shows both; automation fills both |
| Property boundaries missing | Fields left blank; user fills in Review tab |
| Network timeout on portal | Playwright waits 15s; logs error; user can retry |
| Biometric RD Service offline | Bot pauses at KYC; user resolves manually |
| User stops bot mid-flow | Stop signal clears; browser closes; state saved to DB |

---

## Automated CI Testing (GitHub Actions / Local)

Create `.github/workflows/test.yml`:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_all.py -v
```

Note: Playwright browser tests won't run in headless CI without `playwright install chromium` and a display. The pytest suite mocks Playwright, so it runs fine in CI.
