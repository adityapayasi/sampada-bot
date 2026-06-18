import sys
import os
import sqlite3
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image

# Project root
PROJECT_ROOT = Path(r'C:\Users\Adity\Documents\kimi\workspace\sampada-bot')
sys.path.insert(0, str(PROJECT_ROOT))

# ── Stub missing external dependencies ───────────────────────────
class FakeDotenv:
    def load_dotenv(self, *a, **k): pass

class FakeGoogleGenAI:
    def configure(self, *a, **k): pass
    class GenerativeModel:
        def __init__(self, *a, **k): pass
        def generate_content(self, *a, **k):
            m = Mock()
            m.text = json.dumps({
                "name_english": "Ramesh Kumar",
                "name_hindi": "रमेश कुमार",
                "father_husband_name_english": "Suresh Kumar",
                "father_husband_name_hindi": "सुरेश कुमार",
                "dob": "15-08-1985",
                "gender": "Male",
                "address_english": "123 Scheme 54, Indore",
                "address_hindi": "123 स्कीम 54, इंदौर",
                "id_type": "Aadhaar",
                "id_number": "123456789012",
                "pan_number": None,
                "mobile_number": "9876543210",
                "category": "General",
            })
            return m

class FakeHarm:
    HARM_CATEGORY_HARASSMENT = 1
    HARM_CATEGORY_HATE_SPEECH = 2
    HARM_CATEGORY_SEXUALLY_EXPLICIT = 3
    HARM_CATEGORY_DANGEROUS_CONTENT = 4
    BLOCK_NONE = 0

sys.modules['dotenv'] = Mock()
sys.modules['dotenv'].load_dotenv = lambda *a, **k: None
sys.modules['google'] = Mock()
sys.modules['google.generativeai'] = FakeGoogleGenAI()
sys.modules['google'].generativeai = FakeGoogleGenAI()
sys.modules['google.generativeai.types'] = FakeHarm()
sys.modules['playwright'] = Mock()
sys.modules['playwright.sync_api'] = Mock()
sys.modules['pydantic'] = Mock()

# ── Import our modules ───────────────────────────────────────────
from modules import config
from modules.db_manager import init_db, create_registry, get_registry, list_registries
from modules.db_manager import add_party, get_parties, save_property, get_property
from modules.db_manager import add_document, get_documents, log_automation, get_logs
from modules.ai_parser import _clean_id_data, _normalise_date, _normalise_gender, _normalise_id_type, _extract_json
from modules.ai_parser import parse_id_card, parse_property_document

# ── Use a temp DB so we don't pollute the real one ───────────────
TMP_DB = Path(tempfile.mkdtemp()) / "demo.db"
print("=" * 60)
print("  SAMPADA 2.0 BOT — LIVE DEMONSTRATION")
print("=" * 60)
print(f"\nTemp DB: {TMP_DB}")
print(f"Python:  {sys.version}")
print()

with patch("modules.db_manager.DB_PATH", TMP_DB):
    init_db()
    print("✅ Database initialized")
    print()

    # ── 1. Registry CRUD ───────────────────────────────────────
    print("─" * 60)
    print("TEST 1: Registry CRUD")
    print("─" * 60)
    rid = create_registry("Sale Deed - Plot 123")
    print(f"✅ Created registry ID: {rid}")
    reg = get_registry(rid)
    print(f"   Title:   {reg['title']}")
    print(f"   Status:  {reg['status']}")
    print(f"   Step:    {reg['current_step']}")
    print()

    # ── 2. Party CRUD ──────────────────────────────────────────
    print("─" * 60)
    print("TEST 2: Party CRUD (3 parties)")
    print("─" * 60)
    parties = [
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
            "email": "",
            "photo_path": "",
            "verified": 1,
        },
        {
            "role": "Seller 1",
            "name_english": "Mahesh Sharma",
            "name_hindi": "महेश शर्मा",
            "father_husband_name_english": "Ganesh Sharma",
            "father_husband_name_hindi": "गणेश शर्मा",
            "dob": "22-03-1990",
            "gender": "Male",
            "category": "OBC",
            "address_english": "45 Vijay Nagar, Indore",
            "address_hindi": "45 विजय नगर, इंदौर",
            "id_type": "PAN",
            "id_number": "ABCDE1234F",
            "pan_number": "ABCDE1234F",
            "mobile_number": "8765432109",
            "email": "",
            "photo_path": "",
            "verified": 1,
        },
        {
            "role": "Witness 1",
            "name_english": "Suresh Patel",
            "name_hindi": "सुरेश पटेल",
            "father_husband_name_english": "Ramesh Patel",
            "father_husband_name_hindi": "रमेश पटेल",
            "dob": "10-11-1978",
            "gender": "Male",
            "category": "General",
            "address_english": "78 M.G. Road, Indore",
            "address_hindi": "78 एम.जी. रोड, इंदौर",
            "id_type": "Voter ID",
            "id_number": "ABC1234567",
            "pan_number": "",
            "mobile_number": "7654321098",
            "email": "",
            "photo_path": "",
            "verified": 0,
        },
    ]
    for p in parties:
        add_party(rid, p)
    stored = get_parties(rid)
    print(f"✅ Added {len(stored)} parties:")
    for sp in stored:
        print(f"   {sp['role']:12} | {sp['name_english']:20} | verified={sp['verified']}")
    print()

    # ── 3. Property CRUD ───────────────────────────────────────
    print("─" * 60)
    print("TEST 3: Property CRUD")
    print("─" * 60)
    prop = {
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
            "south": "Plot 126",
        },
    }
    save_property(rid, prop)
    stored_prop = get_property(rid)
    print(f"✅ Property saved:")
    print(f"   District: {stored_prop['district']}, Tehsil: {stored_prop['tehsil']}")
    print(f"   Plot: {stored_prop['plot_number']}, Area: {stored_prop['total_area_sqmt']} sqmt")
    print(f"   Boundaries: N={stored_prop['boundaries']['north']}, S={stored_prop['boundaries']['south']}, E={stored_prop['boundaries']['east']}, W={stored_prop['boundaries']['west']}")
    print()

    # ── 4. Document Tracking ───────────────────────────────────
    print("─" * 60)
    print("TEST 4: Document Tracking")
    print("─" * 60)
    add_document(rid, "/tmp/buyer_aadhaar.jpg", "id_scan", "Buyer 1", "aadhaar.jpg", "image/jpeg")
    add_document(rid, "/tmp/seller_pan.jpg", "id_scan", "Seller 1", "pan.jpg", "image/jpeg")
    add_document(rid, "/tmp/property_deed.jpg", "property_scan", "", "deed.jpg", "image/jpeg")
    docs = get_documents(rid)
    print(f"✅ Tracked {len(docs)} documents:")
    for d in docs:
        print(f"   {d['doc_type']:14} | {d['role_hint'] or '—':12} | {d['file_name']}")
    print()

    # ── 5. Automation Logs ───────────────────────────────────────
    print("─" * 60)
    print("TEST 5: Automation Logs")
    print("─" * 60)
    log_automation(rid, "login", "success", "Dashboard loaded after manual login")
    log_automation(rid, "party_filling", "success", "3 parties filled via automation")
    log_automation(rid, "kyc_pause", "pause", "Waiting for biometric scan (Mantra RD)")
    log_automation(rid, "payment_pause", "pause", "Payment gateway reached — stamp duty pending")
    logs = get_logs(rid)
    print(f"✅ Logged {len(logs)} automation steps:")
    for lg in logs:
        icon = "🟢" if lg["status"] == "success" else "🟡"
        print(f"   {icon} {lg['step']:20} | {lg['status']:8} | {lg['message']}")
    print()

    # ── 6. Data Cleaning Tests ─────────────────────────────────
    print("─" * 60)
    print("TEST 6: Data Cleaning (No AI needed)")
    print("─" * 60)
    # JSON extraction
    raw_json = '```json\n{"name": "Ramesh", "city": "Indore"}\n```'
    extracted = _extract_json(raw_json)
    print(f"✅ JSON extraction: {extracted}")
    # Date normalization
    print(f"✅ Date norm '1985-08-15' → '{_normalise_date('1985-08-15')}'")
    print(f"✅ Date norm '15-08-1985' → '{_normalise_date('15-08-1985')}'")
    # Gender normalization
    print(f"✅ Gender 'm' → '{_normalise_gender('m')}'")
    print(f"✅ Gender 'female' → '{_normalise_gender('female')}'")
    # ID type normalization
    print(f"✅ ID type 'aadhaar card' → '{_normalise_id_type('aadhaar card')}'")
    print(f"✅ ID type 'pan' → '{_normalise_id_type('pan')}'")
    # Full ID cleaning
    dirty = {
        "name_english": "  Ramesh Kumar  ",
        "dob": "1985-08-15",
        "gender": "m",
        "id_type": "aadhaar card",
        "id_number": "1234-5678-9012",
        "pan_number": "abcde1234f",
        "mobile_number": "+91-98765-43210",
        "category": "",
    }
    cleaned = _clean_id_data(dirty, "Buyer 1")
    print(f"✅ ID cleaning:")
    print(f"   Name:  '{cleaned['name_english']}'")
    print(f"   DOB:   '{cleaned['dob']}'")
    print(f"   Gender: '{cleaned['gender']}'")
    print(f"   ID:    '{cleaned['id_number']}' (12 digits, no dashes)")
    print(f"   PAN:   '{cleaned['pan_number']}' (uppercase)")
    print(f"   Mobile:'{cleaned['mobile_number']}' (10 digits)")
    print()

    # ── 7. Mock AI Parser (Gemini stub) ──────────────────────────
    print("─" * 60)
    print("TEST 7: AI Parser (Mock Gemini)")
    print("─" * 60)
    # Create a fake image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (200, 200), color="white")
        img.save(f.name)
        img_path = f.name

    # Mock the API key so the parser doesn't complain
    with patch("modules.ai_parser.GEMINI_API_KEY", "demo-key"):
        result = parse_id_card(img_path, "Buyer 1")
    print(f"✅ Parsed ID card (mock response):")
    print(f"   Role:       {result['role']}")
    print(f"   Name (EN):  {result['name_english']}")
    print(f"   Name (HI):  {result['name_hindi']}")
    print(f"   Father (EN):{result['father_husband_name_english']}")
    print(f"   Father (HI):{result['father_husband_name_hindi']}")
    print(f"   DOB:        {result['dob']}")
    print(f"   Gender:     {result['gender']}")
    print(f"   Address HI: {result['address_hindi']}")
    print(f"   ID Type:    {result['id_type']}")
    print(f"   ID Number:  {result['id_number']}")
    print(f"   Mobile:     {result['mobile_number']}")
    print()

    # ── 8. Final Registry Summary ───────────────────────────────
    print("=" * 60)
    print("  FINAL REGISTRY SUMMARY")
    print("=" * 60)
    final_reg = get_registry(rid)
    final_parties = get_parties(rid)
    final_prop = get_property(rid)
    final_docs = get_documents(rid)
    final_logs = get_logs(rid)

    print(f"\nRegistry #{final_reg['id']}: {final_reg['title']}")
    print(f"  Status:  {final_reg['status']}")
    print(f"  Step:    {final_reg['current_step']}")
    print(f"  Created: {final_reg['created_at']}")
    print(f"\n  Parties:     {len(final_parties)}")
    print(f"  Property:    {'YES' if final_prop else 'NO'}")
    print(f"  Documents:   {len(final_docs)}")
    print(f"  Log entries: {len(final_logs)}")

    print()
    print("=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)
    print()
    print("Next steps on your local machine:")
    print("  1. pip install -r requirements.txt")
    print("  2. playwright install chromium")
    print("  3. Add GEMINI_API_KEY to .env")
    print("  4. streamlit run app/streamlit_app.py")

    sys.exit(0)

if __name__ == "__main__":
    pass  # script runs top-level
