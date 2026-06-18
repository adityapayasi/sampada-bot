"""
English → Hindi Transliteration Helper
Uses Gemini as a fallback for phonetic transliteration when the AI parser
needs a second-pass refinement on names or addresses.
"""

import logging
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from modules.config import GEMINI_API_KEY, GEMINI_MODEL_TEXT, LOG_FORMAT, LOG_LEVEL
from prompts.vision_prompts import TRANSLITERATION_PROMPT

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


def transliterate_text(text: str) -> Optional[str]:
    """
    Send a single English text string to Gemini for Hindi phonetic transliteration.
    Returns the Devanagari string or None on failure.
    """
    if not GEMINI_API_KEY or not text.strip():
        return None

    model = genai.GenerativeModel(GEMINI_MODEL_TEXT)
    prompt = TRANSLITERATION_PROMPT.replace("{TEXT}", text.strip())

    try:
        response = model.generate_content(
            prompt,
            safety_settings=SAFETY_SETTINGS,
            request_options={"timeout": 30},
        )
        hindi = response.text or ""
        hindi = hindi.strip().strip('"').strip("'")
        return hindi
    except Exception as e:
        logger.error("Transliteration failed for '%s': %s", text, e)
        return None
