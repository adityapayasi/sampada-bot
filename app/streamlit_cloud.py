"""
Sampada 2.0 Co-Pilot - Cloud Deployable Version
For Streamlit Community Cloud (streamlit.io/cloud)
Uses session state + JSON export/import instead of SQLite.
The browser automation part is handled by a local runner script.
"""

import os, sys, json, tempfile, base64
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

import streamlit as st

# ── Page Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sampada 2.0 Co-Pilot (Cloud)",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark Mode CSS ───────────────────────────────────────────────────────
DARK_CSS = """
<style>
    .block-container { padding-top: 1rem; }
    .stButton>button { border-radius: 8px; }
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div { border-radius: 6px; }
    .stFileUploader>div>div>div { border-radius: 8px; border: 2px dashed #444; }
    .card {
        background-color: #1a1a2e; border-radius: 12px; padding: 1.5rem;
        margin-bottom: 1rem; border: 1px solid #2a2a4e;
    }
    .card-title { color: #1E90FF; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .hint-text { color: #888; font-size: 0.85rem; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────
DEED_CATEGORIES = [
    "Sale Deed", "Gift Deed", "Mortgage Deed", "Exchange Deed",
    "Partition Deed", "Lease Deed", "Agreement", "Power of Attorney", "Will", "Other"
]
GENDERS = ["Male", "Female", "Other"]
CATEGORIES = ["General", "OBC", "SC", "ST", "Other"]
ID_PROOF_TYPES = ["Aadhaar", "PAN", "Voter ID", "Passport", "Driving License"]
PARTY_ROLES = ["Buyer 1", "Buyer 2", "Seller 1", "Seller 2", "Witness 1", "Witness 2", "Identifying Person"]

# ── Session State Helpers ───────────────────────────────────────────────
def init_state():
    defaults = {
        "current_registry_id": 0,
        "registries": [],           # list of dicts
        "parties": {},              # registry_id -> list of parties
        "properties": {},           # registry_id -> property dict
        "documents": {},            # registry_id -> list of docs
        "parsed_cache": {},         # file_name -> parsed data
        "gemini_key": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def next_registry_id():
    ids = [r.get("id", 0) for r in st.session_state["registries"]]
    return max(ids) + 1 if ids else 1

def get_registry(rid):
    return next((r for r in st.session_state["registries"] if r.get("id") == rid), None)

def add_registry(title="New Registry"):
    rid = next_registry_id()
    reg = {
        "id": rid,
        "title": title,
        "deed_category": "",
        "instrument": "",
        "district": "",
        "tehsil": "",
        "status": "draft",
        "current_step": "idle",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    st.session_state["registries"].append(reg)
    st.session_state["parties"][rid] = []
    st.session_state["properties"][rid] = {}
    st.session_state["documents"][rid] = []
    return rid

def update_registry(rid, fields):
    reg = get_registry(rid)
    if reg:
        reg.update(fields)
        reg["updated_at"] = datetime.now().isoformat()

def add_party(rid, data):
    st.session_state["parties"][rid].append(data)

def get_parties(rid):
    return st.session_state["parties"].get(rid, [])

def save_property(rid, data):
    st.session_state["properties"][rid] = data

def get_property(rid):
    return st.session_state["properties"].get(rid, {})

def add_document(rid, doc):
    st.session_state["documents"][rid].append(doc)

def get_documents(rid):
    return st.session_state["documents"].get(rid, [])

# ── Gemini AI Parser (Cloud-compatible) ───────────────────────────────────
@st.cache_resource
def get_gemini_model():
    key = st.session_state.get("gemini_key", "")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"Gemini init failed: {e}")
        return None

def extract_json(text):
    import re
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        raw = re.search(r"(\{.*\})", text, re.DOTALL)
        if raw:
            text = raw.group(1)
    try:
        return json.loads(text)
    except:
        return None

def parse_id_cloud(image_bytes, role_hint=""):
    model = get_gemini_model()
    if not model:
        return None
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes))
    prompt = f"""You are an expert OCR parser for Indian government ID cards (Aadhaar, PAN, Voter ID).
Analyze the image and output raw JSON with:
name_english, name_hindi (transliterated, not translated), father_husband_name_english, father_husband_name_hindi,
dob (DD-MM-YYYY), gender (Male/Female/Other), address_english, address_hindi (transliterate proper nouns, translate Road->मार्ग, Street->गली),
id_type (Aadhaar/PAN/Voter ID/Passport), id_number (12 digits for Aadhaar, 10 chars for PAN), pan_number, mobile_number, category.
Return ONLY valid JSON. Role: {role_hint}"""
    try:
        response = model.generate_content([prompt, img])
        return extract_json(response.text or "")
    except Exception as e:
        st.error(f"AI parsing failed: {e}")
        return None

def parse_property_cloud(image_bytes):
    model = get_gemini_model()
    if not model:
        return None
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes))
    prompt = """You are an expert OCR parser for Indian property documents.
Output raw JSON with: district, tehsil, area_type (Urban/Rural), ward_colony_name, plot_number,
total_area_sqmt, constructed_area_sqmt, road_width_mt, boundaries {east, west, north, south}.
Return ONLY valid JSON."""
    try:
        response = model.generate_content([prompt, img])
        return extract_json(response.text or "")
    except Exception as e:
        st.error(f"AI parsing failed: {e}")
        return None

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏛️ Sampada 2.0 Co-Pilot")
    st.markdown("<div class='hint-text'>Cloud Edition - Prepare data here, automate locally</div>", unsafe_allow_html=True)
    st.divider()

    # Gemini API Key
    key = st.text_input("🔑 Gemini API Key", value=st.session_state.get("gemini_key", ""), type="password", key="gemini_key_input")
    if key:
        st.session_state["gemini_key"] = key
        st.success("✅ Key set")

    st.divider()
    st.subheader("📋 Registries")

    if st.button("➕ New Registry", use_container_width=True):
        new_id = add_registry(f"Registry #{next_registry_id()}")
        st.session_state["current_registry_id"] = new_id
        st.rerun()

    # Import/Export JSON
    c1, c2 = st.columns(2)
    with c1:
        uploaded_json = st.file_uploader("📥 Import", type="json", key="import_json", label_visibility="collapsed")
        if uploaded_json:
            data = json.load(uploaded_json)
            st.session_state["registries"] = data.get("registries", [])
            st.session_state["parties"] = {int(k): v for k, v in data.get("parties", {}).items()}
            st.session_state["properties"] = {int(k): v for k, v in data.get("properties", {}).items()}
            st.session_state["documents"] = {int(k): v for k, v in data.get("documents", {}).items()}
            st.success("Imported!")
            st.rerun()
    with c2:
        if st.session_state["registries"]:
            export_data = {
                "registries": st.session_state["registries"],
                "parties": st.session_state["parties"],
                "properties": st.session_state["properties"],
                "documents": st.session_state["documents"],
            }
            st.download_button(
                "📤 Export", json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name="sampada_data.json", mime="application/json",
                use_container_width=True, key="export_json"
            )

    st.divider()
    for reg in st.session_state["registries"]:
        if st.button(f"{reg['title']}", key=f"reg_btn_{reg['id']}", use_container_width=True):
            st.session_state["current_registry_id"] = reg["id"]
            st.rerun()

    st.divider()
    st.markdown("<div class='hint-text'>v1.0 Cloud Edition</div>", unsafe_allow_html=True)

# ── Main Content ────────────────────────────────────────────────────────
rid = st.session_state.get("current_registry_id", 0)
if not rid:
    st.markdown("""
    <div class="card">
        <div class="card-title">Welcome to Sampada 2.0 Co-Pilot (Cloud)</div>
        <p>Create or import a registry from the sidebar to begin.</p>
        <p>This cloud version lets you:</p>
        <ul>
            <li>📄 Upload and AI-parse ID cards and property documents</li>
            <li>✍️ Review and edit Hindi/English fields</li>
            <li>💾 Export your data as JSON</li>
            <li>🖥️ Download the <b>local runner</b> to execute browser automation on your PC</li>
        </ul>
        <p><b>How it works:</b></p>
        <ol>
            <li>Upload documents here → AI extracts data</li>
            <li>Review & edit all fields in the browser</li>
            <li>Export JSON → download to your PC</li>
            <li>Run <code>local_runner.py</code> on your Windows machine → it opens Chrome and auto-fills the Sampada portal</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

reg = get_registry(rid)
if not reg:
    st.error("Registry not found.")
    st.stop()

st.title(f"🏛️ {reg.get('title', 'Registry')}")

upload_tab, review_tab, export_tab = st.tabs(["📤 Upload & Parse", "✍️ Review & Edit", "📤 Export for Local Runner"])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: Upload & Parse
# ═══════════════════════════════════════════════════════════════════════
with upload_tab:
    st.markdown("<div class='card-title'>Upload Documents</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🪪 ID Cards")
        id_files = st.file_uploader("Upload Aadhaar / PAN / Voter ID", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="id_uploader")
        if id_files:
            for i, uploaded in enumerate(id_files):
                role = st.selectbox(f"Role for {uploaded.name}", PARTY_ROLES, key=f"role_{uploaded.name}_{i}")
                if st.button(f"🔍 Parse {uploaded.name}", key=f"parse_{uploaded.name}_{i}"):
                    with st.spinner(f"Parsing {uploaded.name}..."):
                        parsed = parse_id_cloud(uploaded.getvalue(), role)
                        if parsed:
                            parsed["role"] = role
                            parsed["verified"] = 0
                            parsed["file_name"] = uploaded.name
                            add_party(rid, parsed)
                            add_document(rid, {"doc_type": "id_scan", "role_hint": role, "file_name": uploaded.name})
                            st.success(f"✅ Parsed: {parsed.get('name_english', 'Unknown')}")
                        else:
                            st.error("❌ Failed to parse")

    with col2:
        st.subheader("🏠 Property Documents")
        prop_files = st.file_uploader("Upload property deed / plan", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="prop_uploader")
        if prop_files:
            for uploaded in prop_files:
                if st.button(f"🔍 Parse Property: {uploaded.name}", key=f"parse_prop_{uploaded.name}"):
                    with st.spinner("Parsing property document..."):
                        parsed = parse_property_cloud(uploaded.getvalue())
                        if parsed:
                            save_property(rid, parsed)
                            add_document(rid, {"doc_type": "property_scan", "role_hint": "", "file_name": uploaded.name})
                            st.success("✅ Property details extracted")
                            st.json(parsed)
                        else:
                            st.error("❌ Failed to parse")

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: Review & Edit
# ═══════════════════════════════════════════════════════════════════════
with review_tab:
    st.markdown("<div class='card-title'>Human-in-the-Loop Review</div>", unsafe_allow_html=True)

    parties = get_parties(rid)
    if not parties:
        st.info("No parties parsed yet. Upload ID cards in the first tab.")
    else:
        st.subheader(f"🪪 Parties ({len(parties)})")
        for idx, p in enumerate(parties):
            with st.expander(f"{p['role']}: {p.get('name_english', 'Unnamed')}"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if p.get("file_name"):
                        st.info(f"Source: {p['file_name']}")
                    else:
                        st.info("No image")

                with c2:
                    p["name_english"] = st.text_input("Name (English)", p.get("name_english", ""), key=f"ne_{idx}")
                    p["name_hindi"] = st.text_input("Name (Hindi)", p.get("name_hindi", ""), key=f"nh_{idx}")
                    p["father_husband_name_english"] = st.text_input("Father/Husband (English)", p.get("father_husband_name_english", ""), key=f"fe_{idx}")
                    p["father_husband_name_hindi"] = st.text_input("Father/Husband (Hindi)", p.get("father_husband_name_hindi", ""), key=f"fh_{idx}")
                    p["dob"] = st.text_input("DOB (DD-MM-YYYY)", p.get("dob", ""), key=f"dob_{idx}")
                    p["gender"] = st.selectbox("Gender", GENDERS, index=GENDERS.index(p.get("gender", "Male")) if p.get("gender") in GENDERS else 0, key=f"gen_{idx}")
                    p["category"] = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(p.get("category", "General")) if p.get("category") in CATEGORIES else 0, key=f"cat_{idx}")
                    p["address_english"] = st.text_area("Address (English)", p.get("address_english", ""), key=f"ae_{idx}")
                    p["address_hindi"] = st.text_area("Address (Hindi)", p.get("address_hindi", ""), key=f"ah_{idx}")
                    p["id_type"] = st.selectbox("ID Type", ID_PROOF_TYPES, index=ID_PROOF_TYPES.index(p.get("id_type", "Aadhaar")) if p.get("id_type") in ID_PROOF_TYPES else 0, key=f"idt_{idx}")
                    p["id_number"] = st.text_input("ID Number", p.get("id_number", ""), key=f"idn_{idx}")
                    p["pan_number"] = st.text_input("PAN", p.get("pan_number", ""), key=f"pan_{idx}")
                    p["mobile_number"] = st.text_input("Mobile", p.get("mobile_number", ""), key=f"mob_{idx}")
                    p["verified"] = st.checkbox("Verified", bool(p.get("verified", 0)), key=f"ver_{idx}")
                    if st.button("💾 Save", key=f"save_p_{idx}"):
                        st.success("Party updated")

    st.divider()
    prop = get_property(rid)
    if prop:
        st.subheader("🏠 Property Details")
        with st.expander("Edit Property"):
            pc1, pc2 = st.columns(2)
            with pc1:
                prop["district"] = st.text_input("District", prop.get("district", ""), key="prop_dist")
                prop["tehsil"] = st.text_input("Tehsil", prop.get("tehsil", ""), key="prop_tehsil")
                prop["area_type"] = st.selectbox("Area Type", ["Urban", "Rural"], index=["Urban", "Rural"].index(prop.get("area_type", "Urban")) if prop.get("area_type") in ["Urban", "Rural"] else 0, key="prop_area")
                prop["ward_colony_name"] = st.text_input("Ward/Colony", prop.get("ward_colony_name", ""), key="prop_ward")
                prop["plot_number"] = st.text_input("Plot Number", prop.get("plot_number", ""), key="prop_plot")
            with pc2:
                prop["total_area_sqmt"] = st.number_input("Total Area", value=float(prop.get("total_area_sqmt", 0.0)), key="prop_total")
                prop["constructed_area_sqmt"] = st.number_input("Built-up Area", value=float(prop.get("constructed_area_sqmt", 0.0)), key="prop_built")
                prop["road_width_mt"] = st.number_input("Road Width", value=float(prop.get("road_width_mt", 0.0)), key="prop_road")
            b = prop.get("boundaries", {})
            c1, c2, c3, c4 = st.columns(4)
            with c1: b["north"] = st.text_input("North", b.get("north", ""), key="b_n")
            with c2: b["south"] = st.text_input("South", b.get("south", ""), key="b_s")
            with c3: b["east"] = st.text_input("East", b.get("east", ""), key="b_e")
            with c4: b["west"] = st.text_input("West", b.get("west", ""), key="b_w")
            prop["boundaries"] = b
            if st.button("💾 Save Property", key="save_prop"):
                save_property(rid, prop)
                st.success("Property saved")
    else:
        st.info("No property details parsed yet.")

    all_verified = all(bool(p.get("verified", 0)) for p in parties) if parties else False
    if all_verified and prop:
        st.success("✅ All parties verified & property filled. Ready for export.")
    elif parties:
        st.warning("⚠️ Mark all parties as Verified and save property before export.")

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: Export for Local Runner
# ═══════════════════════════════════════════════════════════════════════
with export_tab:
    st.markdown("<div class='card-title'>Export for Local Automation</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
        <p><b>Why export?</b> The browser automation (Playwright + headed Chrome + biometric RD Service) must run on your local Windows machine. This cloud dashboard prepares all the data. Export it as JSON, then run the local automation script.</p>
    </div>
    """, unsafe_allow_html=True)

    if reg:
        export_payload = {
            "registry": reg,
            "parties": get_parties(rid),
            "property": get_property(rid),
            "documents": get_documents(rid),
        }
        json_str = json.dumps(export_payload, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 Download JSON for Local Runner", json_str,
            file_name=f"registry_{rid}_for_local.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    st.subheader("🖥️ Local Runner Script")
    st.markdown("""
    Save this as `local_runner.py` on your Windows machine and run it after installing dependencies:
    ```bash
    pip install playwright
    playwright install chromium
    python local_runner.py --registry registry_1_for_local.json
    ```
    """)
    
    # Read local_runner.py from the project root
    runner_path = Path(__file__).resolve().parent.parent / "local_runner.py"
    if runner_path.exists():
        with open(runner_path, "r", encoding="utf-8") as f:
            runner_code = f.read()
        st.download_button(
            "📥 Download local_runner.py", runner_code,
            file_name="local_runner.py", mime="text/x-python",
            use_container_width=True,
        )
        st.code(runner_code, language="python")
    else:
        st.warning("local_runner.py not found in project directory.")
