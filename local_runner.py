"""
Sampada 2.0 Local Automation Runner
Reads a JSON export from the cloud dashboard and executes Playwright
headed-browser automation on the Sampada 2.0 portal.

Usage:
    python local_runner.py --registry registry_1_for_local.json
    python local_runner.py --registry registry_1_for_local.json --headed

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import time
import re
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Page, expect
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright")
    print("Then: playwright install chromium")
    sys.exit(1)

# ── Portal URLs ──────────────────────────────────────────────────────
PORTAL_BASE = "https://sampada.mpigr.gov.in"
PORTAL_LOGIN = f"{PORTAL_BASE}/#/clogin"
PORTAL_DASHBOARD = f"{PORTAL_BASE}/#/citizen/dashboard"
PORTAL_E_REGISTRY = f"{PORTAL_BASE}/#/citizen/e-registry"

DEFAULT_GEO = {"latitude": 22.7196, "longitude": 75.8577}
SLOW_MO_MS = 500


def load_registry(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def launch_browser(headed: bool = True):
    p = sync_playwright().start()
    args = ["--disable-blink-features=AutomationControlled"]
    browser = p.chromium.launch(headless=not headed, args=args, slow_mo=SLOW_MO_MS)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        permissions=["geolocation"],
        geolocation=DEFAULT_GEO,
        accept_downloads=True,
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)
    page = context.new_page()
    return p, browser, context, page


def wait_for_resume(page: Page, reason: str) -> bool:
    """Pause automation and wait for user input in the terminal."""
    print(f"\n{'='*60}")
    print(f"  PAUSE: {reason}")
    print(f"{'='*60}")
    print(f"  Browser is at: {page.url}")
    print(f"  Please complete the step manually in the browser window.")
    print(f"  When done, press ENTER in this terminal to continue.")
    print(f"  Or type 'stop' to abort.")
    print(f"{'='*60}")
    try:
        response = input("> ")
    except (EOFError, KeyboardInterrupt):
        response = "stop"
    if response.strip().lower() == "stop":
        print("Automation stopped by user.")
        return False
    print(f"Resuming...")
    time.sleep(1)
    return True


def select_dropdown(page: Page, placeholder_keywords: list, value: str, timeout: int = 15000):
    """Heuristic dropdown selector based on placeholder/label text."""
    try:
        selects = page.query_selector_all("select")
        for sel in selects:
            label = (sel.get_attribute("aria-label") or "").lower()
            placeholder = (sel.get_attribute("placeholder") or "").lower()
            id_attr = (sel.get_attribute("id") or "").lower()
            combined = f"{label} {placeholder} {id_attr}"
            if any(kw in combined for kw in placeholder_keywords):
                sel.select_option(label=value)
                time.sleep(1.5)
                return True
        # Fallback: try nth select
        if len(selects) > 0 and value:
            selects[0].select_option(label=value)
            time.sleep(1.5)
            return True
    except Exception as e:
        print(f"  Dropdown selection warning: {e}")
    return False


def fill_input(page: Page, keywords: list, value: str):
    """Heuristic input filler."""
    try:
        inputs = page.query_selector_all("input, textarea")
        for inp in inputs:
            if not value:
                continue
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            label = (inp.get_attribute("aria-label") or "").lower()
            id_attr = (inp.get_attribute("id") or "").lower()
            name_attr = (inp.get_attribute("name") or "").lower()
            combined = f"{placeholder} {label} {id_attr} {name_attr}"
            if any(kw in combined for kw in keywords):
                inp.fill(value)
                return True
    except Exception:
        pass
    return False


# ── Main Automation Flow ─────────────────────────────────────────────

def run_automation(data: dict, headed: bool = True):
    reg = data.get("registry", {})
    parties = data.get("parties", [])
    prop = data.get("property", {})

    print("\n" + "="*60)
    print("  SAMPADA 2.0 LOCAL AUTOMATION RUNNER")
    print("="*60)
    print(f"\nRegistry: {reg.get('title', 'Unknown')}")
    print(f"Deed:     {reg.get('deed_category', 'Not set')}")
    print(f"Parties:  {len(parties)}")
    print(f"Property: {'YES' if prop else 'NO'}")
    print(f"\nLaunching {'headed' if headed else 'headless'} browser...")

    p, browser, context, page = launch_browser(headed=headed)

    try:
        # 1. Login page
        print(f"\n[1/8] Navigating to login page...")
        page.goto(PORTAL_LOGIN, wait_until="networkidle")
        if not wait_for_resume(page, "LOGIN: Enter username, password, captcha, and OTP. Then click Login."):
            return

        # 2. Wait for dashboard
        print(f"\n[2/8] Checking for dashboard...")
        try:
            page.wait_for_url(lambda url: "/citizen/dashboard" in url, timeout=60000)
            print("  Dashboard detected!")
        except Exception:
            print("  WARNING: Dashboard not detected. Assuming user logged in.")
            time.sleep(3)

        # 3. Navigate to e-Registry
        print(f"\n[3/8] Navigating to e-Registry...")
        page.goto(PORTAL_E_REGISTRY, wait_until="networkidle")
        try:
            page.get_by_role("link", name=re.compile("e-registry|e-रजिस्ट्री|new|नया", re.IGNORECASE)).first.click(timeout=5000)
        except Exception:
            print("  Could not auto-click e-Registry link. Please click manually.")
            wait_for_resume(page, "E-REGISTRY: Click 'New Registry' or 'e-Registry' link.")
        time.sleep(2)

        # 4. Deed Category selection
        print(f"\n[4/8] Selecting deed category...")
        deed = reg.get("deed_category", "Sale Deed")
        select_dropdown(page, ["deed", "category", "document"], deed)
        time.sleep(2)

        # 5. Dropdown sync (District -> Tehsil -> Halka -> Ward)
        print(f"\n[5/8] Filling location dropdowns...")
        district = prop.get("district", "Indore")
        tehsil = prop.get("tehsil", "Indore")
        ward = prop.get("ward_colony_name", "")
        select_dropdown(page, ["district"], district)
        time.sleep(2.5)
        select_dropdown(page, ["tehsil"], tehsil)
        time.sleep(2.5)
        if ward:
            select_dropdown(page, ["ward", "colony", "village"], ward)
            time.sleep(2)
        print("  Dropdowns filled.")

        # 6. Party filling
        print(f"\n[6/8] Filling party details ({len(parties)} parties)...")
        for party in parties:
            role = party.get("role", "Party")
            print(f"  Adding {role}: {party.get('name_english', '')}")
            try:
                add_btn = page.get_by_role("button", name=re.compile("add party|नया पक्ष|add buyer|add seller|जोड़ें", re.IGNORECASE)).first
                if add_btn:
                    add_btn.click()
                    time.sleep(1.5)
            except Exception:
                pass

            # Fill all possible fields
            fill_input(page, ["name"], party.get("name_english", ""))
            fill_input(page, ["name", "hindi"], party.get("name_hindi", ""))
            fill_input(page, ["father", "husband"], party.get("father_husband_name_english", ""))
            fill_input(page, ["father", "husband", "hindi"], party.get("father_husband_name_hindi", ""))
            fill_input(page, ["address"], party.get("address_english", ""))
            fill_input(page, ["address", "hindi"], party.get("address_hindi", ""))
            fill_input(page, ["dob", "birth", "date"], party.get("dob", ""))
            fill_input(page, ["aadhaar", "id number"], party.get("id_number", ""))
            fill_input(page, ["pan"], party.get("pan_number", ""))
            fill_input(page, ["mobile", "phone"], party.get("mobile_number", ""))

            select_dropdown(page, ["gender"], party.get("gender", ""))
            select_dropdown(page, ["category", "caste"], party.get("category", ""))
            select_dropdown(page, ["id proof", "id type"], party.get("id_type", ""))

            # Save party
            try:
                page.get_by_role("button", name=re.compile("save|submit|जमा|जोड़ें", re.IGNORECASE)).first.click(timeout=3000)
                time.sleep(1.5)
            except Exception:
                pass
            print(f"  {role} filled.")

        # 7. Property filling
        print(f"\n[7/8] Filling property details...")
        fill_input(page, ["plot"], prop.get("plot_number", ""))
        fill_input(page, ["total area"], str(prop.get("total_area_sqmt", "")))
        fill_input(page, ["constructed", "built"], str(prop.get("constructed_area_sqmt", "")))
        fill_input(page, ["road", "width"], str(prop.get("road_width_mt", "")))
        b = prop.get("boundaries", {})
        fill_input(page, ["north"], b.get("north", ""))
        fill_input(page, ["south"], b.get("south", ""))
        fill_input(page, ["east"], b.get("east", ""))
        fill_input(page, ["west"], b.get("west", ""))
        print("  Property filled.")

        # 8. KYC / Payment pause points
        print(f"\n[8/8] Reaching KYC / Biometric step...")
        wait_for_resume(page, "KYC/BIOMETRICS: Complete e-KYC, Video KYC, and fingerprint scan. Then resume.")

        print(f"\nReaching Payment Gateway...")
        wait_for_resume(page, "PAYMENT: Pay stamp duty and registration fees. Then resume.")

        print(f"\n{'='*60}")
        print(f"  AUTOMATION COMPLETE")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\nClosing browser in 5 seconds...")
        time.sleep(5)
        context.close()
        browser.close()
        p.stop()
        print("Done.")


# ── CLI Entry Point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sampada 2.0 Local Automation Runner")
    parser.add_argument("--registry", "-r", required=True, help="Path to the JSON export from the cloud dashboard")
    parser.add_argument("--headed", action="store_true", default=True, help="Run in headed mode (default)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (not recommended for Sampada)")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"ERROR: Registry file not found: {registry_path}")
        sys.exit(1)

    data = load_registry(str(registry_path))
    headed = args.headed and not args.headless
    run_automation(data, headed=headed)


if __name__ == "__main__":
    main()
