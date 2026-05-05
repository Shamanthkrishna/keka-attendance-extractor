"""
auto_extract.py
---------------
Fully automated Keka attendance extraction using Playwright with a persistent
browser profile. No Chrome extension or manual token copying needed.

Flow:
  1. Load cached token if still valid  → skip browser entirely
  2. Otherwise launch Chrome with your saved profile (GAuth session reused)
  3. Navigate to Keka → extract access_token from localStorage
  4. Cache the token with its expiry
  5. Run the main extraction pipeline

Run this via Task Scheduler daily (see setup_scheduler.py).
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
# Chrome user-data directory to reuse your existing session.
# Change this to your actual Chrome profile path if different.
# Default Chrome profile on Windows: %LOCALAPPDATA%\Google\Chrome\User Data
# ---------------------------------------------------------------------------
CHROME_USER_DATA = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"
)
# Profile folder inside User Data (Default, Profile 1, etc.)
CHROME_PROFILE = "Default"

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
# Browser-based token extraction via Playwright
# ---------------------------------------------------------------------------

def fetch_token_via_browser(headless: bool = False) -> str | None:
    """
    Launch Chrome with the persistent user profile (so GAuth session is reused),
    navigate to Keka, and read the access_token from localStorage.

    headless=False  → shows the browser; required when GAuth login is needed.
    headless=True   → invisible; works only if the session is still alive.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        log.error(
            "Playwright is not installed. Run:  pip install playwright && playwright install chromium"
        )
        sys.exit(1)

    log.info("Launching Chrome with persistent profile: %s / %s", CHROME_USER_DATA, CHROME_PROFILE)

    with sync_playwright() as p:
        # launch_persistent_context reuses cookies, localStorage, and session storage
        # from the given Chrome profile — including your GAuth session.
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA,
            channel="chrome",               # use your installed Google Chrome
            headless=headless,
            args=["--profile-directory=" + CHROME_PROFILE],
        )
        page = context.new_page()

        try:
            log.info("Navigating to %s ...", KEKA_URL)
            page.goto(KEKA_URL, wait_until="networkidle", timeout=60_000)

            # If Keka redirects to a login page, wait for the user to authenticate.
            # The page title will no longer contain "Login" once authenticated.
            if "login" in page.url.lower() or "signin" in page.url.lower():
                if headless:
                    log.warning(
                        "Session expired and headless mode is on. Relaunching with visible browser..."
                    )
                    context.close()
                    return fetch_token_via_browser(headless=False)

                log.info(
                    "Keka login page detected. Please complete login in the browser window "
                    "(GAuth or email+OTP). Script will wait up to 3 minutes..."
                )
                # Wait until URL no longer contains login indicators
                page.wait_for_url(
                    lambda url: "login" not in url.lower() and "signin" not in url.lower(),
                    timeout=180_000,
                )
                # After redirect, wait for the app to settle
                page.wait_for_load_state("networkidle", timeout=30_000)

            # Extract token from localStorage (same as content.js does)
            token = page.evaluate(f"() => localStorage.getItem('{TOKEN_STORAGE_KEY}')")

            if not token:
                # Some Keka tenants also use sessionStorage
                token = page.evaluate(f"() => sessionStorage.getItem('{TOKEN_STORAGE_KEY}')")

            if token:
                log.info("Token extracted successfully from browser.")
            else:
                log.error(
                    "Token not found in localStorage or sessionStorage after login. "
                    "The storage key may have changed — check browser DevTools > Application > "
                    "Local Storage for the correct key and update TOKEN_STORAGE_KEY."
                )

        except PWTimeout as e:
            log.error("Timed out waiting for Keka: %s", e)
            token = None
        finally:
            context.close()

    return token or None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    log.info("=" * 60)
    log.info("Keka Attendance Auto-Extractor starting (%s)", datetime.date.today())
    log.info("=" * 60)

    # Step 1: try the cache first
    token = load_cached_token()

    # Step 2: if no valid cached token, get one from the browser
    if not token:
        log.info("No valid cached token. Opening browser to extract token...")
        token = fetch_token_via_browser(headless=True)   # tries silent first
        if not token:
            log.error("Could not obtain a token. Aborting.")
            sys.exit(1)
        save_cached_token(token)

    # Step 3: run the extraction pipeline (imported from main.py)
    # We import here to avoid triggering the Tkinter GUI at module level
    log.info("Starting attendance extraction pipeline...")
    try:
        # Suppress GUI-related code in main.py by monkey-patching tkinter globals
        import main as keka_main
        # Provide stub log_box so log_message() doesn't crash (no GUI here)
        import tkinter as tk
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
