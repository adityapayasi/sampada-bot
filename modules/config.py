"""
Sampada 2.0 e-Registry Automation Bot
========================================
Configuration & Constants Module
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_DIR = DATA_DIR / "db"
LOGS_DIR = DATA_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
PROMPTS_DIR = BASE_DIR / "prompts"

# Ensure directories exist
for d in (UPLOAD_DIR, DB_DIR, LOGS_DIR, ASSETS_DIR, PROMPTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────
DB_PATH = DB_DIR / "sampada_state.db"

# ── AI / Gemini ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_VISION = os.getenv("GEMINI_MODEL_VISION", "gemini-1.5-flash")
GEMINI_MODEL_TEXT = os.getenv("GEMINI_MODEL_TEXT", "gemini-1.5-flash")
GEMINI_MAX_RETRIES = 3
GEMINI_TIMEOUT_SECONDS = 60

# ── Playwright / Browser ─────────────────────────────────────────────
BROWSER_HEADED = True          # Must be headed for biometric & user sessions
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")  # chromium, firefox, webkit
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "")        # Path to Chrome/Edge profile
SLOW_MO_MS = 500               # Slow down Playwright actions for stability
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# ── Portal URLs ──────────────────────────────────────────────────────
PORTAL_BASE = "https://sampada.mpigr.gov.in"
PORTAL_LOGIN = f"{PORTAL_BASE}/#/clogin"
PORTAL_DASHBOARD = f"{PORTAL_BASE}/#/citizen/dashboard"
PORTAL_E_REGISTRY = f"{PORTAL_BASE}/#/citizen/e-registry"

# ── Geolocation (Madhya Pradesh – Indore default) ────────────────────
DEFAULT_GEO = {
    "latitude": 22.7196,
    "longitude": 75.8577,
}

# ── Biometric / RD Service ───────────────────────────────────────────
RD_SERVICE_PORTS = [11100, 11101, 11102]  # Mantra, Morpho, Startek common ports
RD_SERVICE_HOST = "127.0.0.1"

# ── UI / Streamlit ───────────────────────────────────────────────────
APP_TITLE = "Sampada 2.0 Co-Pilot"
APP_ICON = "🏛️"
PAGE_LAYOUT = "wide"
PRIMARY_COLOR = "#1E90FF"
BACKGROUND_COLOR = "#0E1117"

# ── Form Constants ────────────────────────────────────────────────────
DEED_CATEGORIES = [
    "Sale Deed",
    "Gift Deed",
    "Mortgage Deed",
    "Exchange Deed",
    "Partition Deed",
    "Lease Deed",
    "Agreement",
    "Power of Attorney",
    "Will",
    "Other",
]

GENDERS = ["Male", "Female", "Other"]
CATEGORIES = ["General", "OBC", "SC", "ST", "Other"]
ID_PROOF_TYPES = ["Aadhaar", "PAN", "Voter ID", "Passport", "Driving License"]
AREA_TYPES = ["Urban", "Rural"]

PARTY_ROLES = ["Buyer", "Seller", "Witness", "Identifying Person"]

# ── Validation Regex ───────────────────────────────────────────────
AADHAAR_REGEX = r"^\d{12}$"
PAN_REGEX = r"^[A-Z]{5}\d{4}[A-Z]$"
MOBILE_REGEX = r"^\d{10}$"
DATE_FORMAT = "%d-%m-%Y"

# ── State Machine ────────────────────────────────────────────────────
class BotState:
    IDLE = "idle"
    LOGIN_WAIT = "login_wait"
    DASHBOARD = "dashboard"
    E_REGISTRY = "e_registry"
    DEED_SELECTION = "deed_selection"
    DROPDOWN_FILLING = "dropdown_filling"
    PARTY_FILLING = "party_filling"
    PROPERTY_FILLING = "property_filling"
    DRAFT_UPLOAD = "draft_upload"
    KYC_PAUSE = "kyc_pause"
    PAYMENT_PAUSE = "payment_pause"
    COMPLETED = "completed"
    ERROR = "error"

# ── Logging ──────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
