"""
Gemini Vision AI Parser
Extracts structured data from ID cards and property documents using
Google Gemini 1.5 Flash / Pro with dual-prompt transliteration.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from modules.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_VISION,
    GEMINI_MAX_RETRIES,
    GEMINI_TIMEOUT_SECONDS,
    LOG_FORMAT,
    LOG_LEVEL,
)
from prompts.vision_prompts import ID_CARD_PROMPT, PROPERTY_DOC_PROMPT

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not set – AI parser will fail.")


# Safety config: allow all content types for document analysis
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


def _load_image(path: str | Path):
    """Return a PIL Image from disk."""
    from PIL import Image
    with Image.open(path) as img:
        img.load()
        return img


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull the first JSON object out of the LLM response text."""
    # Try to find JSON inside markdown fences
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        # Try raw object
        raw = re.search(r"(\{.*\})", text, re.DOTALL)
        if raw:
            text = raw.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("JSON decode failed: %s", e)
        return None


def _clean_id_data(raw: Dict[str, Any], role_hint: str = "") -> Dict[str, Any]:
    """Normalise & validate extracted ID card fields."""
    cleaned: Dict[str, Any] = {}

    cleaned["role"] = role_hint or raw.get("role", "Unknown")
    cleaned["name_english"] = str(raw.get("name_english", "")).strip()
    cleaned["name_hindi"] = str(raw.get("name_hindi", "")).strip()
    cleaned["father_husband_name_english"] = str(raw.get("father_husband_name_english", "")).strip()
    cleaned["father_husband_name_hindi"] = str(raw.get("father_husband_name_hindi", "")).strip()

    # Date formatting
    dob = str(raw.get("dob", raw.get("date_of_birth", ""))).strip()
    cleaned["dob"] = _normalise_date(dob)

    cleaned["gender"] = _normalise_gender(str(raw.get("gender", "")))
    cleaned["address_english"] = str(raw.get("address_english", "")).strip()
    cleaned["address_hindi"] = str(raw.get("address_hindi", "")).strip()
    cleaned["id_type"] = _normalise_id_type(str(raw.get("id_type", "")))

    # Clean Aadhaar / PAN numbers
    id_num = str(raw.get("id_number", "")).strip()
    pan = str(raw.get("pan_number", "")).strip().upper()
    if cleaned["id_type"] == "Aadhaar":
        id_num = re.sub(r"\D", "", id_num)
    cleaned["id_number"] = id_num
    cleaned["pan_number"] = pan

    mobile = str(raw.get("mobile_number", "")).strip()
    mobile_digits = re.sub(r"\D", "", mobile)
    if len(mobile_digits) > 10:
        mobile_digits = mobile_digits[-10:]
    cleaned["mobile_number"] = mobile_digits
    cleaned["category"] = str(raw.get("category", "")).strip() or "General"
    return cleaned


def _normalise_date(dob: str) -> str:
    """Convert various date strings to DD-MM-YYYY."""
    from dateutil.parser import parse
    if not dob:
        return ""
    try:
        dt = parse(dob, dayfirst=True)
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return dob


def _normalise_gender(g: str) -> str:
    g = g.lower().strip()
    if g in ("m", "male", "पुरुष"):
        return "Male"
    if g in ("f", "female", "महिला"):
        return "Female"
    return "Other"


def _normalise_id_type(t: str) -> str:
    t = t.lower().strip()
    if "aadhaar" in t:
        return "Aadhaar"
    if "pan" in t:
        return "PAN"
    if "voter" in t or "epic" in t:
        return "Voter ID"
    if "passport" in t:
        return "Passport"
    if "driving" in t or "license" in t:
        return "Driving License"
    return "Aadhaar"


# ── Public API ───────────────────────────────────────────────────────

def parse_id_card(
    image_path: str | Path,
    role_hint: str = "",
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Send an ID card image to Gemini and return cleaned structured data.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = _load_image(image_path)
    prompt = ID_CARD_PROMPT.replace("{ROLE_HINT}", role_hint)

    model_name = model or GEMINI_MODEL_VISION
    gemini_model = genai.GenerativeModel(model_name)

    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            logger.info("[Attempt %d/%d] Parsing %s as %s", attempt, GEMINI_MAX_RETRIES, image_path.name, role_hint or "ID")
            response = gemini_model.generate_content(
                [prompt, img],
                safety_settings=SAFETY_SETTINGS,
                request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
            )
            raw_text = response.text or ""
            raw_json = _extract_json(raw_text)
            if raw_json is None:
                logger.warning("No valid JSON returned on attempt %d", attempt)
                continue
            cleaned = _clean_id_data(raw_json, role_hint)
            logger.info("Successfully parsed ID for %s", cleaned.get("name_english", "?"))
            return cleaned
        except Exception as e:
            logger.exception("Gemini call failed on attempt %d: %s", attempt, e)

    logger.error("All %d attempts exhausted for %s", GEMINI_MAX_RETRIES, image_path.name)
    return None


def parse_property_document(
    image_path: str | Path,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Send a property document image to Gemini and return structured property details.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = _load_image(image_path)
    gemini_model = genai.GenerativeModel(model or GEMINI_MODEL_VISION)

    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            logger.info("[Attempt %d/%d] Parsing property doc %s", attempt, GEMINI_MAX_RETRIES, image_path.name)
            response = gemini_model.generate_content(
                [PROPERTY_DOC_PROMPT, img],
                safety_settings=SAFETY_SETTINGS,
                request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
            )
            raw_text = response.text or ""
            raw_json = _extract_json(raw_text)
            if raw_json is None:
                continue
            # Normalise numeric fields
            for k in ["total_area_sqmt", "constructed_area_sqmt", "road_width_mt"]:
                if k in raw_json:
                    try:
                        raw_json[k] = float(raw_json[k])
                    except (ValueError, TypeError):
                        raw_json[k] = 0.0
            boundaries = raw_json.get("boundaries", {})
            if isinstance(boundaries, dict):
                raw_json["boundaries"] = boundaries
            else:
                raw_json["boundaries"] = {}
            logger.info("Successfully parsed property document")
            return raw_json
        except Exception:
            logger.exception("Property parsing failed on attempt %d", attempt)

    logger.error("All attempts exhausted for property doc %s", image_path.name)
    return None


def batch_parse_id_cards(
    file_role_pairs: List[tuple],
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Parse multiple ID cards.
    file_role_pairs: list of (file_path, role_hint) tuples.
    """
    results = []
    for path, role in file_role_pairs:
        data = parse_id_card(path, role_hint=role, model=model)
        if data:
            results.append(data)
    return results
