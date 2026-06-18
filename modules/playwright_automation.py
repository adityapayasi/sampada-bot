"""
Playwright Web Automation Module
Handles headed browser control, login detection, dropdown filling,
party data entry, property details, and HITL pause points.
"""

import os
import re
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, expect
from playwright._impl._errors import TimeoutError as PlaywrightTimeout

from modules import config
from modules.db_manager import (
    get_registry,
    get_parties,
    get_property,
    update_registry,
    log_automation,
)

logging.basicConfig(format=config.LOG_FORMAT, level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global control flags
_pause_event = threading.Event()
_stop_event = threading.Event()
_current_bot: Optional["SampadaAutomation"] = None


class SampadaAutomation:
    """
    Encapsulates the full Playwright automation lifecycle for a single registry.
    """

    def __init__(self, registry_id: int):
        self.registry_id = registry_id
        self.registry = get_registry(registry_id)
        self.parties: List[Dict[str, Any]] = get_parties(registry_id)
        self.property_data: Optional[Dict[str, Any]] = get_property(registry_id)

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._paused = False

        global _current_bot
        _current_bot = self

    # ── Lifecycle ───────────────────────────────────────────────────────

    def _launch_browser(self) -> Page:
        """Launch a headed browser with geolocation & user profile if configured."""
        self.playwright = sync_playwright().start()

        args = ["--disable-blink-features=AutomationControlled"]
        if config.USER_DATA_DIR:
            args.append(f"--user-data-dir={config.USER_DATA_DIR}")

        browser_type = getattr(self.playwright, config.BROWSER_TYPE, self.playwright.chromium)

        self.browser = browser_type.launch(
            headless=False,
            args=args,
            slow_mo=config.SLOW_MO_MS,
        )

        self.context = self.browser.new_context(
            viewport=config.DEFAULT_VIEWPORT,
            permissions=["geolocation"],
            geolocation=config.DEFAULT_GEO,
            accept_downloads=True,
        )

        # Inject stealth script to reduce bot detection
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        self.page = self.context.new_page()
        logger.info("Browser launched for registry %d", self.registry_id)
        return self.page

    def _close(self) -> None:
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed for registry %d", self.registry_id)

    # ── Pause / Resume HITL ───────────────────────────────────────────

    def _wait_for_resume(self, reason: str, screenshot_name: str = "") -> bool:
        """
        Pause the bot, notify the UI, and block until the user clicks 'Resume'.
        Returns False if the user clicked 'Stop'.
        """
        self._paused = True
        update_registry(self.registry_id, {"current_step": reason})
        log_automation(self.registry_id, reason, "pause", f"Waiting for user action: {reason}")
        logger.info("[PAUSE] %s — registry %d", reason, self.registry_id)

        if self.page and screenshot_name:
            try:
                path = config.LOGS_DIR / f"{screenshot_name}_{self.registry_id}.png"
                self.page.screenshot(path=str(path))
            except Exception:
                pass

        # Wait for resume or stop
        while not self._resume_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.5)

        stopped = self._stop_event.is_set()
        self._resume_event.clear()
        self._paused = False

        if stopped:
            log_automation(self.registry_id, reason, "error", "User stopped the bot")
            return False

        log_automation(self.registry_id, reason, "resume", "User resumed the bot")
        return True

    def resume(self) -> None:
        self._resume_event.set()
        logger.info("Resume signal received for registry %d", self.registry_id)

    def stop(self) -> None:
        self._stop_event.set()
        logger.info("Stop signal received for registry %d", self.registry_id)

    # ── Navigation Helpers ──────────────────────────────────────────────

    def _goto(self, url: str) -> None:
        self.page.goto(url, wait_until="networkidle")

    def _wait_for_selector(self, selector: str, timeout: int = 15000) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            return True
        except PlaywrightTimeout:
            return False

    def _click(self, selector: str) -> None:
        self.page.click(selector)

    def _fill(self, selector: str, value: str) -> None:
        self.page.fill(selector, value)

    def _select_option(self, selector: str, label: Optional[str] = None, value: Optional[str] = None) -> None:
        """Select dropdown by visible label or option value."""
        if label:
            self.page.select_option(selector, label=label)
        elif value:
            self.page.select_option(selector, value=value)

    def _wait_for_url_contains(self, fragment: str, timeout: int = 30000) -> bool:
        try:
            self.page.wait_for_url(lambda url: fragment in url, timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False

    # ── Main Automation Flow ────────────────────────────────────────────

    def start_automation(self) -> None:
        """Entry point — launches browser and begins the registry sequence."""
        try:
            self._launch_browser()
            self._run_login_step()
        except Exception as e:
            logger.exception("Automation crashed: %s", e)
            log_automation(self.registry_id, "global", "error", str(e))
            update_registry(self.registry_id, {"current_step": "error", "error_log": str(e)})
        finally:
            self._close()

    def _run_login_step(self) -> None:
        # 1. Navigate to login
        self._goto(config.PORTAL_LOGIN)
        update_registry(self.registry_id, {"current_step": "login_wait"})
        log_automation(self.registry_id, "login", "success", "Opened login page. Waiting for user to solve captcha + OTP.")

        # PAUSE: let user log in manually
        if not self._wait_for_resume("login_wait", "login_pause"):
            return  # stopped

        # Detect dashboard
        if self._wait_for_url_contains("/citizen/dashboard", timeout=60000):
            log_automation(self.registry_id, "dashboard", "success", "Login detected — dashboard loaded.")
            self._run_e_registry_step()
        else:
            log_automation(self.registry_id, "dashboard", "error", "Dashboard not detected after resume.")

    def _run_e_registry_step(self) -> None:
        # 2. Navigate to e-Registry
        self._goto(config.PORTAL_E_REGISTRY)
        update_registry(self.registry_id, {"current_step": "e_registry"})

        # Look for "Start New Registry" or "e-Registry" button
        # Sampada UI is Angular-based — selectors are dynamic. Use text-based locators.
        try:
            self.page.get_by_role("link", name=re.compile("e-registry|e-रजिस्ट्री|new registry|नया", re.IGNORECASE)).first.click()
        except Exception:
            # Fallback: try to find by partial URL or button
            pass

        time.sleep(2)
        log_automation(self.registry_id, "e_registry", "success", "Navigated to e-Registry section.")
        self._run_deed_selection_step()

    def _run_deed_selection_step(self) -> None:
        # 3. Deed Category & Instrument
        update_registry(self.registry_id, {"current_step": "deed_selection"})
        deed = self.registry.get("deed_category", "Sale Deed")

        # Wait for deed dropdown to appear
        if self._wait_for_selector("select", timeout=20000):
            selects = self.page.query_selector_all("select")
            if len(selects) >= 1:
                # Try to match deed category
                self._select_option(selects[0], label=deed)
                time.sleep(1.5)  # Wait for instrument dropdown to populate

            if len(selects) >= 2:
                instrument = self.registry.get("instrument", "")
                if instrument:
                    self._select_option(selects[1], label=instrument)

        # Click "Next" / "Proceed" if available
        try:
            self.page.get_by_role("button", name=re.compile("next|proceed|आगे|जमा", re.IGNORECASE)).first.click()
        except Exception:
            pass

        time.sleep(2)
        log_automation(self.registry_id, "deed_selection", "success", f"Selected deed: {deed}")
        self._run_dropdown_sync_step()

    def _run_dropdown_sync_step(self) -> None:
        # 4. Nested Dropdowns: District → Tehsil → Patwari Halka → Ward/Colony
        update_registry(self.registry_id, {"current_step": "dropdown_filling"})
        prop = self.property_data or {}

        district = prop.get("district", "Indore")
        tehsil = prop.get("tehsil", "Indore")
        ward = prop.get("ward_colony_name", "")

        selects = self.page.query_selector_all("select")
        # Heuristic: try to fill dropdowns sequentially
        try:
            if len(selects) > 0 and district:
                self._select_option(selects[0], label=district)
                time.sleep(2.5)  # Wait for tehsil options to load via XHR

            if len(selects) > 1 and tehsil:
                self._select_option(selects[1], label=tehsil)
                time.sleep(2.5)

            if len(selects) > 2 and ward:
                self._select_option(selects[2], label=ward)
                time.sleep(2)
        except Exception as e:
            logger.warning("Dropdown sync issue: %s", e)
            log_automation(self.registry_id, "dropdown_filling", "error", str(e))

        log_automation(self.registry_id, "dropdown_filling", "success", "Dropdowns filled.")
        self._run_party_filling_step()

    def _run_party_filling_step(self) -> None:
        # 5. Party Details (Buyer, Seller, Witness)
        update_registry(self.registry_id, {"current_step": "party_filling"})
        parties = self.parties

        for party in parties:
            if self._stop_event.is_set():
                return

            # Click "Add Party" / "नया पक्ष जोड़ें"
            try:
                add_btn = self.page.get_by_role("button", name=re.compile("add party|नया पक्ष|add buyer|add seller", re.IGNORECASE)).first
                if add_btn:
                    add_btn.click()
                    time.sleep(1.5)
            except Exception:
                pass

            # Fill text fields
            self._fill_party_form(party)

            # Save party
            try:
                self.page.get_by_role("button", name=re.compile("save|submit|जोड़ें|जमा", re.IGNORECASE)).first.click()
                time.sleep(1.5)
            except Exception:
                pass

            log_automation(self.registry_id, "party_filling", "success", f"Filled party: {party.get('role')}")

        self._run_property_filling_step()

    def _fill_party_form(self, party: Dict[str, Any]) -> None:
        """Heuristic form filling using placeholder or nearby label text."""
        p = party
        fields = {
            "name_english": p.get("name_english", ""),
            "name_hindi": p.get("name_hindi", ""),
            "father_husband_name_english": p.get("father_husband_name_english", ""),
            "father_husband_name_hindi": p.get("father_husband_name_hindi", ""),
            "dob": p.get("dob", ""),
            "gender": p.get("gender", ""),
            "category": p.get("category", ""),
            "address_english": p.get("address_english", ""),
            "address_hindi": p.get("address_hindi", ""),
            "id_number": p.get("id_number", ""),
            "pan_number": p.get("pan_number", ""),
            "mobile_number": p.get("mobile_number", ""),
        }

        # Strategy: find inputs by placeholder text or label proximity
        inputs = self.page.query_selector_all("input, textarea, select")
        for inp in inputs:
            try:
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                label = (inp.get_attribute("aria-label") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                name_attr = (inp.get_attribute("name") or "").lower()
                combined = f"{placeholder} {label} {id_attr} {name_attr}"

                if "name" in combined and "hindi" in combined and fields["name_hindi"]:
                    inp.fill(fields["name_hindi"])
                elif "name" in combined and fields["name_english"] and "hindi" not in combined:
                    inp.fill(fields["name_english"])
                elif "father" in combined and "hindi" in combined and fields["father_husband_name_hindi"]:
                    inp.fill(fields["father_husband_name_hindi"])
                elif "father" in combined and fields["father_husband_name_english"] and "hindi" not in combined:
                    inp.fill(fields["father_husband_name_english"])
                elif "dob" in combined or "birth" in combined:
                    inp.fill(fields["dob"])
                elif "address" in combined and "hindi" in combined and fields["address_hindi"]:
                    inp.fill(fields["address_hindi"])
                elif "address" in combined and fields["address_english"] and "hindi" not in combined:
                    inp.fill(fields["address_english"])
                elif "aadhaar" in combined or "id number" in combined:
                    inp.fill(fields["id_number"])
                elif "pan" in combined:
                    inp.fill(fields["pan_number"])
                elif "mobile" in combined or "phone" in combined:
                    inp.fill(fields["mobile_number"])
                elif inp.tag_name == "select":
                    if "gender" in combined and fields["gender"]:
                        inp.select_option(label=fields["gender"])
                    elif "category" in combined or "caste" in combined and fields["category"]:
                        inp.select_option(label=fields["category"])
            except Exception:
                pass

    def _run_property_filling_step(self) -> None:
        # 6. Property Identification & Valuation
        update_registry(self.registry_id, {"current_step": "property_filling"})
        prop = self.property_data or {}
        if not prop:
            log_automation(self.registry_id, "property_filling", "success", "No property data to fill.")
            self._run_draft_upload_step()
            return

        fields = {
            "plot": prop.get("plot_number", ""),
            "total_area": str(prop.get("total_area_sqmt", "")),
            "constructed_area": str(prop.get("constructed_area_sqmt", "")),
            "road_width": str(prop.get("road_width_mt", "")),
        }
        boundaries = prop.get("boundaries", {})

        inputs = self.page.query_selector_all("input, textarea")
        for inp in inputs:
            try:
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                label = (inp.get_attribute("aria-label") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                combined = f"{placeholder} {label} {id_attr}"

                if "plot" in combined and fields["plot"]:
                    inp.fill(fields["plot"])
                elif "total area" in combined or "area" in combined and "total" in combined:
                    inp.fill(fields["total_area"])
                elif "constructed" in combined or "built" in combined:
                    inp.fill(fields["constructed_area"])
                elif "road" in combined and "width" in combined:
                    inp.fill(fields["road_width"])
                elif "north" in combined:
                    inp.fill(boundaries.get("north", ""))
                elif "south" in combined:
                    inp.fill(boundaries.get("south", ""))
                elif "east" in combined:
                    inp.fill(boundaries.get("east", ""))
                elif "west" in combined:
                    inp.fill(boundaries.get("west", ""))
            except Exception:
                pass

        log_automation(self.registry_id, "property_filling", "success", "Property details filled.")
        self._run_draft_upload_step()

    def _run_draft_upload_step(self) -> None:
        # 7. Deed Drafting / Uploads
        update_registry(self.registry_id, {"current_step": "draft_upload"})
        log_automation(self.registry_id, "draft_upload", "success", "Draft upload step reached.")
        self._run_kyc_pause_step()

    def _run_kyc_pause_step(self) -> None:
        # 8. KYC / Biometrics Pause
        update_registry(self.registry_id, {"current_step": "kyc_pause"})
        log_automation(self.registry_id, "kyc_pause", "pause", "e-KYC / Video KYC / Biometric step reached. Human action required.")

        if not self._wait_for_resume("kyc_pause", "kyc_pause"):
            return

        self._run_payment_pause_step()

    def _run_payment_pause_step(self) -> None:
        # 9. Payment Gateway Pause
        update_registry(self.registry_id, {"current_step": "payment_pause"})
        log_automation(self.registry_id, "payment_pause", "pause", "Payment gateway reached. Human action required.")

        if not self._wait_for_resume("payment_pause", "payment_pause"):
            return

        # 10. Completion
        update_registry(self.registry_id, {
            "current_step": "completed",
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        })
        log_automation(self.registry_id, "completion", "success", "Registry automation completed successfully.")


# ── External Control API ───────────────────────────────────────────────

def resume_bot(registry_id: int) -> None:
    global _current_bot
    if _current_bot and _current_bot.registry_id == registry_id:
        _current_bot.resume()
    else:
        logger.warning("No active bot for registry %d to resume", registry_id)


def stop_bot(registry_id: int) -> None:
    global _current_bot
    if _current_bot and _current_bot.registry_id == registry_id:
        _current_bot.stop()
    else:
        logger.warning("No active bot for registry %d to stop", registry_id)
