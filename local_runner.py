"""
Sampada 2.0 Local Automation Runner (Improved)
Reads a JSON export from the cloud dashboard and executes Playwright
headed-browser automation on the Sampada 2.0 portal.

Usage:
    python local_runner.py --registry registry_1_for_local.json
    python local_runner.py --registry registry_1_for_local.json --debug

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

# ── Anti-Detection Script ────────────────────────────────────────────
ANTI_DETECT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
window.chrome = { runtime: {} };
window.navigator.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(parameter);
};
"""


def load_registry(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def take_screenshot(page: Page, name: str, debug_dir: Path):
    """Take a screenshot for debugging."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = debug_dir / f"{name}_{ts}.png"
        page.screenshot(path=str(path), full_page=True)
        print(f"  📸 Screenshot saved: {path}")
    except Exception as e:
        print(f"  Screenshot failed: {e}")


def launch_browser(headed: bool = True, debug_dir: Path = None):
    p = sync_playwright().start()
    
    # More realistic browser args to avoid detection
    args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--window-size=1920,1080",
        "--start-maximized",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-web-security",
        "--disable-features=BlockInsecurePrivateNetworkRequests",
    ]
    
    browser = p.chromium.launch(
        headless=not headed,
        args=args,
        slow_mo=SLOW_MO_MS,
        # Use a persistent context for cookies/session
    )
    
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        permissions=["geolocation"],
        geolocation=DEFAULT_GEO,
        accept_downloads=True,
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        color_scheme="light",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "DNT": "1",
        },
    )
    
    context.add_init_script(ANTI_DETECT_SCRIPT)
    
    page = context.new_page()
    
    # Set additional properties
    page.evaluate("""
        () => {
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
        }
    """)
    
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


def safe_goto(page: Page, url: str, timeout: int = 60000, debug_dir: Path = None):
    """Navigate to URL with retry and error handling."""
    print(f"  Navigating to: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        time.sleep(2)
        # Check if page loaded properly
        if page.title() == "" or "error" in page.title().lower():
            print(f"  WARNING: Page title suspicious: '{page.title()}'")
            if debug_dir:
                take_screenshot(page, "navigate_error", debug_dir)
        else:
            print(f"  Page title: {page.title()}")
        return True
    except Exception as e:
        print(f"  ERROR navigating: {e}")
        if debug_dir:
            take_screenshot(page, "navigate_exception", debug_dir)
        return False


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

def run_automation(data: dict, headed: bool = True, debug: bool = False):
    reg = data.get("registry", {})
    parties = data.get("parties", [])
    prop = data.get("property", {})
    
    # Create debug directory
    debug_dir = None
    if debug:
        debug_dir = Path("debug_screenshots")
        debug_dir.mkdir(exist_ok=True)
        print(f"\n  Debug screenshots will be saved to: {debug_dir.absolute()}")

    print("\n" + "="*60)
    print("  SAMPADA 2.0 LOCAL AUTOMATION RUNNER")
    print("="*60)
    print(f"\nRegistry: {reg.get('title', 'Unknown')}")
    print(f"Deed:     {reg.get('deed_category', 'Not set')}")
    print(f"Parties:  {len(parties)}")
    print(f"Property: {'YES' if prop else 'NO'}")
    print(f"\nLaunching {'headed' if headed else 'headless'} browser...")

    p, browser, context, page = launch_browser(headed=headed, debug_dir=debug_dir)
    
    if debug and debug_dir:
        take_screenshot(page, "browser_opened", debug_dir)

    try:
        # 1. Login page
        print(f"\n[1/8] Navigating to login page...")
        if not safe_goto(page, PORTAL_LOGIN, debug_dir=debug_dir):
            print("  Failed to load login page. Retrying in 5 seconds...")
            time.sleep(5)
            if not safe_goto(page, PORTAL_LOGIN, debug_dir=debug_dir):
                print("  ERROR: Could not load login page after retry. Exiting.")
                return
        
        if debug and debug_dir:
            take_screenshot(page, "login_page", debug_dir)
        
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
        
        if debug and debug_dir:
            take_screenshot(page, "dashboard", debug_dir)

        # 3. Navigate to e-Registry
        print(f"\n[3/8] Navigating to e-Registry...")
        if not safe_goto(page, PORTAL_E_REGISTRY, debug_dir=debug_dir):
            print("  Could not navigate to e-Registry.")
            return
        
        try:
            page.get_by_role("link", name=re.compile("e-registry|e-रजिस्ट्री|new|नया", re.IGNORECASE)).first.click(timeout=5000)
        except Exception:
            print("  Could not auto-click e-Registry link. Please click manually.")
            if not wait_for_resume(page, "E-REGISTRY: Click 'New Registry' or 'e-Registry' link."):
                return
        time.sleep(2)
        
        if debug and debug_dir:
            take_screenshot(page, "e_registry", debug_dir)

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
        if debug and debug_dir:
            take_screenshot(page, "fatal_error", debug_dir)
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
    parser.add_argument("--debug", action="store_true", help="Enable debug screenshots")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"ERROR: Registry file not found: {registry_path}")
        sys.exit(1)

    data = load_registry(str(registry_path))
    headed = args.headed and not args.headless
    run_automation(data, headed=headed, debug=args.debug)


if __name__ == "__main__":
    main()
