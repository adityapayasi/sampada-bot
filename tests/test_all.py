import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from modules import config
from modules.db_manager import (
    init_db, create_registry, get_registry, list_registries,
    update_registry, add_party, get_parties, update_party, delete_party,
    save_property, get_property, add_document, get_documents,
    log_automation, get_logs
)
from modules.ai_parser import _clean_id_data, _normalise_date, _normalise_gender, _normalise_id_type, _extract_json
from modules.transliterator import transliterate_text

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Use a temporary DB for every test."""
    with patch("modules.db_manager.DB_PATH", tmp_path / "test.db"):
        init_db()
        yield

@pytest.fixture
def sample_registry():
    return create_registry("Test Sale Deed")

@pytest.fixture
def sample_party_data():
    return {
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

@pytest.fixture
def sample_property_data():
    return {
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


# ── Database Tests ─────────────────────────────────────────────────────

class TestRegistryCRUD:
    def test_create_registry(self):
        rid = create_registry("My First Deed")
        assert isinstance(rid, int)
        reg = get_registry(rid)
        assert reg["title"] == "My First Deed"
        assert reg["status"] == "draft"

    def test_list_registries(self, sample_registry):
        regs = list_registries()
        assert len(regs) >= 1
        assert any(r["id"] == sample_registry for r in regs)

    def test_list_by_status(self, sample_registry):
        update_registry(sample_registry, {"status": "paused"})
        regs = list_registries(status="paused")
        assert all(r["status"] == "paused" for r in regs)

    def test_update_registry(self, sample_registry):
        update_registry(sample_registry, {
            "deed_category": "Sale Deed",
            "district": "Indore",
            "current_step": "party_filling",
        })
        reg = get_registry(sample_registry)
        assert reg["deed_category"] == "Sale Deed"
        assert reg["current_step"] == "party_filling"


class TestPartyCRUD:
    def test_add_party(self, sample_registry, sample_party_data):
        pid = add_party(sample_registry, sample_party_data)
        assert isinstance(pid, int)
        parties = get_parties(sample_registry)
        assert len(parties) == 1
        assert parties[0]["name_english"] == "Ramesh Kumar"

    def test_update_party(self, sample_registry, sample_party_data):
        pid = add_party(sample_registry, sample_party_data)
        update_party(pid, {"name_english": "Rajesh Kumar", "verified": 0})
        parties = get_parties(sample_registry)
        assert parties[0]["name_english"] == "Rajesh Kumar"
        assert parties[0]["verified"] == 0

    def test_delete_party(self, sample_registry, sample_party_data):
        pid = add_party(sample_registry, sample_party_data)
        delete_party(pid)
        parties = get_parties(sample_registry)
        assert len(parties) == 0

    def test_multiple_parties(self, sample_registry, sample_party_data):
        add_party(sample_registry, {**sample_party_data, "role": "Buyer 1"})
        add_party(sample_registry, {**sample_party_data, "role": "Seller 1", "name_english": "Mahesh Sharma"})
        parties = get_parties(sample_registry)
        assert len(parties) == 2
        roles = [p["role"] for p in parties]
        assert "Buyer 1" in roles
        assert "Seller 1" in roles


class TestPropertyCRUD:
    def test_save_and_get_property(self, sample_registry, sample_property_data):
        save_property(sample_registry, sample_property_data)
        prop = get_property(sample_registry)
        assert prop is not None
        assert prop["district"] == "Indore"
        assert prop["total_area_sqmt"] == 150.0
        assert prop["boundaries"]["east"] == "Plot 124"

    def test_overwrite_property(self, sample_registry, sample_property_data):
        save_property(sample_registry, sample_property_data)
        save_property(sample_registry, {**sample_property_data, "district": "Bhopal"})
        prop = get_property(sample_registry)
        assert prop["district"] == "Bhopal"


class TestDocumentCRUD:
    def test_add_document(self, sample_registry):
        did = add_document(sample_registry, "/tmp/fake.jpg", "id_scan", "Buyer 1", "aadhaar.jpg", "image/jpeg")
        docs = get_documents(sample_registry)
        assert len(docs) == 1
        assert docs[0]["doc_type"] == "id_scan"

    def test_filter_by_type(self, sample_registry):
        add_document(sample_registry, "/tmp/fake.jpg", "id_scan", "Buyer 1", "aadhaar.jpg", "image/jpeg")
        add_document(sample_registry, "/tmp/fake2.jpg", "property_scan", "", "deed.jpg", "image/jpeg")
        id_docs = get_documents(sample_registry, "id_scan")
        assert len(id_docs) == 1
        assert id_docs[0]["role_hint"] == "Buyer 1"


class TestAutomationLog:
    def test_log_and_retrieve(self, sample_registry):
        log_automation(sample_registry, "login", "success", "Login page loaded")
        log_automation(sample_registry, "dropdown", "error", "Tehsil not found")
        logs = get_logs(sample_registry)
        assert len(logs) == 2
        assert logs[0]["step"] == "login"
        assert logs[1]["status"] == "error"


# ── AI Parser Helper Tests ────────────────────────────────────────────

class TestCleanIdData:
    def test_basic_cleaning(self):
        raw = {
            "name_english": "  Ramesh Kumar  ",
            "name_hindi": "रमेश कुमार",
            "dob": "1985-08-15",
            "gender": "m",
            "id_type": "aadhaar card",
            "id_number": "1234-5678-9012",
            "pan_number": "abcde1234f",
            "mobile_number": "+91-98765-43210",
            "category": "",
        }
        cleaned = _clean_id_data(raw, "Buyer 1")
        assert cleaned["role"] == "Buyer 1"
        assert cleaned["name_english"] == "Ramesh Kumar"
        assert cleaned["dob"] == "15-08-1985"
        assert cleaned["gender"] == "Male"
        assert cleaned["id_type"] == "Aadhaar"
        assert cleaned["id_number"] == "123456789012"
        assert cleaned["pan_number"] == "ABCDE1234F"
        assert cleaned["mobile_number"] == "9876543210"
        assert cleaned["category"] == "General"

    def test_pan_detection(self):
        raw = {"id_type": "pan", "id_number": "ABCDE1234F"}
        cleaned = _clean_id_data(raw)
        assert cleaned["id_type"] == "PAN"
        assert cleaned["id_number"] == "ABCDE1234F"


class TestNormaliseDate:
    def test_iso_to_dmy(self):
        assert _normalise_date("1985-08-15") == "15-08-1985"

    def test_dmy_passthrough(self):
        assert _normalise_date("15-08-1985") == "15-08-1985"

    def test_empty(self):
        assert _normalise_date("") == ""


class TestNormaliseGender:
    def test_variants(self):
        assert _normalise_gender("m") == "Male"
        assert _normalise_gender("male") == "Male"
        assert _normalise_gender("पुरुष") == "Male"
        assert _normalise_gender("f") == "Female"
        assert _normalise_gender("Female") == "Female"
        assert _normalise_gender("unknown") == "Other"


class TestNormaliseIdType:
    def test_variants(self):
        assert _normalise_id_type("aadhaar") == "Aadhaar"
        assert _normalise_id_type("pan") == "PAN"
        assert _normalise_id_type("voter id") == "Voter ID"
        assert _normalise_id_type("epic") == "Voter ID"
        assert _normalise_id_type("passport") == "Passport"
        assert _normalise_id_type("driving license") == "Driving License"
        assert _normalise_id_type("something else") == "Aadhaar"  # default


class TestExtractJson:
    def test_fenced_json(self):
        text = 'Some text\n```json\n{"name": "Ramesh"}\n```\nMore text'
        result = _extract_json(text)
        assert result == {"name": "Ramesh"}

    def test_raw_json(self):
        text = 'Here is the result: {"name": "Ramesh", "age": 30}'
        result = _extract_json(text)
        assert result["name"] == "Ramesh"

    def test_invalid_json(self):
        text = "No JSON here at all"
        result = _extract_json(text)
        assert result is None


# ── Transliterator Tests (mocked) ──────────────────────────────────────

class TestTransliterator:
    @patch("modules.transliterator.genai.GenerativeModel")
    def test_success(self, mock_model_class):
        mock_response = Mock()
        mock_response.text = "रमेश"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        result = transliterate_text("Ramesh")
        assert result == "रमेश"

    @patch("modules.transliterator.GEMINI_API_KEY", "")
    def test_no_key_returns_none(self):
        assert transliterate_text("Ramesh") is None


# ── Config Tests ─────────────────────────────────────────────────────

class TestConfig:
    def test_paths_exist(self):
        assert config.BASE_DIR.exists()
        assert config.UPLOAD_DIR.exists()
        assert config.DB_DIR.exists()
        assert config.LOGS_DIR.exists()

    def test_constants(self):
        assert config.PORTAL_BASE == "https://sampada.mpigr.gov.in"
        assert "General" in config.CATEGORIES
        assert "Aadhaar" in config.ID_PROOF_TYPES
        assert "Urban" in config.AREA_TYPES

    def test_regex_patterns(self):
        import re
        assert re.match(config.AADHAAR_REGEX, "123456789012")
        assert not re.match(config.AADHAAR_REGEX, "12345")
        assert re.match(config.PAN_REGEX, "ABCDE1234F")
        assert not re.match(config.PAN_REGEX, "ABCDE1234")
        assert re.match(config.MOBILE_REGEX, "9876543210")


# ── Mock Gemini Integration Test ─────────────────────────────────────

class TestAIParserIntegration:
    @patch("modules.ai_parser.genai.GenerativeModel")
    def test_parse_id_card_success(self, mock_model_class):
        # Create a fake image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), color="white")
            img.save(f.name)
            img_path = f.name

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

        with patch("modules.ai_parser.GEMINI_API_KEY", "fake-key"):
            from modules.ai_parser import parse_id_card
            result = parse_id_card(img_path, "Buyer 1")

        assert result is not None
        assert result["name_english"] == "Ramesh Kumar"
        assert result["role"] == "Buyer 1"
        assert result["id_number"] == "123456789012"

        Path(img_path).unlink()

    @patch("modules.ai_parser.genai.GenerativeModel")
    def test_parse_property_document(self, mock_model_class):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (200, 200), color="white")
            img.save(f.name)
            img_path = f.name

        mock_response = Mock()
        mock_response.text = json.dumps({
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
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch("modules.ai_parser.GEMINI_API_KEY", "fake-key"):
            from modules.ai_parser import parse_property_document
            result = parse_property_document(img_path)

        assert result is not None
        assert result["district"] == "Indore"
        assert result["total_area_sqmt"] == 150.0
        assert result["boundaries"]["east"] == "Plot 124"

        Path(img_path).unlink()


# ── End-to-End Flow Test ─────────────────────────────────────────────

class TestEndToEndFlow:
    def test_full_registry_workflow(self, sample_party_data, sample_property_data):
        """Simulate a complete registry lifecycle without any external APIs."""
        # 1. Create registry
        rid = create_registry("Sale Deed - Plot 123")
        reg = get_registry(rid)
        assert reg["status"] == "draft"

        # 2. Add parties
        add_party(rid, {**sample_party_data, "role": "Buyer 1"})
        add_party(rid, {**sample_party_data, "role": "Seller 1", "name_english": "Mahesh Sharma", "name_hindi": "महेश शर्मा"})
        add_party(rid, {**sample_party_data, "role": "Witness 1", "name_english": "Suresh Patel", "name_hindi": "सुरेश पटेल"})
        parties = get_parties(rid)
        assert len(parties) == 3

        # 3. Save property
        save_property(rid, sample_property_data)
        prop = get_property(rid)
        assert prop["plot_number"] == "123"

        # 4. Add documents
        add_document(rid, "/tmp/buyer_aadhaar.jpg", "id_scan", "Buyer 1", "buyer_aadhaar.jpg", "image/jpeg")
        add_document(rid, "/tmp/seller_pan.jpg", "id_scan", "Seller 1", "seller_pan.jpg", "image/jpeg")
        add_document(rid, "/tmp/property_deed.jpg", "property_scan", "", "property_deed.jpg", "image/jpeg")
        docs = get_documents(rid)
        assert len(docs) == 3

        # 5. Update registry status
        update_registry(rid, {
            "deed_category": "Sale Deed",
            "district": "Indore",
            "tehsil": "Indore",
            "current_step": "party_filling",
            "status": "in_progress",
        })
        reg = get_registry(rid)
        assert reg["deed_category"] == "Sale Deed"
        assert reg["status"] == "in_progress"

        # 6. Log automation steps
        log_automation(rid, "login", "success", "Dashboard loaded")
        log_automation(rid, "party_filling", "success", "3 parties filled")
        log_automation(rid, "property_filling", "success", "Property details entered")
        logs = get_logs(rid)
        assert len(logs) == 3
        assert logs[0]["status"] == "success"

        # 7. Verify all data is retrievable
        full_reg = get_registry(rid)
        full_parties = get_parties(rid)
        full_prop = get_property(rid)
        full_docs = get_documents(rid)
        full_logs = get_logs(rid)

        assert full_reg is not None
        assert len(full_parties) == 3
        assert full_prop is not None
        assert len(full_docs) == 3
        assert len(full_logs) == 3
