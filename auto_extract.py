"""
auto_extract.py
---------------
Fully automated Keka attendance extraction.

Flow:
  1. Load cached token if still valid  → done, no browser at all
  2. Otherwise connect to YOUR already-running Chrome via CDP
     (Chrome must be started with --remote-debugging-port=9222, see start_chrome.bat)
  3. Find any open Keka tab → extract access_token from localStorage
  4. Cache the token with its expiry
  5. Run the extraction pipeline

No new browser window, no login required — uses the Keka tab you already have open.
Run via Task Scheduler daily (see setup_scheduler.py).
"""

import os
import sys
import json
import base64
import datetime
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "Logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"attendance_log_{datetime.date.today()}.txt"
TOKEN_CACHE_FILE = BASE_DIR / ".token_cache.json"   # hidden file, gitignore this

# ---------------------------------------------------------------------------
# Logging (reuse same file as main.py would use today)
# ---------------------------------------------------------------------------
handler = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[handler, logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keka config  ← adjust if your org subdomain changes
# ---------------------------------------------------------------------------
KEKA_URL = "https://hrmstismo.keka.com"
# localStorage key Keka uses for the Bearer token
TOKEN_STORAGE_KEY = "access_token"

# ---------------------------------------------------------------------------
# CDP endpoint — Chrome must be launched with --remote-debugging-port=9222
# (start_chrome.bat does this automatically)
# ---------------------------------------------------------------------------
CDP_URL = "http://localhost:9222"

# ---------------------------------------------------------------------------
# Token cache helpers
# ---------------------------------------------------------------------------

def _decode_jwt_expiry(token: str) -> datetime.datetime | None:
    """Decode the exp claim from a JWT without verifying the signature."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + "=="          # add padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp:
            return datetime.datetime.utcfromtimestamp(exp)
    except Exception:
        pass
    return None


def load_cached_token() -> str | None:
    """Return a cached token if it is still valid (with a 5-minute buffer)."""
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
        token = data.get("token", "")
        expires_at_str = data.get("expires_at", "")
        if not token or not expires_at_str:
            return None
        expires_at = datetime.datetime.fromisoformat(expires_at_str)
        if datetime.datetime.utcnow() < expires_at - datetime.timedelta(minutes=5):
            log.info("Using cached token (valid until %s UTC)", expires_at.strftime("%Y-%m-%d %H:%M"))
            return token
        log.info("Cached token has expired.")
    except Exception as e:
        log.warning("Could not read token cache: %s", e)
    return None


def save_cached_token(token: str) -> None:
    """Persist token with its decoded expiry."""
    expires_at = _decode_jwt_expiry(token)
    if not expires_at:
        # Fallback: assume token lasts 8 hours
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        log.warning("Could not decode token expiry; assuming 8-hour lifetime.")
    cache = {"token": token, "expires_at": expires_at.isoformat()}
    TOKEN_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    log.info("Token cached (expires %s UTC).", expires_at.strftime("%Y-%m-%d %H:%M"))


# ---------------------------------------------------------------------------
# CDP-based token extraction from running Chrome
# ---------------------------------------------------------------------------

def _read_token_from_page(page) -> str | None:
    """Try localStorage then sessionStorage on a Playwright page object."""
    try:
        token = page.evaluate(f"() => localStorage.getItem('{TOKEN_STORAGE_KEY}')")
        if not token:
            token = page.evaluate(f"() => sessionStorage.getItem('{TOKEN_STORAGE_KEY}')")
        return token or None
    except Exception:
        return None


def fetch_token_via_cdp() -> str | None:
    """
    Connect to the already-running Chrome instance via CDP and extract the
    Bearer token from any open Keka tab.

    Requires Chrome to be running with --remote-debugging-port=9222.
    Use start_chrome.bat (placed in Windows Startup) to ensure this.
    """
    import requests as req

    # 1. Check CDP is reachable
    try:
        resp = req.get(f"{CDP_URL}/json", timeout=2)
        tabs = resp.json()
    except Exception as e:
        log.error(
            "Cannot reach Chrome on %s. "
            "Make sure Chrome was started via start_chrome.bat (adds --remote-debugging-port=9222). "
            "Close Chrome, run start_chrome.bat, open Keka, then retry. Detail: %s",
            CDP_URL, e,
        )
        return None

    # 2. Check there is at least one Keka page tab
    keka_tabs = [
        t for t in tabs
        if KEKA_URL in t.get("url", "") and t.get("type") == "page"
    ]
    if not keka_tabs:
        log.error(
            "Chrome is running with CDP but no Keka tab was found. "
            "Open %s in Chrome and make sure you are logged in, then retry.",
            KEKA_URL,
        )
        return None

    log.info("Found %d Keka tab(s) in Chrome. Extracting token...", len(keka_tabs))

    # 3. Connect via Playwright CDP and read the token
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        token = None
        try:
            for context in browser.contexts:
                for page in context.pages:
                    if KEKA_URL in page.url:
                        token = _read_token_from_page(page)
                        if token:
                            log.info("Token extracted from tab: %s", page.url[:80])
                            break
                if token:
                    break
        finally:
            browser.close()

    if not token:
        log.error(
            "Keka tab found but token was not in localStorage/sessionStorage. "
            "Check DevTools > Application > Local Storage for the correct key "
            "and update TOKEN_STORAGE_KEY in auto_extract.py."
        )
    return token or None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    log.info("=" * 60)
    log.info("Keka Attendance Auto-Extractor starting (%s)", datetime.date.today())
    log.info("=" * 60)

    # Step 1: use cached token if still valid
    token = load_cached_token()

    # Step 2: get token from the running Chrome (no new window, no login)
    if not token:
        log.info("No valid cached token. Connecting to Chrome to extract token...")
        token = fetch_token_via_cdp()
        if not token:
            sys.exit(1)
        save_cached_token(token)

    # Step 3: run the extraction pipeline
    log.info("Starting attendance extraction pipeline...")
    try:
        import main as keka_main
        keka_main.log_box = type("_Stub", (), {
            "configure": lambda *a, **k: None,
            "insert": lambda *a, **k: None,
            "see": lambda *a, **k: None,
            "update_idletasks": lambda *a, **k: None,
        })()
        keka_main.main(token)
        log.info("Extraction pipeline completed successfully.")
    except Exception as e:
        log.error("Extraction pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()



