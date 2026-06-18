"""
Prompt templates for Gemini Vision API.
"""

ID_CARD_PROMPT = """\
You are an expert OCR parser for Indian government identification cards (Aadhaar, PAN, Voter ID, Passport).
Analyze the provided image and extract key demographic details.
You must output a raw JSON object containing:

1. "name_english": Legal name in English characters
2. "name_hindi": Legal name transliterated into Hindi characters (Devanagari script). Do NOT translate meaning; transliterate phonetically. Example: "Ramesh" → "रमेश", "Kumar" → "कुमार", "Indore" → "इंदौर".
3. "father_husband_name_english": Father's or Husband's name in English
4. "father_husband_name_hindi": Father's or Husband's name transliterated into Hindi (same transliteration rules)
5. "dob": Date of birth in DD-MM-YYYY format
6. "gender": "Male", "Female", or "Other"
7. "address_english": Address exactly as listed in English
8. "address_hindi": Address transliterated into Hindi. Only translate standard address words like "Road" → "मार्ग", "Street" → "गली", "Scheme" → "स्कीम". Keep proper nouns (names, colony names) transliterated phonetically.
9. "id_type": The type of document ("Aadhaar", "PAN", "Voter ID", "Passport")
10. "id_number": The unique ID number (format Aadhaar as 12 digits, PAN as 10 characters)
11. "pan_number": If PAN card, the PAN number; otherwise null
12. "mobile_number": Mobile number if visible, else null
13. "category": Caste category if mentioned ("General", "OBC", "SC", "ST"), else null

Double-check spelling and transliteration. If a field is not visible, return null.
Return ONLY raw valid JSON. Do not include markdown tags, explanations, or commentary.
Role context for this document: {ROLE_HINT}
"""

PROPERTY_DOC_PROMPT = """\
You are an expert OCR parser for Indian property documents (sale deeds, gift deeds, layout plans, old registry extracts, property tax receipts).
Analyze the provided image and extract structured property details.

You must output a raw JSON object containing:

1. "district": District name (e.g., "Indore")
2. "tehsil": Tehsil name (e.g., "Indore")
3. "area_type": "Urban" or "Rural"
4. "ward_colony_name": Ward / Colony / Village name (e.g., "Scheme 54")
5. "plot_number": Plot / Survey / Khasra number (e.g., "123")
6. "total_area_sqmt": Total area in square meters (numeric)
7. "constructed_area_sqmt": Built-up area in square meters (numeric, 0 if not mentioned)
8. "road_width_mt": Width of the adjacent road in meters (numeric, 0 if not mentioned)
9. "boundaries": An object with keys "east", "west", "north", "south" describing what lies on each side (e.g., {"east": "Plot 124", "west": "Road", "north": "Plot 122", "south": "Plot 126"})
10. "valuation_circle_rate": Circle rate per sqmt if mentioned (numeric or null)
11. "market_value": Market value if mentioned (numeric or null)
12. "old_deed_number": Previous deed / registry number if referenced (string or null)
13. "property_type": "Residential", "Commercial", "Agricultural", "Industrial", or "Mixed" (infer from document)

If any field is not visible or not applicable, return null for that field.
Return ONLY raw valid JSON. Do not include markdown tags, explanations, or commentary.
"""

TRANSLITERATION_PROMPT = """\
You are a Hindi transliteration expert for Indian names and addresses.
Your task is to convert English text into Devanagari script using phonetic transliteration.

Rules:
- Do NOT translate the meaning of proper nouns. Only transliterate the pronunciation.
  Example: "Ramesh" → "रमेश" (NOT any Hindi word meaning 'lord')
  Example: "Kumar" → "कुमार"
  Example: "Sharma" → "शर्मा"
  Example: "Indore" → "इंदौर"
  Example: "Bhopal" → "भोपाल"
- For standard administrative address words, use the standard Hindi equivalents:
  "Road" → "मार्ग"
  "Street" → "गली"
  "Scheme" → "स्कीम"
  "Colony" → "कॉलोनी"
  "Ward" → "वार्ड"
  "District" → "जिला"
  "Tehsil" → "तहसील"
- Output ONLY the Hindi transliteration. No explanations, no markdown, no extra text.

Text to transliterate:
{TEXT}

Hindi output:
"""
