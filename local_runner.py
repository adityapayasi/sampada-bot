"""
Sampada 2.0 Local Automation Runner - Full Page Support
Handles wide pages, scrolling, and JavaScript-heavy forms.

Usage:
    python local_runner.py --registry registry_1.json
    python local_runner.py --registry registry_1.json --debug
"""

import argparse
import json
import time
import re
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright")
    print("Then: playwright install chromium")
    sys.exit(1)

PORTAL_BASE = "https://sampada.mpigr.gov.in"
PORTAL_LOGIN = f"{PORTAL_BASE}/#/clogin"
PORTAL_DASHBOARD = f"{PORTAL_BASE}/#/citizen/dashboard"
PORTAL_E_REGISTRY = f"{PORTAL_BASE}/#/citizen/e-registry"

DEFAULT_GEO = {"latitude": 22.7196, "longitude": 75.8577}
SLOW_MO_MS = 500

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
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = debug_dir / f"{name}_{ts}.png"
        page.screenshot(path=str(path), full_page=True)
        print(f"  [SCREENSHOT] Saved: {path}")
    except Exception as e:
        print(f"  [SCREENSHOT] Failed: {e}")


def launch_browser(headed: bool = True):
    p = sync_playwright().start()
    args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--window-size=1920,1080",
        "--start-maximized",
        "--force-device-scale-factor=1",
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
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1,
        permissions=["geolocation"],
        geolocation=DEFAULT_GEO,
        accept_downloads=True,
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        color_scheme="light",
    )
    context.add_init_script(ANTI_DETECT_SCRIPT)
    page = context.new_page()
    page.evaluate("""
        () => {
            document.body.style.zoom = '100%';
            document.body.style.transform = 'none';
            document.body.style.transformOrigin = 'top left';
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
        }
    """)
    try:
        page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
    except Exception:
        pass
    return p, browser, context, page


def wait_for_resume(page: Page, reason: str) -> bool:
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
    print("Resuming...")
    time.sleep(1)
    return True


def safe_goto(page: Page, url: str, timeout: int = 60000):
    print(f"  Navigating to: {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout)
        time.sleep(3)
        title = page.title()
        try:
            print(f"  Page title: {title}")
        except UnicodeEncodeError:
            print(f"  Page title: [Unicode title]")
        return True
    except Exception as e:
        print(f"  ERROR navigating: {e}")
        return False


def scroll_to_element(page: Page, element):
    """Scroll element into view and wait."""
    try:
        element.scroll_into_view_if_needed()
        time.sleep(0.5)
    except Exception:
        pass


def select_dropdown(page: Page, placeholder_keywords: list, value: str, timeout: int = 30000):
    """Wait for dropdown to be populated and select option."""
    try:
        # First, try to find the dropdown
        selects = page.query_selector_all("select")
        target_sel = None
        for sel in selects:
            label = (sel.get_attribute("aria-label") or "").lower()
            placeholder = (sel.get_attribute("placeholder") or "").lower()
            id_attr = (sel.get_attribute("id") or "").lower()
            combined = f"{label} {placeholder} {id_attr}"
            if any(kw in combined for kw in placeholder_keywords):
                target_sel = sel
                break
        
        if not target_sel and len(selects) > 0:
            target_sel = selects[0]
        
        if not target_sel or not value:
            return False
        
        # Scroll into view
        scroll_to_element(page, target_sel)
        
        # Wait for dropdown to have options (not just empty)
        print(f"  Waiting for dropdown options to load...")
        for attempt in range(10):
            options = target_sel.query_selector_all("option")
            if len(options) > 1:
                print(f"  Found {len(options)} options in dropdown")
                break
            time.sleep(1)
        
        # Try to select by value or label
        try:
            target_sel.select_option(value=value)
            print(f"  Selected by value: {value}")
            time.sleep(2)
            return True
        except Exception:
            try:
                target_sel.select_option(label=value)
                print(f"  Selected by label: {value}")
                time.sleep(2)
                return True
            except Exception:
                print(f"  Could not select '{value}' - option not found")
                return False
                
    except Exception as e:
        print(f"  Dropdown warning: {e}")
    return False


def fill_input(page: Page, keywords: list, value: str):
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
                scroll_to_element(page, inp)
                inp.fill(value)
                print(f"    [FILL] Filled field matching {keywords} with '{value}'")
                return True
        print(f"    [WARN] No input field found matching keywords: {keywords}")
    except Exception as e:
        print(f"    [ERROR] Failed to fill field matching {keywords}: {e}")
    return False


def click_button(page: Page, keywords: list, timeout: int = 3000):
    """Try to find and click a button by keyword."""
    try:
        buttons = page.query_selector_all("button, [role='button'], a, input[type='submit']")
        for btn in buttons:
            text = (btn.inner_text() or "").lower()
            aria = (btn.get_attribute("aria-label") or "").lower()
            combined = f"{text} {aria}"
            if any(kw in combined for kw in keywords):
                scroll_to_element(page, btn)
                btn.click()
                time.sleep(1.5)
                return True
    except Exception:
        pass
    return False


# Main Automation Flow

def run_automation(data: dict, headed: bool = True, debug: bool = False):
    reg = data.get("registry", {})
    parties = data.get("parties", [])
    prop = data.get("property", {})
    
    debug_dir = None
    if debug:
        debug_dir = Path.home() / "OneDrive" / "Desktop" / "sampada_debug"
        debug_dir.mkdir(exist_ok=True, parents=True)
        print(f"\n  Debug screenshots: {debug_dir}")

    print("\n" + "="*60)
    print("  SAMPADA 2.0 LOCAL AUTOMATION RUNNER")
    print("="*60)
    print(f"\nRegistry: {reg.get('title', 'Unknown')}")
    print(f"Deed:     {reg.get('deed_category', 'Not set')}")
    print(f"Parties:  {len(parties)}")
    print(f"Property: {'YES' if prop else 'NO'}")
    print(f"\nLaunching {'headed' if headed else 'headless'} browser...")

    p, browser, context, page = launch_browser(headed=headed)
    
    if debug and debug_dir:
        take_screenshot(page, "01_browser_opened", debug_dir)

    try:
        # 1. Login page
        print(f"\n[1/8] Navigating to login page...")
        if not safe_goto(page, PORTAL_LOGIN):
            print("  Retrying in 5 seconds...")
            time.sleep(5)
            if not safe_goto(page, PORTAL_LOGIN):
                print("  ERROR: Could not load login page. Exiting.")
                return
        
        if debug and debug_dir:
            take_screenshot(page, "02_login_page", debug_dir)
        
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
            take_screenshot(page, "03_dashboard", debug_dir)

        # 3. Navigate to e-Registry
        print(f"\n[3/8] Navigating to e-Registry...")
        if not safe_goto(page, PORTAL_E_REGISTRY):
            print("  Could not navigate to e-Registry.")
            return
        
        # Try to click e-Registry link
        try:
            page.get_by_role("link", name=re.compile("e-registry|e-registry|new|naya", re.IGNORECASE)).first.click(timeout=5000)
        except Exception:
            # Try clicking by button if link not found
            if not click_button(page, ["e-registry", "registry", "new", "naya", "e registry"]):
                print("  Could not auto-click e-Registry link. Please click manually.")
                if not wait_for_resume(page, "E-REGISTRY: Click 'New Registry' or 'e-Registry' link."):
                    return
        time.sleep(2)
        
        if debug and debug_dir:
            take_screenshot(page, "04_e_registry", debug_dir)

        # 4. Deed Category
        print(f"\n[4/8] Selecting deed category...")
        deed = reg.get("deed_category", "Sale Deed")
        select_dropdown(page, ["deed", "category", "document"], deed)
        time.sleep(2)

        # 5. Dropdowns
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

        # Pause to let the user navigate to the Plot Identification page
        if not wait_for_resume(page, "PROPERTY STEP: If needed, click Proceed/Next in the browser to navigate to the Plot Identification (Property details) page."):
            return

        # 6. Property details filling
        print(f"\n[6/8] Filling property details...")
        try:
            page.wait_for_selector("input", state="visible", timeout=10000)
            time.sleep(2)
        except Exception:
            print("  [WARN] Timeout waiting for inputs to load on Property page. Attempting to fill...")

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

        # Pause to let the user save the property and navigate to the Parties page
        if not wait_for_resume(page, "PARTY STEP: Click Save/Next on the property page to navigate to the Party details page."):
            return

        # 7. Party filling
        print(f"\n[7/8] Filling party details ({len(parties)} parties)...")
        try:
            page.wait_for_selector("input", state="visible", timeout=10000)
            time.sleep(2)
        except Exception:
            print("  [WARN] Timeout waiting for inputs to load on Parties page. Attempting to fill...")

        for party in parties:
            role = party.get("role", "Party")
            print(f"  Adding {role}: {party.get('name_english', '')}")
            
            # Try to click Add Party button
            if not click_button(page, ["add party", "naya paksh", "add buyer", "add seller", "joden", "add", "new"]):
                try:
                    add_btn = page.get_by_role("button", name=re.compile("add party|naya paksh|add buyer|add seller|joden", re.IGNORECASE)).first
                    if add_btn:
                        add_btn.click()
                        time.sleep(1.5)
                except Exception:
                    pass

            # Fill all possible fields with scrolling
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
            if not click_button(page, ["save", "submit", "jama", "joden", "save party"]):
                try:
                    page.get_by_role("button", name=re.compile("save|submit|jama|joden", re.IGNORECASE)).first.click(timeout=3000)
                    time.sleep(1.5)
                except Exception:
                    pass
            print(f"  {role} filled.")

        # 8. KYC / Payment
        print(f"\n[8/8] Reaching KYC / Biometric step...")
        wait_for_resume(page, "KYC/BIOMETRICS: Complete e-KYC, Video KYC, and fingerprint scan. Then resume.")

        print("\nReaching Payment Gateway...")
        wait_for_resume(page, "PAYMENT: Pay stamp duty and registration fees. Then resume.")

        print(f"\n{'='*60}")
        print(f"  AUTOMATION COMPLETE")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if debug and debug_dir:
            take_screenshot(page, "99_fatal_error", debug_dir)
    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        context.close()
        browser.close()
        p.stop()
        print("Done.")


# CLI Entry Point

def main():
    parser = argparse.ArgumentParser(description="Sampada 2.0 Local Automation Runner")
    parser.add_argument("--registry", "-r", required=True, help="Path to JSON export")
    parser.add_argument("--headed", action="store_true", default=True, help="Run in headed mode")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
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
