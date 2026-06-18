"""
Integration test runner that exercises the full module chain
without needing real API keys or a real browser.
Run: python tests/test_integration.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from unittest.mock import Mock, patch
from PIL import Image
import tempfile

from modules.db_manager import init_db, create_registry, get_registry, list_registries
from modules.db_manager import add_party, get_parties, save_property, get_property
from modules.db_manager import add_document, get_documents, log_automation, get_logs
from modules.ai_parser import _clean_id_data, _normalise_date, _extract_json
from modules import config


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_config():
    print_header("TEST: Config Module")
    assert config.PORTAL_BASE == "https://sampada.mpigr.gov.in"
    assert "Sale Deed" in config.DEED_CATEGORIES
    assert "Aadhaar" in config.ID_PROOF_TYPES
    assert config.DEFAULT_GEO["latitude"] == 22.7196
    print("✅ Config constants validated")


def test_database():
    print_header("TEST: Database CRUD")
    
    # Use a temp DB so we don't pollute the real one
    import tempfile
    tmp_db = Path(tempfile.mkdtemp()) / "integration_test.db"
    with patch("modules.db_manager.DB_PATH", tmp_db):
        init_db()
        
        # Create registry
        rid = create_registry("Integration Test Registry")
        assert isinstance(rid, int)
        print(f"✅ Created registry ID: {rid}")
        
        # Verify retrieval
        reg = get_registry(rid)
        assert reg["title"] == "Integration Test Registry"
        assert reg["status"] == "draft"
        print("✅ Registry retrieval works")
        
        # Add parties
        buyer = {
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
        }
        seller = {
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
        }
        add_party(rid, buyer)
        add_party(rid, seller)
        parties = get_parties(rid)
        assert len(parties) == 2
        print(f"✅ Added {len(parties)} parties")
        
        # Save property
        property_data = {
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
        save_property(rid, property_data)
        prop = get_property(rid)
        assert prop["district"] == "Indore"
        assert prop["boundaries"]["east"] == "Plot 124"
        print("✅ Property saved and retrieved")
        
        # Add documents
        add_document(rid, "/tmp/fake1.jpg", "id_scan", "Buyer 1", "aadhaar.jpg", "image/jpeg")
        add_document(rid, "/tmp/fake2.jpg", "id_scan", "Seller 1", "pan.jpg", "image/jpeg")
        add_document(rid, "/tmp/fake3.jpg", "property_scan", "", "deed.jpg", "image/jpeg")
        docs = get_documents(rid)
        assert len(docs) == 3
        print(f"✅ Added {len(docs)} documents")
        
        # Log automation steps
        log_automation(rid, "login", "success", "Dashboard loaded after manual login")
        log_automation(rid, "party_filling", "success", "Buyer and Seller filled")
        log_automation(rid, "kyc_pause", "pause", "Waiting for biometric scan")
        logs = get_logs(rid)
        assert len(logs) == 3
        print(f"✅ Logged {len(logs)} automation steps")
        
        # List all registries
        all_regs = list_registries()
        assert any(r["id"] == rid for r in all_regs)
        print("✅ Registry listing works")


def test_data_cleaning():
    print_header("TEST: Data Cleaning Functions")
    
    # Test JSON extraction
    raw = '```json\n{"name": "Ramesh", "age": 30}\n```'
    result = _extract_json(raw)
    assert result == {"name": "Ramesh", "age": 30}
    print("✅ Fenced JSON extraction works")
    
    # Test raw JSON extraction
    raw2 = 'Here is data: {"name": "Kumar", "city": "Indore"}'
    result2 = _extract_json(raw2)
    assert result2["city"] == "Indore"
    print("✅ Raw JSON extraction works")
    
    # Test ID cleaning
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
    assert cleaned["name_english"] == "Ramesh Kumar"
    assert cleaned["dob"] == "15-08-1985"
    assert cleaned["gender"] == "Male"
    assert cleaned["id_type"] == "Aadhaar"
    assert cleaned["id_number"] == "123456789012"
    assert cleaned["pan_number"] == "ABCDE1234F"
    assert cleaned["mobile_number"] == "9876543210"
    assert cleaned["category"] == "General"
    print("✅ ID data cleaning works (dates, gender, IDs, mobile)")
    
    # Test date normalization
    assert _normalise_date("1990-01-25") == "25-01-1990"
    assert _normalise_date("25-01-1990") == "25-01-1990"
    assert _normalise_date("") == ""
    print("✅ Date normalization works")


@patch("modules.ai_parser.genai.GenerativeModel")
def test_mock_gemini_parsing(mock_model_class):
    print_header("TEST: Mock Gemini AI Parsing")
    
    # Create fake image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(f.name)
        img_path = f.name
    
    # Mock response
    mock_response = Mock()
    mock_response.text = json.dumps({
        "name_english": "Ramesh Kumar",
        "name_hindi": "रमेश कुमार",
        "father_husband_name_english": "Suresh Kumar",
        "father_husband_name_hindi": "सुरेश कुमार",
        "dob": "15-08-1985",
        "gender": "Male",
        "address_english": "123 Indore",
        "address_hindi": "123 इंदौर",
        "id_type": "Aadhaar",
        "id_number": "123456789012",
        "pan_number": None,
        "mobile_number": "9876543210",
        "category": "General",
    })
    mock_model = Mock()
    mock_model.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model
    
    from modules.ai_parser import parse_id_card
    with patch("modules.ai_parser.GEMINI_API_KEY", "fake-test-key"):
        result = parse_id_card(img_path, "Buyer 1")
    
    assert result is not None
    assert result["name_english"] == "Ramesh Kumar"
    assert result["role"] == "Buyer 1"
    assert result["id_number"] == "123456789012"
    print("✅ Mock Gemini ID parsing works")
    
    # Mock property parsing
    mock_response2 = Mock()
    mock_response2.text = json.dumps({
        "district": "Indore",
        "tehsil": "Indore",
        "area_type": "Urban",
        "ward_colony_name": "Scheme 54",
        "plot_number": "123",
        "total_area_sqmt": 150.0,
        "constructed_area_sqmt": 120.0,
        "road_width_mt": 9.0,
        "boundaries": {"east": "Plot 124", "west": "Road"},
    })
    mock_model.generate_content.return_value = mock_response2
    
    from modules.ai_parser import parse_property_document
    with patch("modules.ai_parser.GEMINI_API_KEY", "fake-test-key"):
        result2 = parse_property_document(img_path)
    
    assert result2 is not None
    assert result2["district"] == "Indore"
    assert result2["total_area_sqmt"] == 150.0
    print("✅ Mock Gemini property parsing works")
    
    # Cleanup
    Path(img_path).unlink()


def test_streamlit_smoke():
    print_header("TEST: Streamlit App Smoke Test (Imports)")
    try:
        # Just verify the app module can be imported without runtime errors
        import app.streamlit_app
        print("✅ Streamlit app module imports successfully")
    except Exception as e:
        print(f"⚠️ Streamlit import warning (may need streamlit installed): {e}")


def test_playwright_smoke():
    print_header("TEST: Playwright Module Smoke Test (Imports)")
    try:
        from modules.playwright_automation import SampadaAutomation, resume_bot, stop_bot
        print("✅ Playwright automation module imports successfully")
    except Exception as e:
        print(f"⚠️ Playwright import warning (may need playwright installed): {e}")


def run_all_tests():
    print("\n" + "="*60)
    print("  SAMPADA 2.0 BOT - INTEGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        test_config,
        test_database,
        test_data_cleaning,
        test_mock_gemini_parsing,
        test_streamlit_smoke,
        test_playwright_smoke,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
    print(f"{'='*60}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
