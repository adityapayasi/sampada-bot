"""
Sampada 2.0 Co-Pilot – Main Streamlit Dashboard
Phase 1: Input & AI Extraction + Registry Management
"""

import os
import sys
from pathlib import Path

# Ensure modules are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from PIL import Image

from modules import config
from modules.db_manager import (
    init_db,
    create_registry,
    list_registries,
    get_registry,
    update_registry,
    add_party,
    get_parties,
    save_property,
    get_property,
    add_document,
    get_documents,
    log_automation,
)
from modules.ai_parser import parse_id_card, parse_property_document
from modules.transliterator import transliterate_text

# ── Page Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout=config.PAGE_LAYOUT,
    initial_sidebar_state="expanded",
)

# ── Dark Mode CSS ───────────────────────────────────────────────────────
DARK_CSS = """
<style>
    .block-container { padding-top: 1rem; }
    .stButton>button { border-radius: 8px; }
    .stTextInput>div>div>input { border-radius: 6px; }
    .stTextArea>div>textarea { border-radius: 6px; }
    .stSelectbox>div>div { border-radius: 6px; }
    .stFileUploader>div>div>div { border-radius: 8px; border: 2px dashed #444; }
    .card {
        background-color: #1a1a2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #2a2a4e;
    }
    .card-title { color: #1E90FF; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-draft { background: #3d3d3d; color: #aaa; }
    .status-paused { background: #4a3b00; color: #f0c040; }
    .status-completed { background: #004d1a; color: #4ade80; }
    .status-error { background: #4a0000; color: #f87171; }
    .hint-text { color: #888; font-size: 0.85rem; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ── Init DB ───────────────────────────────────────────────────────────
init_db()

# ── Session State ───────────────────────────────────────────────────────
for key in ["current_registry_id", "uploaded_files", "parsed_parties", "parsed_property"]:
    if key not in st.session_state:
        st.session_state[key] = None if "id" in key else {}

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.markdown("<div class='hint-text'>MPIGR e-Registry Automation Co-Pilot</div>", unsafe_allow_html=True)
    st.divider()

    # API Key check
    if not config.GEMINI_API_KEY:
        st.warning("⚠️ GEMINI_API_KEY not set in environment. Add it to a `.env` file or set it in the OS environment.")
    else:
        st.success("✅ Gemini API connected")

    st.divider()

    # Registry selector
    st.subheader("📋 Registries")
    registries = list_registries()

    if st.button("➕ New Registry", use_container_width=True):
        new_id = create_registry(f"Registry #{len(registries) + 1}")
        st.session_state["current_registry_id"] = new_id
        st.session_state["parsed_parties"] = {}
        st.session_state["parsed_property"] = {}
        st.session_state["uploaded_files"] = {}
        st.rerun()

    st.divider()

    for reg in registries:
        status_class = f"status-{reg.get('status', 'draft')}"
        title = reg.get("title", f"Registry #{reg['id']}")
        step = reg.get("current_step", "idle")
        if st.button(f"{title} — {step}", key=f"reg_btn_{reg['id']}", use_container_width=True):
            st.session_state["current_registry_id"] = reg["id"]
            st.rerun()

    st.divider()
    st.markdown("<div class='hint-text'>v1.0 · Phase 1-4 Active</div>", unsafe_allow_html=True)

# ── Main Content ────────────────────────────────────────────────────────
registry_id = st.session_state.get("current_registry_id")

if not registry_id:
    st.markdown("""
    <div class="card">
        <div class="card-title">Welcome to Sampada 2.0 Co-Pilot</div>
        <p>Select or create a registry from the sidebar to begin.</p>
        <p>This automation bot helps you:</p>
        <ul>
            <li>📄 Extract data from ID cards using AI Vision (Gemini)</li>
            <li>🏠 Extract property details from scanned deeds & plans</li>
            <li>✍️ Review & edit Hindi/English fields before submission</li>
            <li>🤖 Auto-fill the MPIGR Sampada 2.0 portal via Playwright</li>
            <li>⏸️ Pause at KYC, Biometrics & Payment for human-in-the-loop</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

registry = get_registry(registry_id)
if not registry:
    st.error("Registry not found.")
    st.stop()

st.title(f"🏛️ {registry.get('title', 'Registry')}")

# Tabs
upload_tab, review_tab, automation_tab = st.tabs(["📤 Upload & Parse", "✍️ Review & Edit", "🤖 Automation"])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: Upload & Parse
# ═══════════════════════════════════════════════════════════════════════
with upload_tab:
    st.markdown("<div class='card-title'>Upload Documents</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🪪 ID Cards")
        id_files = st.file_uploader(
            "Upload Aadhaar / PAN / Voter ID scans",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="id_uploader",
        )

        if id_files:
            for i, uploaded in enumerate(id_files):
                role = st.selectbox(
                    f"Role for {uploaded.name}",
                    ["Buyer 1", "Buyer 2", "Seller 1", "Seller 2", "Witness 1", "Witness 2", "Identifying Person"],
                    key=f"role_{uploaded.name}_{i}",
                )
                if st.button(f"🔍 Parse {uploaded.name}", key=f"parse_{uploaded.name}_{i}"):
                    with st.spinner(f"Parsing {uploaded.name} with Gemini..."):
                        file_path = config.UPLOAD_DIR / uploaded.name
                        with open(file_path, "wb") as f:
                            f.write(uploaded.getbuffer())
                        add_document(registry_id, str(file_path), "id_scan", role, uploaded.name, uploaded.type)

                        try:
                            parsed = parse_id_card(str(file_path), role_hint=role)
                            if parsed:
                                st.session_state["parsed_parties"][role] = parsed
                                party_id = add_party(registry_id, parsed)
                                st.success(f"✅ Parsed: {parsed.get('name_english', 'Unknown')} ({role})")
                            else:
                                st.error(f"❌ Failed to parse {uploaded.name}")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

    with col2:
        st.subheader("🏠 Property Documents")
        prop_files = st.file_uploader(
            "Upload property deeds / plans / tax receipts",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="prop_uploader",
        )

        if prop_files:
            for uploaded in prop_files:
                if st.button(f"🔍 Parse Property: {uploaded.name}", key=f"parse_prop_{uploaded.name}"):
                    with st.spinner(f"Parsing property document..."):
                        file_path = config.UPLOAD_DIR / uploaded.name
                        with open(file_path, "wb") as f:
                            f.write(uploaded.getbuffer())
                        add_document(registry_id, str(file_path), "property_scan", "", uploaded.name, uploaded.type)

                        try:
                            parsed = parse_property_document(str(file_path))
                            if parsed:
                                st.session_state["parsed_property"] = parsed
                                save_property(registry_id, parsed)
                                st.success("✅ Property details extracted")
                                st.json(parsed)
                            else:
                                st.error(f"❌ Failed to parse property doc")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

    st.divider()
    st.markdown("<div class='hint-text'>Tip: After parsing, go to the 'Review & Edit' tab to verify all Hindi/English fields before automation.</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: Review & Edit (Inline HITL)
# ═══════════════════════════════════════════════════════════════════════
with review_tab:
    st.markdown("<div class='card-title'>Human-in-the-Loop Review</div>", unsafe_allow_html=True)

    parties = get_parties(registry_id)
    if not parties:
        st.info("No parties parsed yet. Upload ID cards in the first tab.")
    else:
        st.subheader(f"🪪 Parties ({len(parties)})")
        for p in parties:
            with st.expander(f"{p['role']}: {p['name_english'] or 'Unnamed'}"):
                c1, c2 = st.columns([1, 2])
                docs = get_documents(registry_id, "id_scan")
                doc = next((d for d in docs if d["role_hint"] == p["role"]), None)
                with c1:
                    if doc and Path(doc["file_path"]).exists():
                        st.image(doc["file_path"], use_container_width=True)
                    else:
                        st.info("No image")

                with c2:
                    new_data = {}
                    new_data["name_english"] = st.text_input("Name (English)", p.get("name_english", ""), key=f"ne_{p['id']}")
                    new_data["name_hindi"] = st.text_input("Name (Hindi)", p.get("name_hindi", ""), key=f"nh_{p['id']}")
                    if st.button("🔁 Transliterate Name", key=f"trans_name_{p['id']}"):
                        hindi = transliterate_text(new_data["name_english"])
                        if hindi:
                            st.session_state[f"nh_{p['id']}"] = hindi
                            st.rerun()

                    new_data["father_husband_name_english"] = st.text_input("Father/Husband Name (English)", p.get("father_husband_name_english", ""), key=f"fe_{p['id']}")
                    new_data["father_husband_name_hindi"] = st.text_input("Father/Husband Name (Hindi)", p.get("father_husband_name_hindi", ""), key=f"fh_{p['id']}")
                    new_data["dob"] = st.text_input("DOB (DD-MM-YYYY)", p.get("dob", ""), key=f"dob_{p['id']}")
                    new_data["gender"] = st.selectbox("Gender", config.GENDERS, index=config.GENDERS.index(p.get("gender", "Male")) if p.get("gender") in config.GENDERS else 0, key=f"gen_{p['id']}")
                    new_data["category"] = st.selectbox("Category", config.CATEGORIES, index=config.CATEGORIES.index(p.get("category", "General")) if p.get("category") in config.CATEGORIES else 0, key=f"cat_{p['id']}")
                    new_data["address_english"] = st.text_area("Address (English)", p.get("address_english", ""), key=f"ae_{p['id']}")
                    new_data["address_hindi"] = st.text_area("Address (Hindi)", p.get("address_hindi", ""), key=f"ah_{p['id']}")
                    new_data["id_type"] = st.selectbox("ID Type", config.ID_PROOF_TYPES, index=config.ID_PROOF_TYPES.index(p.get("id_type", "Aadhaar")) if p.get("id_type") in config.ID_PROOF_TYPES else 0, key=f"idt_{p['id']}")
                    new_data["id_number"] = st.text_input("ID Number", p.get("id_number", ""), key=f"idn_{p['id']}")
                    new_data["pan_number"] = st.text_input("PAN Number", p.get("pan_number", ""), key=f"pan_{p['id']}")
                    new_data["mobile_number"] = st.text_input("Mobile", p.get("mobile_number", ""), key=f"mob_{p['id']}")
                    new_data["verified"] = st.checkbox("Verified", bool(p.get("verified", 0)), key=f"ver_{p['id']}")

                    if st.button("💾 Save Party", key=f"save_p_{p['id']}"):
                        from modules.db_manager import update_party
                        update_party(p["id"], new_data)
                        st.success("Party updated")
                        st.rerun()

    # Property Review
    st.divider()
    prop = get_property(registry_id)
    if prop:
        st.subheader("🏠 Property Details")
        with st.expander("Edit Property"):
            pc1, pc2 = st.columns(2)
            with pc1:
                district = st.text_input("District", prop.get("district", ""), key="prop_dist")
                tehsil = st.text_input("Tehsil", prop.get("tehsil", ""), key="prop_tehsil")
                area_type = st.selectbox("Area Type", config.AREA_TYPES, index=config.AREA_TYPES.index(prop.get("area_type", "Urban")) if prop.get("area_type") in config.AREA_TYPES else 0, key="prop_area")
                ward_colony = st.text_input("Ward/Colony", prop.get("ward_colony_name", ""), key="prop_ward")
                plot_number = st.text_input("Plot Number", prop.get("plot_number", ""), key="prop_plot")
            with pc2:
                total_area = st.number_input("Total Area (sqmt)", value=prop.get("total_area_sqmt", 0.0), key="prop_total")
                constructed_area = st.number_input("Built-up Area (sqmt)", value=prop.get("constructed_area_sqmt", 0.0), key="prop_built")
                road_width = st.number_input("Road Width (mt)", value=prop.get("road_width_mt", 0.0), key="prop_road")

            boundaries = prop.get("boundaries", {})
            st.write("Boundaries")
            bcol1, bcol2, bcol3, bcol4 = st.columns(4)
            with bcol1:
                north = st.text_input("North", boundaries.get("north", ""), key="b_north")
            with bcol2:
                south = st.text_input("South", boundaries.get("south", ""), key="b_south")
            with bcol3:
                east = st.text_input("East", boundaries.get("east", ""), key="b_east")
            with bcol4:
                west = st.text_input("West", boundaries.get("west", ""), key="b_west")

            if st.button("💾 Save Property", key="save_prop"):
                updated = {
                    "district": district,
                    "tehsil": tehsil,
                    "area_type": area_type,
                    "ward_colony_name": ward_colony,
                    "plot_number": plot_number,
                    "total_area_sqmt": total_area,
                    "constructed_area_sqmt": constructed_area,
                    "road_width_mt": road_width,
                    "boundaries": {"north": north, "south": south, "east": east, "west": west},
                }
                save_property(registry_id, updated)
                st.success("Property saved")
                st.rerun()
    else:
        st.info("No property details parsed yet. Upload property documents in the first tab.")

    # Confirm button
    st.divider()
    all_verified = all(bool(p.get("verified", 0)) for p in parties) if parties else False
    if all_verified and prop:
        st.success("✅ All parties verified & property filled. Ready for automation.")
        if st.button("🚀 Confirm & Go to Automation", use_container_width=True, type="primary"):
            st.session_state["go_to_automation"] = True
            st.rerun()
    elif parties:
        st.warning("⚠️ Mark all parties as 'Verified' and ensure property details are saved before automation.")

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: Automation Control
# ═══════════════════════════════════════════════════════════════════════
with automation_tab:
    st.markdown("<div class='card-title'>Playwright Automation Control</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
        <p>This panel will launch a <b>headed</b> Chrome/Edge browser and guide you through:</p>
        <ol>
            <li>Login & Captcha (you solve it manually)</li>
            <li>Deed Category selection</li>
            <li>District → Tehsil → Patwari Halka → Ward dropdowns</li>
            <li>Party details auto-fill (Buyer, Seller, Witness)</li>
            <li>Property dimensions & boundaries</li>
            <li><b>PAUSE</b> at e-KYC / Video KYC / Biometrics</li>
            <li><b>PAUSE</b> at Payment gateway</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        deed = st.selectbox("Deed Category", config.DEED_CATEGORIES, key="auto_deed")
    with col2:
        instrument = st.text_input("Instrument Type (if known)", key="auto_inst")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 Start Browser Automation", use_container_width=True, type="primary"):
            update_registry(registry_id, {
                "deed_category": deed,
                "instrument": instrument,
                "current_step": "login_wait",
            })
            st.info("Launching headed browser... Please wait.")
            # Launch automation in a separate thread/process
            try:
                from modules.playwright_automation import SampadaAutomation
                bot = SampadaAutomation(registry_id)
                bot.start_automation()
                st.success("Browser launched! Check the new Chrome window. Solve login + captcha, then click 'Resume' here.")
            except Exception as e:
                st.error(f"Failed to launch automation: {e}")
                log_automation(registry_id, "launch", "error", str(e))

    st.divider()
    st.subheader("⏸️ Pause / Resume Controls")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶️ Resume Bot", use_container_width=True):
            from modules.playwright_automation import resume_bot
            resume_bot(registry_id)
            st.success("Resume signal sent")
    with c2:
        if st.button("⏹️ Stop Bot", use_container_width=True):
            from modules.playwright_automation import stop_bot
            stop_bot(registry_id)
            st.warning("Stop signal sent")

    st.divider()
    st.subheader("📜 Automation Logs")
    logs = get_logs(registry_id)
    if logs:
        for log in logs[-20:]:
            color = "🟢" if log["status"] == "success" else "🔴" if log["status"] == "error" else "🟡"
            st.write(f"{color} **{log['step']}** — {log['status']} | {log['message']}")
    else:
        st.info("No automation logs yet.")
