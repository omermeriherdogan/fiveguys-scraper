import asyncio
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from contextlib import suppress
from dataclasses import asdict, dataclass, fields
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import StorageCommands
from selectolax.parser import HTMLParser


PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "logs"
SAVE_TERMINAL_LOG = (
    os.getenv("SAVE_TERMINAL_LOG", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
TERMINAL_LOG_PATH = os.getenv("TERMINAL_LOG_PATH", "").strip()
LOCAL_APP_DATA_DIR = Path(
    os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
)
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", r"C:\fiveguys-cdp-profile")
CHROME_WORKER_PROFILE_ROOT = Path(
    os.getenv(
        "CHROME_WORKER_PROFILE_ROOT",
        str(LOCAL_APP_DATA_DIR / "fiveguys-scraper" / "chrome-worker-profiles"),
    )
)
GOOGLE_MAPS_PROFILE_DIR = PROJECT_DIR / ".google-maps-review-profile"
GOOGLE_MAPS_PROFILE_RUN_ROOT = PROJECT_DIR / ".google-maps-review-profiles"
GOOGLE_MAPS_LANGUAGE = "en"
GOOGLE_MAPS_REGION = "US"
CHROME_START_URL = "https://order.fiveguys.com/location"
ORDER_ORIGIN = "https://order.fiveguys.com"
ORDER_CLIENT_STORAGE_TYPES = os.getenv(
    "ORDER_CLIENT_STORAGE_TYPES",
    "local_storage,indexeddb,cache_storage,service_workers,shared_storage",
).strip()
FIVE_GUYS_DIRECTORY_ROOT_URL = (
    os.getenv(
        "FIVE_GUYS_DIRECTORY_ROOT_URL",
        "https://restaurants.fiveguys.com/index.html",
    ).strip()
    or "https://restaurants.fiveguys.com/index.html"
)
FIVE_GUYS_MAX_LOCATIONS = int(os.getenv("FIVE_GUYS_MAX_LOCATIONS", "0") or 0)
FIVE_GUYS_LOCATION_URLS = os.getenv("FIVE_GUYS_LOCATION_URLS", "").strip()
FIVE_GUYS_DIRECTORY_DISCOVERY_ATTEMPTS = int(
    os.getenv("FIVE_GUYS_DIRECTORY_DISCOVERY_ATTEMPTS", "2") or 2
)
FIVE_GUYS_DIRECTORY_READY_SELECTOR = (
    "section.Directory, article.Teaser--directory, span.LocationName-geo"
)
CHROME_TURNSTILE_WAIT_SECONDS = int(
    os.getenv("CHROME_TURNSTILE_WAIT_SECONDS", "15") or 15
)
TURNSTILE_MANUAL_CLICK_MAX_ATTEMPTS = int(
    os.getenv("TURNSTILE_MANUAL_CLICK_MAX_ATTEMPTS", "4") or 4
)
TURNSTILE_MANUAL_CLICK_RETRY_SECONDS = float(
    os.getenv("TURNSTILE_MANUAL_CLICK_RETRY_SECONDS", "4") or 4
)
TURNSTILE_MANUAL_CLICK_POST_WAIT_SECONDS = float(
    os.getenv("TURNSTILE_MANUAL_CLICK_POST_WAIT_SECONDS", "3") or 3
)
CHROME_SESSION_READY_WAIT_SECONDS = int(
    os.getenv("CHROME_SESSION_READY_WAIT_SECONDS", "60") or 60
)
BOOTSTRAP_SESSION_READY_WAIT_SECONDS = int(
    os.getenv("BOOTSTRAP_SESSION_READY_WAIT_SECONDS", "45") or 45
)
BOOTSTRAP_HELPER_WAIT_SECONDS = int(
    os.getenv("BOOTSTRAP_HELPER_WAIT_SECONDS", "30") or 30
)
USE_CLOUDFLARE_BYPASS_WRAPPER = True 
LOCATION_NAVIGATION_TIMEOUT_SECONDS = 60
USE_HTTP_FOR_RESTAURANT_PAGES = (
    os.getenv("USE_HTTP_FOR_RESTAURANT_PAGES", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
HTTP_LOCATION_ATTEMPTS = int(os.getenv("HTTP_LOCATION_ATTEMPTS", "2") or 2)
HTTP_LOCATION_TIMEOUT_SECONDS = int(
    os.getenv("HTTP_LOCATION_TIMEOUT_SECONDS", "20") or 20
)
GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS = 120
GOOGLE_MAPS_READY_WAIT_SECONDS = 12
GOOGLE_MAPS_REVIEW_PANEL_WAIT_SECONDS = 12
GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS = 1.5
SCRAPER_MODE = os.getenv("SCRAPER_MODE", "full").strip().lower()
RUN_GOOGLE_REVIEWS_AFTER_CORE = (
    os.getenv("RUN_GOOGLE_REVIEWS_AFTER_CORE", "0").strip().lower()
    in ("1", "true", "yes", "on")
)
BEFORE_GOOGLE_REVIEWS_COMMAND = os.getenv(
    "BEFORE_GOOGLE_REVIEWS_COMMAND",
    "",
).strip()
BEFORE_GOOGLE_REVIEWS_COMMAND_TIMEOUT_SECONDS = int(
    os.getenv("BEFORE_GOOGLE_REVIEWS_COMMAND_TIMEOUT_SECONDS", "120") or 120
)
BEFORE_GOOGLE_REVIEWS_WAIT_SECONDS = float(
    os.getenv("BEFORE_GOOGLE_REVIEWS_WAIT_SECONDS", "20") or 20
)
GOOGLE_MAPS_REVIEW_LIMIT = int(os.getenv("GOOGLE_MAPS_REVIEW_LIMIT", "100"))
GOOGLE_MAPS_REQUIRE_REVIEW_TEXT = (
    os.getenv("GOOGLE_MAPS_REQUIRE_REVIEW_TEXT", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
GOOGLE_MAPS_DEBUG_STORE_NAME = os.getenv("GOOGLE_MAPS_DEBUG_STORE_NAME", "").strip()
GOOGLE_MAPS_DEBUG_STORE_LIMIT = int(os.getenv("GOOGLE_MAPS_DEBUG_STORE_LIMIT", "0") or 0)
GOOGLE_MAPS_REVIEW_MAX_SCROLLS = 160
GOOGLE_MAPS_REVIEW_NO_PROGRESS_SCROLLS = 8
ORDER_NAVIGATION_TIMEOUT_SECONDS = int(
    os.getenv("ORDER_NAVIGATION_TIMEOUT_SECONDS", "75") or 75
)
ORDER_BLANK_PAGE_RELOAD_SECONDS = 12
ORDER_BLANK_PAGE_MAX_RELOADS = 2
ORDER_CLOUDFLARE_HELPER_URL = os.getenv("ORDER_CLOUDFLARE_HELPER_URL", "").strip()
ORDER_CLOUDFLARE_HELPER_ENABLED = (
    os.getenv("ORDER_CLOUDFLARE_HELPER_ENABLED", "0").strip().lower()
    in ("1", "true", "yes", "on")
) and bool(ORDER_CLOUDFLARE_HELPER_URL)
ORDER_CLOUDFLARE_HELPER_WAIT_SECONDS = int(
    os.getenv("ORDER_CLOUDFLARE_HELPER_WAIT_SECONDS", "45") or 45
)
ORDER_MENU_WAIT_SECONDS = int(os.getenv("ORDER_MENU_WAIT_SECONDS", "90") or 90)
ORDER_MENU_HTML_FALLBACK_WAIT_SECONDS = 20
ORDER_MENU_HTML_FALLBACK_POLL_SECONDS = 1
ORDER_PAGE_ACTIVATION_RETRIES = 3
ORDER_PAGE_ACTIVATION_RETRY_SECONDS = 1
ORDER_PAGE_ACTIVATION_POST_CLICK_SECONDS = 0.5
ORDER_PAGE_FRONT_FOCUS_SECONDS = 0.25
ORDER_PAGE_STALL_REACTIVATION_POLLS = 3
ORDER_PAGE_MAX_REACTIVATIONS = 2
MANAGED_CHALLENGE_CONFIRM_POLLS = 2
SCRAPE_CONCURRENCY = max(1, int(os.getenv("SCRAPE_CONCURRENCY", "3") or 3))
WORKER_BOOTSTRAP_CONCURRENCY = max(
    1,
    int(os.getenv("WORKER_BOOTSTRAP_CONCURRENCY", "1") or 1),
)
WORKER_BROWSER_START_ATTEMPTS = max(
    1,
    int(os.getenv("WORKER_BROWSER_START_ATTEMPTS", "3") or 3),
)
WORKER_BROWSER_START_RETRY_SECONDS = float(
    os.getenv("WORKER_BROWSER_START_RETRY_SECONDS", "5") or 5
)
BOOTSTRAP_SESSION_ATTEMPTS = max(
    1,
    int(os.getenv("BOOTSTRAP_SESSION_ATTEMPTS", "3") or 3),
)
BOOTSTRAP_SESSION_RETRY_SECONDS = float(
    os.getenv("BOOTSTRAP_SESSION_RETRY_SECONDS", "5") or 5
)
WORKER_BROWSER_RECYCLE_STORES = int(
    os.getenv("WORKER_BROWSER_RECYCLE_STORES", "25") or 25
)
WORKER_BROWSER_RECYCLE_PAUSE_SECONDS = float(
    os.getenv("WORKER_BROWSER_RECYCLE_PAUSE_SECONDS", "3") or 3
)
GOOGLE_MAPS_SCRAPE_CONCURRENCY = max(
    1,
    int(os.getenv("GOOGLE_MAPS_SCRAPE_CONCURRENCY", "2") or 2),
)
SCRAPE_LOCATION_ATTEMPTS = 2
SCRAPE_LOCATION_TIMEOUT_SECONDS = int(
    os.getenv("SCRAPE_LOCATION_TIMEOUT_SECONDS", "360") or 360
)
FAILED_STORE_RETRY_CONCURRENCY = max(
    1,
    int(os.getenv("FAILED_STORE_RETRY_CONCURRENCY", "1") or 1),
)
FAILED_STORE_RETRY_STAGES = {
    stage.strip().lower()
    for stage in os.getenv(
        "FAILED_STORE_RETRY_STAGES",
        "store_unrecovered,store_timeout,store_scrape,worker_start",
    ).split(",")
    if stage.strip()
}
SCRAPE_CLASSIC_COMBO = (
    os.getenv("SCRAPE_CLASSIC_COMBO", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
SCRAPE_MILKSHAKE_MIXINS = (
    os.getenv("SCRAPE_MILKSHAKE_MIXINS", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
CLASSIC_COMBO_PAGE_FALLBACK = (
    os.getenv("CLASSIC_COMBO_PAGE_FALLBACK", "0").strip().lower()
    in ("1", "true", "yes", "on")
)
CLASSIC_COMBO_FALLBACK_SLUG = (
    os.getenv("CLASSIC_COMBO_FALLBACK_SLUG", "classic-combo").strip()
    or "classic-combo"
)
CLASSIC_COMBO_FALLBACK_CHAINPRODUCTID = (
    os.getenv("CLASSIC_COMBO_FALLBACK_CHAINPRODUCTID", "1092687").strip()
    or "1092687"
)
CLASSIC_COMBO_RENDER_ATTEMPTS = max(
    1,
    int(os.getenv("CLASSIC_COMBO_RENDER_ATTEMPTS", "1") or 1),
)
CLASSIC_COMBO_PRESENT_RENDER_ATTEMPTS = max(
    1,
    int(os.getenv("CLASSIC_COMBO_PRESENT_RENDER_ATTEMPTS", "3") or 3),
)
CLASSIC_COMBO_TIMEOUT_SECONDS = int(
    os.getenv("CLASSIC_COMBO_TIMEOUT_SECONDS", "15") or 15
)
CLASSIC_COMBO_FALLBACK_TIMEOUT_SECONDS = int(
    os.getenv(
        "CLASSIC_COMBO_FALLBACK_TIMEOUT_SECONDS",
        str(CLASSIC_COMBO_TIMEOUT_SECONDS),
    )
    or CLASSIC_COMBO_TIMEOUT_SECONDS
)
CLASSIC_COMBO_PRESENT_TIMEOUT_SECONDS = int(
    os.getenv("CLASSIC_COMBO_PRESENT_TIMEOUT_SECONDS", "90") or 90
)
CLASSIC_COMBO_DETAIL_CONCURRENCY = max(
    1,
    int(os.getenv("CLASSIC_COMBO_DETAIL_CONCURRENCY", "1") or 1),
)
CLASSIC_COMBO_FRESH_TAB_FIRST = (
    os.getenv("CLASSIC_COMBO_FRESH_TAB_FIRST", "1").strip().lower()
    not in ("0", "false", "no", "off")
)
CLASSIC_COMBO_MIN_EXPECTED_ROWS = 200
MILKSHAKE_RENDER_ATTEMPTS = 3
MILKSHAKE_MIN_EXPECTED_ROWS = 8
MILKSHAKE_DETAIL_WAIT_SECONDS = 30
MILKSHAKE_DIRECT_TIMEOUT_SECONDS = int(
    os.getenv("MILKSHAKE_DIRECT_TIMEOUT_SECONDS", "20") or 20
)
MILKSHAKE_PAGE_FALLBACK_TIMEOUT_SECONDS = int(
    os.getenv("MILKSHAKE_PAGE_FALLBACK_TIMEOUT_SECONDS", "60") or 60
)
MILKSHAKE_NOT_FOUND_WAIT_SECONDS = float(
    os.getenv("MILKSHAKE_NOT_FOUND_WAIT_SECONDS", "4") or 4
)
CHROME_CLOUDFLARE_WAIT_SECONDS = CHROME_SESSION_READY_WAIT_SECONDS
CHROME_CANDIDATE_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
LOCATIONS_CSV_PATH = PROJECT_DIR / "locations.csv"
LOCATIONS_JSON_PATH = PROJECT_DIR / "locations.json"
MENU_ITEMS_CSV_PATH = PROJECT_DIR / "menu_items.csv"
MENU_ITEMS_JSON_PATH = PROJECT_DIR / "menu_items.json"
SCRAPE_FAILURES_CSV_PATH = PROJECT_DIR / "scrape_failures.csv"
CLASSIC_COMBO_CSV_PATH = PROJECT_DIR / "classic_combo_items.csv"
CLASSIC_COMBO_JSON_PATH = PROJECT_DIR / "classic_combo_items.json"
MILKSHAKE_MIXIN_CSV_PATH = PROJECT_DIR / "milkshake_mixin_items.csv"
MILKSHAKE_MIXIN_JSON_PATH = PROJECT_DIR / "milkshake_mixin_items.json"
GOOGLE_REVIEWS_CSV_PATH = PROJECT_DIR / "google_reviews.csv"
GOOGLE_REVIEWS_JSON_PATH = PROJECT_DIR / "google_reviews.json"
ORDER_MENU_QUERY = "nomnom=add-restaurant-to-menu"
KNOWN_RESTAURANT_IDS_BY_ORDER_URL = {}
KNOWN_RESTAURANT_IDS_LOADED = False
CLASSIC_COMBO_CSV_APPEND_LOCK = threading.Lock()
LOCATION_CSV_APPEND_LOCK = threading.Lock()
MENU_CSV_APPEND_LOCK = threading.Lock()
MILKSHAKE_MIXIN_CSV_APPEND_LOCK = threading.Lock()
GOOGLE_REVIEW_CSV_APPEND_LOCK = threading.Lock()
SCRAPE_FAILURE_CSV_APPEND_LOCK = threading.Lock()
LOCATION_CSV_WRITTEN_KEYS = set()
MENU_CSV_WRITTEN_KEYS = set()
CLASSIC_COMBO_DETAIL_SEMAPHORE = None
TERMINAL_LOG_FILE = None
PROFILE_ROOT_ITEMS_TO_CLONE = (
    "Default",
    "Local State",
    "First Run",
    "Last Version",
    "Variations",
)
COOKIE_PARAM_FIELDS = (
    "name",
    "value",
    "domain",
    "path",
    "secure",
    "httpOnly",
    "sameSite",
    "expires",
    "priority",
)


def find_chrome_executable():
    for path in CHROME_CANDIDATE_PATHS:
        if Path(path).exists():
            return path

    for command in ("chrome.exe", "chrome"):
        chrome_path = shutil.which(command)
        if chrome_path:
            return chrome_path

    raise FileNotFoundError(
        "Could not find Google Chrome. Install Chrome or update CHROME_CANDIDATE_PATHS."
    )


def prepare_profile_dir(profile_dir):
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir



def build_chrome_options(profile_dir=None):
    chrome_path = find_chrome_executable()
    profile_dir = Path(profile_dir or CHROME_USER_DATA_DIR)
    profile_dir.mkdir(parents=True, exist_ok=True)
    current_time = int(time.time())

    options = ChromiumOptions()
    options.binary_location = chrome_path
    options.start_timeout = 30
    options.headless = False
    options.block_notifications = True
    options.block_popups = True
    options.set_accept_languages("en-US,en")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=Translate")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.browser_preferences = {
        "profile": {
            "last_engagement_time": str(current_time - (3 * 60 * 60)),
            "exited_cleanly": True,
            "exit_type": "Normal",
        },
        "intl": {"accept_languages": "en-US,en"},
        "safebrowsing": {"enabled": True},
        "translate": {"enabled": False},
    }
    return options


def build_bootstrap_chrome_options():
    chrome_path = find_chrome_executable()
    Path(CHROME_USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
    current_time = int(time.time())

    options = ChromiumOptions()
    options.binary_location = chrome_path
    options.start_timeout = 30
    options.headless = False
    options.block_notifications = True
    options.block_popups = True
    options.set_accept_languages("en-US,en")
    options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=Translate")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.browser_preferences = {
        "profile": {
            "last_engagement_time": str(current_time - (3 * 60 * 60)),
            "exited_cleanly": True,
            "exit_type": "Normal",
        },
        "intl": {"accept_languages": "en-US,en"},
        "safebrowsing": {"enabled": True},
        "translate": {"enabled": False},
    }
    return options


def extract_runtime_value(response):
    if not isinstance(response, dict):
        return response
    return response.get("result", {}).get("result", {}).get("value")


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams
        self.encoding = getattr(streams[0], "encoding", "utf-8") if streams else "utf-8"
        self.errors = getattr(streams[0], "errors", "replace") if streams else "replace"

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return bool(self.streams and hasattr(self.streams[0], "isatty") and self.streams[0].isatty())


def setup_terminal_log():
    global TERMINAL_LOG_FILE
    if not SAVE_TERMINAL_LOG:
        return None

    log_path = Path(TERMINAL_LOG_PATH) if TERMINAL_LOG_PATH else None
    if log_path is None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / f"scraper-{time.strftime('%Y%m%d-%H%M%S')}.log"
    else:
        if not log_path.is_absolute():
            log_path = PROJECT_DIR / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

    TERMINAL_LOG_FILE = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = TeeStream(sys.stdout, TERMINAL_LOG_FILE)
    sys.stderr = TeeStream(sys.stderr, TERMINAL_LOG_FILE)
    print(f"Saving terminal output to: {log_path}")
    return log_path


def close_terminal_log():
    global TERMINAL_LOG_FILE
    if TERMINAL_LOG_FILE is None:
        return

    with suppress(Exception):
        TERMINAL_LOG_FILE.flush()
    with suppress(Exception):
        TERMINAL_LOG_FILE.close()
    TERMINAL_LOG_FILE = None


async def run_script_value(tab, script):
    response = await tab.execute_script(script, return_by_value=True)
    return extract_runtime_value(response)


async def reset_order_client_state(tab, label):
    """Clear per-tab order app state while preserving cookies/session auth."""
    if ORDER_CLIENT_STORAGE_TYPES:
        try:
            await tab._connection_handler.execute_command(
                StorageCommands.clear_data_for_origin(
                    ORDER_ORIGIN,
                    ORDER_CLIENT_STORAGE_TYPES,
                ),
                timeout=10,
            )
        except Exception as e:
            print(f"Could not reset order origin storage for {label}: {e}")

    script = """
    (() => {
        const result = {href: location.href, localStorage: false, sessionStorage: false};
        if (!location.href.startsWith("https://order.fiveguys.com/")) {
            return result;
        }
        try {
            window.localStorage.clear();
            result.localStorage = true;
        } catch (e) {}
        try {
            window.sessionStorage.clear();
            result.sessionStorage = true;
        } catch (e) {}
        return result;
    })();
    """
    try:
        await asyncio.wait_for(run_script_value(tab, script), timeout=5)
    except Exception as e:
        print(f"Could not reset order client state for {label}: {e}")


async def close_browser_safely(browser):
    browser._backup_preferences_dir = ""

    with suppress(Exception):
        if await browser._is_browser_running(timeout=2):
            await browser.stop()
            return

    with suppress(Exception):
        await browser._connection_handler.close()


def worker_profile_dir(run_namespace, worker_id, cycle_index=0):
    return (
        CHROME_WORKER_PROFILE_ROOT
        / run_namespace
        / f"worker-{worker_id:02d}-cycle-{cycle_index:03d}"
    )


def google_maps_review_profile_dir(run_namespace):
    return GOOGLE_MAPS_PROFILE_RUN_ROOT / run_namespace / "browser"


def ignore_profile_copy(_directory, names):
    ignored = set()
    ignored_names = {
        "bootstrap",
        "listing",
        "singletoncookie",
        "singletonlock",
        "singletonsocket",
        "lockfile",
        "devtoolsactiveport",
        "chrome_debug.log",
        "preferences.backup",
    }
    ignored_substrings = (
        "cache",
        "code cache",
        "dawngraphitecache",
        "dawnwebgpucache",
        "gpucache",
        "shadercache",
        "crashpad",
    )

    for name in names:
        normalized_name = name.lower()
        if (
            normalized_name in ignored_names
            or normalized_name.endswith(".lock")
            or normalized_name.endswith("-journal")
            or any(fragment in normalized_name for fragment in ignored_substrings)
        ):
            ignored.add(name)

    return ignored


def safe_copy2(src, dst):
    try:
        return shutil.copy2(src, dst)
    except (PermissionError, FileNotFoundError):
        return dst


def clone_base_profile_to_worker(base_profile_dir, target_profile_dir):
    base_profile_dir = Path(base_profile_dir)
    target_profile_dir = Path(target_profile_dir)

    if target_profile_dir.exists():
        shutil.rmtree(target_profile_dir, ignore_errors=True)

    prepare_profile_dir(target_profile_dir)

    for item_name in PROFILE_ROOT_ITEMS_TO_CLONE:
        source_path = base_profile_dir / item_name
        target_path = target_profile_dir / item_name

        if not source_path.exists():
            continue

        if source_path.is_dir():
            shutil.copytree(
                source_path,
                target_path,
                ignore=ignore_profile_copy,
                copy_function=safe_copy2,
                dirs_exist_ok=True,
            )
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            safe_copy2(source_path, target_path)

    prepare_profile_dir(target_profile_dir)


def cookie_to_cookie_param(cookie):
    if not isinstance(cookie, dict):
        return None

    name = cookie.get("name")
    value = cookie.get("value")
    domain = cookie.get("domain")
    if not name or value is None or not domain:
        return None

    cookie_param = {}
    for field_name in COOKIE_PARAM_FIELDS:
        field_value = cookie.get(field_name)
        if field_value in (None, ""):
            continue
        if field_name == "expires" and field_value < 0:
            continue
        cookie_param[field_name] = field_value

    cookie_param.setdefault("path", "/")
    cookie_param.setdefault("secure", False)
    cookie_param.setdefault("httpOnly", False)
    return cookie_param


def normalize_cookie_params(cookies):
    normalized_cookies = []
    seen = set()

    for cookie in cookies or []:
        cookie_param = cookie_to_cookie_param(cookie)
        if not cookie_param:
            continue

        cookie_key = (
            cookie_param.get("name"),
            cookie_param.get("domain"),
            cookie_param.get("path"),
        )
        if cookie_key in seen:
            continue

        seen.add(cookie_key)
        normalized_cookies.append(cookie_param)

    return normalized_cookies


def shorten_debug_text(value, limit=160):
    if value is None:
        return None
    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        return value[: limit - 3] + "..."
    return value or None


class ManagedCloudflareChallengeError(RuntimeError):
    """Raised when Cloudflare escalates into a managed challenge we cannot auto-solve."""


def format_cloudflare_challenge_details(details):
    parts = [
        f"url={details.get('current_url')!r}",
        f"title={details.get('title')!r}",
        f"cf_type={details.get('challenge_type')!r}",
        f"turnstile_api={details.get('turnstile_api_available')!r}",
        f"token_len={details.get('turnstile_response_length')!r}",
    ]

    body_excerpt = details.get("body_text_excerpt")
    if body_excerpt:
        parts.append(f"body={body_excerpt!r}")

    return ", ".join(parts)



async def collect_session_cookies(tab):
    """Return normalized CDP cookie params for all cookies visible to the tab."""
    try:
        cookies = await tab.get_cookies()
        normalized = normalize_cookie_params(cookies)
        print(f"Collected {len(normalized)} session cookies from initial browser.")
        return normalized
    except Exception as e:
        print(f"Could not collect session cookies: {e}")
        return []


async def inject_session_cookies(tab, cookies):
    """Inject previously collected cookies into a worker tab via CDP."""
    if not cookies:
        return

    try:
        await tab.set_cookies(cookies)
        print(f"Injected {len(cookies)} session cookies into worker tab.")
    except Exception as e:
        print(f"Could not inject session cookies into worker tab: {e}")


async def get_cloudflare_challenge_details(tab):
    try:
        current_url = await tab.current_url
    except Exception:
        current_url = None

    try:
        title = await tab.title
    except Exception:
        title = None

    try:
        body_text = await run_script_value(
            tab,
            "return document.body ? document.body.innerText : '';",
        )
    except Exception:
        body_text = None

    try:
        dom_state = await run_script_value(
            tab,
            """
            (() => {
                const turnstileResponse = document.querySelector("input[name='cf-turnstile-response']");
                const cfOpt = window._cf_chl_opt || null;
                return {
                    challenge_type: cfOpt ? (cfOpt.cType || null) : null,
                    turnstile_api_available: typeof window.turnstile !== "undefined",
                    turnstile_response_present: !!turnstileResponse,
                    turnstile_response_length: turnstileResponse && turnstileResponse.value
                        ? turnstileResponse.value.length
                        : 0,
                };
            })();
            """,
        )
    except Exception:
        dom_state = {}

    current_url_lower = (current_url or "").lower()
    title_lower = (title or "").lower()
    challenge_type = (dom_state or {}).get("challenge_type")
    managed_challenge = bool(
        challenge_type == "managed"
        or "__cf_chl_rt_tk=" in current_url_lower
        or title_lower.startswith("security check")
    )

    return {
        "current_url": current_url,
        "title": title,
        "body_text_excerpt": shorten_debug_text(body_text),
        "challenge_type": challenge_type,
        "turnstile_api_available": (dom_state or {}).get("turnstile_api_available"),
        "turnstile_response_present": (dom_state or {}).get("turnstile_response_present"),
        "turnstile_response_length": (dom_state or {}).get("turnstile_response_length"),
        "managed_challenge": managed_challenge,
    }


async def page_has_cloudflare_challenge_pydoll(tab):
    challenge_markers = (
        "verify you are human",
        "ger\u00e7ek ki\u015fi",
        "ray id",
        "just a moment",
        "bir dakika",
    )

    try:
        current_url = (await tab.current_url).lower()
    except Exception:
        current_url = ""

    if "security_challenge" in current_url:
        return True

    try:
        title = (await tab.title).lower()
    except Exception:
        title = ""

    try:
        body_text = await run_script_value(
            tab,
            "return document.body ? document.body.innerText : '';",
        )
        body_text = (body_text or "").lower()
    except Exception:
        body_text = ""

    page_text = f"{title}\n{body_text}"
    return any(marker in page_text for marker in challenge_markers)


async def page_is_five_guys_not_found(tab):
    try:
        title = (await tab.title).lower()
    except Exception:
        title = ""

    try:
        body_text = await run_script_value(
            tab,
            "return document.body ? document.body.innerText : '';",
        )
        body_text = (body_text or "").lower()
    except Exception:
        body_text = ""

    page_text = f"{title}\n{body_text}"
    return "page not found" in page_text and (
        "five guys" in page_text
        or "back to homepage" in page_text
        or "not sure what" in page_text
    )


async def wait_for_five_guys_not_found(tab, wait_seconds):
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if await page_is_five_guys_not_found(tab):
            return True
        await asyncio.sleep(0.5)
    return await page_is_five_guys_not_found(tab)


async def page_looks_blank_pydoll(tab):
    try:
        body_text = await run_script_value(
            tab,
            "return document.body ? document.body.innerText : '';",
        )
    except Exception:
        return False

    if clean_text(body_text):
        return False

    try:
        ready_state = await run_script_value(tab, "return document.readyState;")
    except Exception:
        return False

    return ready_state in ("interactive", "complete")


async def find_cloudflare_turnstile_click_target(tab):
    click_target_script = """
    (() => {
        const isVisible = (node) => {
            if (!node) {
                return false;
            }

            const rect = node.getBoundingClientRect();
            if (rect.width < 20 || rect.height < 20) {
                return false;
            }

            const style = window.getComputedStyle(node);
            return (
                style.display !== "none"
                && style.visibility !== "hidden"
                && style.opacity !== "0"
                && style.pointerEvents !== "none"
            );
        };

        const checkboxPointFromRect = (rect, source, detail) => {
            const xOffset = Math.min(Math.max(rect.width * 0.075, 18), 32);
            return {
                x: rect.left + xOffset,
                y: rect.top + (rect.height * 0.5),
                width: rect.width,
                height: rect.height,
                source,
                detail,
            };
        };

        const queryAllDeep = (selector) => {
            const found = [];
            const seen = new Set();
            const visit = (root) => {
                if (!root || typeof root.querySelectorAll !== "function") {
                    return;
                }

                for (const node of root.querySelectorAll(selector)) {
                    if (!seen.has(node)) {
                        seen.add(node);
                        found.push(node);
                    }
                }

                for (const node of root.querySelectorAll("*")) {
                    if (node.shadowRoot) {
                        visit(node.shadowRoot);
                    }
                }
            };

            visit(document);
            return found;
        };

        const frames = queryAllDeep("iframe")
            .filter((iframe) => {
                const src = (iframe.getAttribute("src") || "").toLowerCase();
                const title = (iframe.getAttribute("title") || "").toLowerCase();
                const name = (iframe.getAttribute("name") || "").toLowerCase();
                return (
                    src.includes("challenges.cloudflare.com")
                    || src.includes("turnstile")
                    || title.includes("cloudflare")
                    || title.includes("turnstile")
                    || name.includes("cf-chl-widget")
                );
            })
            .map((iframe) => ({ iframe, rect: iframe.getBoundingClientRect() }))
            .filter(({ iframe, rect }) => (
                isVisible(iframe)
                && rect.right > 0
                && rect.bottom > 0
                && rect.left < window.innerWidth
                && rect.top < window.innerHeight
            ));

        if (frames.length) {
            frames.sort((a, b) => (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height));
            const { iframe, rect } = frames[0];
            return checkboxPointFromRect(
                rect,
                "iframe",
                iframe.getAttribute("title") || iframe.getAttribute("src") || "cloudflare"
            );
        }

        const widgetContainers = queryAllDeep("div, section, form")
            .map((node) => ({ node, rect: node.getBoundingClientRect() }))
            .filter(({ node, rect }) => {
                if (!isVisible(node)) {
                    return false;
                }

                const text = (node.innerText || node.textContent || "").toLowerCase();
                const classes = String(node.className || "").toLowerCase();
                const id = String(node.id || "").toLowerCase();
                const looksLikeTurnstile = (
                    text.includes("verify you are human")
                    || text.includes("cloudflare")
                    || classes.includes("turnstile")
                    || classes.includes("cf-")
                    || id.includes("turnstile")
                    || id.includes("cf-")
                );
                return looksLikeTurnstile && rect.width >= 220 && rect.height >= 40;
            });

        if (widgetContainers.length) {
            widgetContainers.sort((a, b) => {
                const aArea = a.rect.width * a.rect.height;
                const bArea = b.rect.width * b.rect.height;
                return aArea - bArea;
            });
            const { node, rect } = widgetContainers[0];
            return checkboxPointFromRect(
                rect,
                "container",
                node.id || node.className || "turnstile"
            );
        }

        const bodyText = (document.body ? document.body.innerText : "").toLowerCase();
        if (
            bodyText.includes("verify you are human")
            || bodyText.includes("ray id")
            || bodyText.includes("just a moment")
        ) {
            return {
                x: Math.max(24, Math.round((window.innerWidth * 0.5) - 130)),
                y: Math.max(160, Math.round(Math.min(window.innerHeight - 160, window.innerHeight * 0.4))),
                width: 300,
                height: 65,
                source: "viewport-estimate",
                detail: "challenge text fallback",
            };
        }

        return null;
    })();
    """
    return await run_script_value(tab, click_target_script)


async def click_cloudflare_turnstile_checkbox(tab, label, attempt):
    try:
        await tab.bring_to_front()
        await asyncio.sleep(ORDER_PAGE_FRONT_FOCUS_SECONDS)
    except Exception as e:
        print(f"Could not bring {label} to front before Turnstile click: {e}")

    try:
        click_target = await find_cloudflare_turnstile_click_target(tab)
    except Exception as e:
        print(f"Could not locate Turnstile checkbox for {label}: {e}")
        return False

    if not click_target:
        return False

    try:
        click_x = int(round(float(click_target["x"])))
        click_y = int(round(float(click_target["y"])))
    except (KeyError, TypeError, ValueError):
        print(f"Turnstile click target for {label} was malformed: {click_target}")
        return False

    try:
        await tab.mouse.click(click_x, click_y, humanize=True)
        print(
            f"Clicked Cloudflare Turnstile checkbox for {label} "
            f"at ({click_x}, {click_y}) via {click_target.get('source')} "
            f"(attempt {attempt}/{TURNSTILE_MANUAL_CLICK_MAX_ATTEMPTS})."
        )
        await asyncio.sleep(TURNSTILE_MANUAL_CLICK_POST_WAIT_SECONDS)
        return True
    except Exception as e:
        print(f"Turnstile checkbox click failed for {label}: {e}")
        return False


def is_order_page_url(url):
    hostname = urlparse(url).netloc.lower()
    return hostname.endswith("order.fiveguys.com") or hostname.endswith("fiveguys.olo.com")


async def activate_order_page(tab, label, url):
    if not is_order_page_url(url):
        return False

    try:
        await tab.bring_to_front()
        await asyncio.sleep(ORDER_PAGE_FRONT_FOCUS_SECONDS)
    except Exception as e:
        print(f"Could not bring {label} to the front before clicking: {e}")

    click_point_script = """
    (() => {
        const interactiveSelector = [
            "a",
            "button",
            "input",
            "label",
            "select",
            "textarea",
            "summary",
            "[role='button']",
            "[role='link']",
            "[contenteditable='']",
            "[contenteditable='true']",
            "[tabindex]:not([tabindex='-1'])",
        ].join(",");

        const isVisible = (node) => {
            if (!node) {
                return false;
            }

            const rect = node.getBoundingClientRect();
            if (rect.width < 2 || rect.height < 2) {
                return false;
            }

            const style = window.getComputedStyle(node);
            return (
                style.display !== "none"
                && style.visibility !== "hidden"
                && style.pointerEvents !== "none"
            );
        };

        const containers = [
            document.querySelector("main"),
            document.querySelector("[role='main']"),
            document.querySelector("app-root"),
            document.querySelector("app-menu"),
            document.body,
            document.documentElement,
        ].filter(Boolean);

        const seeds = [
            [0.18, 0.18],
            [0.35, 0.18],
            [0.50, 0.18],
            [0.65, 0.18],
            [0.82, 0.18],
            [0.18, 0.34],
            [0.35, 0.34],
            [0.50, 0.34],
            [0.65, 0.34],
            [0.82, 0.34],
            [0.18, 0.52],
            [0.35, 0.52],
            [0.50, 0.52],
            [0.65, 0.52],
            [0.82, 0.52],
        ];

        for (const container of containers) {
            if (!isVisible(container)) {
                continue;
            }

            const rect = container.getBoundingClientRect();
            const left = Math.max(8, rect.left + 8);
            const right = Math.min(window.innerWidth - 8, rect.right - 8);
            const top = Math.max(96, rect.top + 24);
            const bottom = Math.min(window.innerHeight - 8, rect.bottom - 8);

            if (right <= left || bottom <= top) {
                continue;
            }

            for (const [px, py] of seeds) {
                const x = left + ((right - left) * px);
                const y = top + ((bottom - top) * py);
                const target = document.elementFromPoint(x, y);
                if (!isVisible(target)) {
                    continue;
                }
                if (target.closest(interactiveSelector)) {
                    continue;
                }

                return {
                    x,
                    y,
                    tag: target.tagName ? target.tagName.toLowerCase() : null,
                };
            }
        }

        return {
            x: Math.round(window.innerWidth * 0.5),
            y: Math.round(Math.max(140, Math.min(window.innerHeight - 140, window.innerHeight * 0.3))),
            tag: "viewport",
        };
    })();
    """

    for attempt in range(1, ORDER_PAGE_ACTIVATION_RETRIES + 1):
        try:
            click_point = await run_script_value(tab, click_point_script)
        except Exception as e:
            print(
                f"Could not calculate an activation click target for {label} "
                f"(attempt {attempt}/{ORDER_PAGE_ACTIVATION_RETRIES}): {e}"
            )
            click_point = None

        if click_point and click_point.get("x") is not None and click_point.get("y") is not None:
            try:
                await tab.mouse.click(
                    click_point["x"],
                    click_point["y"],
                    humanize=False,
                )
                print(
                    f"Clicked {click_point.get('tag') or 'page'} to activate {label} "
                    f"(attempt {attempt}/{ORDER_PAGE_ACTIVATION_RETRIES})."
                )
                await asyncio.sleep(ORDER_PAGE_ACTIVATION_POST_CLICK_SECONDS)
                return True
            except Exception as e:
                print(
                    f"Activation click failed for {label} "
                    f"(attempt {attempt}/{ORDER_PAGE_ACTIVATION_RETRIES}): {e}"
                )

        if attempt < ORDER_PAGE_ACTIVATION_RETRIES:
            await asyncio.sleep(ORDER_PAGE_ACTIVATION_RETRY_SECONDS)

    print(f"Could not activate {label} with an initial click; continuing anyway.")
    return False


async def reactivate_order_page_if_stalled(
    tab,
    label,
    url,
    stall_polls,
    activation_count,
):
    if not is_order_page_url(url):
        return activation_count

    if activation_count >= ORDER_PAGE_MAX_REACTIVATIONS:
        return activation_count

    if stall_polls < ORDER_PAGE_STALL_REACTIVATION_POLLS:
        return activation_count

    if stall_polls % ORDER_PAGE_STALL_REACTIVATION_POLLS != 0:
        return activation_count

    next_attempt = activation_count + 1
    print(
        f"Page looks stalled for {label}; trying to reactivate it "
        f"({next_attempt}/{ORDER_PAGE_MAX_REACTIVATIONS})."
    )
    await activate_order_page(tab, f"{label} stalled page", url)
    return next_attempt


async def wait_for_turnstile_clear(
    tab,
    label,
    timeout_seconds,
    fail_on_managed_challenge=False,
):
    clear_checks = 0
    managed_challenge_checks = 0
    manual_click_attempts = 0
    last_manual_click_at = 0
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if await page_has_cloudflare_challenge_pydoll(tab):
            clear_checks = 0
            now = time.time()
            if (
                manual_click_attempts < TURNSTILE_MANUAL_CLICK_MAX_ATTEMPTS
                and now - last_manual_click_at >= TURNSTILE_MANUAL_CLICK_RETRY_SECONDS
            ):
                manual_click_attempts += 1
                last_manual_click_at = now
                clicked = await click_cloudflare_turnstile_checkbox(
                    tab,
                    label,
                    manual_click_attempts,
                )
                if clicked:
                    managed_challenge_checks = 0
                    continue

            if fail_on_managed_challenge:
                challenge_details = await get_cloudflare_challenge_details(tab)
                if challenge_details.get("managed_challenge"):
                    managed_challenge_checks += 1
                    if managed_challenge_checks >= MANAGED_CHALLENGE_CONFIRM_POLLS:
                        raise ManagedCloudflareChallengeError(
                            f"Cloudflare escalated {label} into a managed challenge that "
                            f"this scraper cannot auto-solve. "
                            f"{format_cloudflare_challenge_details(challenge_details)}"
                        )
                else:
                    managed_challenge_checks = 0
        elif await page_looks_blank_pydoll(tab):
            clear_checks = 0
            managed_challenge_checks = 0
        else:
            managed_challenge_checks = 0
            clear_checks += 1
            if clear_checks >= 2:
                return True

        await asyncio.sleep(2)

    print(f"Timed out waiting for Cloudflare/session clear for {label}.")
    return False


async def go_to_with_turnstile(
    tab,
    url,
    label,
    timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
    activate_page=False,
    fallback_to_plain_navigation=True,
    use_cloudflare_bypass_wrapper=None,
):
    print(f"Opening {label}: {url}")

    if use_cloudflare_bypass_wrapper is None:
        use_cloudflare_bypass_wrapper = USE_CLOUDFLARE_BYPASS_WRAPPER

    if use_cloudflare_bypass_wrapper:
        try:
            async with tab.expect_and_bypass_cloudflare_captcha(
                time_to_wait_captcha=CHROME_TURNSTILE_WAIT_SECONDS
            ):
                await tab.go_to(url, timeout=timeout_seconds)
        except Exception as e:
            if not fallback_to_plain_navigation:
                raise
            print(
                f"Cloudflare bypass wrapper failed for {label}: {e}. "
                "Retrying with normal navigation."
            )
            await tab.go_to(url, timeout=timeout_seconds)
    else:
        await tab.go_to(url, timeout=timeout_seconds)

    if activate_page:
        await activate_order_page(tab, label, url)


async def clear_order_cloudflare_with_helper_pydoll(
    browser,
    label,
    fail_on_managed_challenge=False,
    wait_seconds=ORDER_CLOUDFLARE_HELPER_WAIT_SECONDS,
    fallback_to_plain_navigation=True,
):
    if not ORDER_CLOUDFLARE_HELPER_ENABLED:
        print(
            f"Order helper recovery is disabled for {label}; "
            "this store will be retried with a fresh browser if needed."
        )
        return False

    helper_tab = await browser.new_tab()
    await helper_tab.enable_auto_solve_cloudflare_captcha(
        time_to_wait_captcha=CHROME_TURNSTILE_WAIT_SECONDS
    )

    try:
        print(
            f"Opening Cloudflare helper page for {label}: "
            f"{ORDER_CLOUDFLARE_HELPER_URL}"
        )
        await go_to_with_turnstile(
            helper_tab,
            ORDER_CLOUDFLARE_HELPER_URL,
            f"{label} Cloudflare helper",
            timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
            fallback_to_plain_navigation=fallback_to_plain_navigation,
            use_cloudflare_bypass_wrapper=True,
        )
        if await wait_for_turnstile_clear(
            helper_tab,
            f"{label} helper",
            wait_seconds,
            fail_on_managed_challenge=fail_on_managed_challenge,
        ):
            print(f"Cloudflare helper looks cleared for {label}.")
            return True

        print(f"Timed out waiting for Cloudflare helper to clear for {label}.")
        return False
    finally:
        await helper_tab.close()


async def reload_blank_order_page_until_done_pydoll(tab, browser, done_future, label, url):
    reload_count = 0

    while not done_future.done() and reload_count < ORDER_BLANK_PAGE_MAX_RELOADS:
        await asyncio.sleep(ORDER_BLANK_PAGE_RELOAD_SECONDS)
        if done_future.done():
            return

        if await page_has_cloudflare_challenge_pydoll(tab):
            continue

        if not await page_looks_blank_pydoll(tab):
            continue

        reload_count += 1
        print(
            f"Order page is blank for {label}; reloading "
            f"({reload_count}/{ORDER_BLANK_PAGE_MAX_RELOADS})"
        )

        try:
            await go_to_with_turnstile(
                tab,
                url,
                label,
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                use_cloudflare_bypass_wrapper=False,
            )
        except Exception as e:
            print(f"Blank-page recovery failed for {label}: {e}")

    if done_future.done():
        return

    if await page_has_cloudflare_challenge_pydoll(tab):
        return

    if await page_looks_blank_pydoll(tab):
        if not ORDER_CLOUDFLARE_HELPER_ENABLED:
            print(
                f"Order page stayed blank for {label}; skipping this menu so "
                "the store can retry with a fresh browser."
            )
            done_future.set_result(None)
            return

        print(f"Order page stayed blank for {label}; using helper page to clear Cloudflare.")
        try:
            helper_cleared = await clear_order_cloudflare_with_helper_pydoll(browser, label)
            if not helper_cleared:
                print(f"Cloudflare helper did not clear for {label}; skipping this menu.")
                done_future.set_result(None)
                return

            print(f"Retrying {label} after helper Cloudflare clear.")
            await go_to_with_turnstile(
                tab,
                url,
                label,
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                use_cloudflare_bypass_wrapper=False,
            )
            await asyncio.sleep(ORDER_BLANK_PAGE_RELOAD_SECONDS)
            if done_future.done():
                return

            if await page_has_cloudflare_challenge_pydoll(tab):
                print(f"{label} still needs Cloudflare after helper.")
                return

            if await page_looks_blank_pydoll(tab):
                print(f"Order page stayed blank for {label} even after helper; skipping this menu.")
                done_future.set_result(None)
        except Exception as e:
            print(f"Helper recovery failed for {label}: {e}")
            done_future.set_result(None)


async def ensure_initial_order_session(tab, browser):
    await tab.enable_auto_solve_cloudflare_captcha(
        time_to_wait_captcha=CHROME_TURNSTILE_WAIT_SECONDS
    )
    await go_to_with_turnstile(
        tab,
        CHROME_START_URL,
        "initial order hub",
        timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
        fallback_to_plain_navigation=False,
        use_cloudflare_bypass_wrapper=True,
    )

    if await wait_for_turnstile_clear(
        tab,
        "initial order hub",
        BOOTSTRAP_SESSION_READY_WAIT_SECONDS,
    ):
        await reset_order_client_state(tab, "initial order hub")
        print("Cloudflare/session looks ready. Starting scraper...")
        return

    if not ORDER_CLOUDFLARE_HELPER_ENABLED:
        raise TimeoutError(
            "Timed out waiting for the initial Cloudflare/Turnstile flow to clear."
        )

    print("Initial order hub did not clear cleanly; trying helper page once.")
    helper_cleared = await clear_order_cloudflare_with_helper_pydoll(
        browser,
        "initial order hub",
        wait_seconds=BOOTSTRAP_HELPER_WAIT_SECONDS,
        fallback_to_plain_navigation=False,
    )
    if not helper_cleared:
        raise TimeoutError(
            "Timed out waiting for the initial Cloudflare/Turnstile flow to clear."
        )

    await go_to_with_turnstile(
        tab,
        CHROME_START_URL,
        "initial order hub retry",
        timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
        fallback_to_plain_navigation=False,
        use_cloudflare_bypass_wrapper=True,
    )
    if not await wait_for_turnstile_clear(
        tab,
        "initial order hub retry",
        BOOTSTRAP_SESSION_READY_WAIT_SECONDS,
    ):
        raise TimeoutError(
            "Cloudflare/Turnstile still did not clear after helper recovery."
        )

    await reset_order_client_state(tab, "initial order hub retry")
    print("Cloudflare/session looks ready after helper recovery. Starting scraper...")


@dataclass
class MenuItem:
    name: str | None
    price: Decimal | None
    categories: str | None
    location: str | None

@dataclass
class FiveGuysLocation:
    name: str | None
    street: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    phone: str | None
    google_maps_cid: str | None
    google_maps_url: str | None
    order_url: str | None
    hours: dict | None
    delivery_hours: dict | None
    services: list[str] | None
    payment_methods: list[str] | None
    rating: float | None
    review_count: int | None
    reviews: list[dict] | None
    menu: list[dict] | None


async def get_html_pydoll(url, tab, ready_selector=None):
    try:
        await tab.go_to(url, timeout=LOCATION_NAVIGATION_TIMEOUT_SECONDS)
        if ready_selector:
            try:
                await tab.query(ready_selector, timeout=10, raise_exc=False)
            except Exception:
                pass
        return HTMLParser(await tab.page_source)
    except Exception as e:
        print(f"Failed to load {url}: {e}")
        return None


def is_restaurants_site_url(url):
    return urlparse(url).netloc.lower() == "restaurants.fiveguys.com"


def fetch_html_http_sync(url):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=HTTP_LOCATION_TIMEOUT_SECONDS) as response:
        body = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        return body.decode(encoding, errors="replace")


async def get_restaurants_html(url, tab=None, ready_selector=None):
    if USE_HTTP_FOR_RESTAURANT_PAGES and is_restaurants_site_url(url):
        for attempt in range(1, HTTP_LOCATION_ATTEMPTS + 1):
            try:
                html_text = await asyncio.to_thread(fetch_html_http_sync, url)
                html = HTMLParser(html_text)
                if not ready_selector or html.css_first(ready_selector):
                    return html
                print(
                    f"HTTP loaded {url}, but expected selector was missing; "
                    "falling back to browser navigation."
                )
                break
            except (HTTPError, URLError, TimeoutError, OSError) as e:
                print(
                    f"HTTP load failed for {url} "
                    f"({attempt}/{HTTP_LOCATION_ATTEMPTS}): {e}"
                )
                if attempt < HTTP_LOCATION_ATTEMPTS:
                    await asyncio.sleep(1)

    if tab is None:
        return None
    return await get_html_pydoll(url, tab, ready_selector=ready_selector)


def parse_menu_item(html, page, collections=None):
    price_raw = html.css_first("sale-price").text().strip()
    price = Decimal(
        price_raw.replace("\u20ac", "").replace("Sale price", "").replace(",", ".").strip()
    ) if price_raw else None

    new_item = MenuItem(
        name=extract_text(html, "h1.product-title"),
        price=price,
        categories=list(collections) if collections else [],
    )
    return asdict(new_item)


def extract_text(html, sel):
    try:
        return html.css_first(sel).text()
    except AttributeError:
        return None


def parse_money(value):
    if value in (None, ""):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
    return Decimal(match.group()) if match else None


def parse_int(value):
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value).replace(",", ""))
    return int(match.group()) if match else None


def clean_text(value):
    if value is None:
        return None
    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def slugify(value):
    value = clean_text(value) or ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or None


def parse_calories_delta(value):
    if value in (None, ""):
        return None
    match = re.search(r"[+-]?\d+", str(value).replace(",", ""))
    return int(match.group()) if match else None


def canonical_order_menu_url(value):
    cleaned = clean_text(value)
    if not cleaned:
        return None

    parsed_url = urlparse(cleaned)
    host = parsed_url.netloc.lower()
    if host != "order.fiveguys.com":
        return cleaned.rstrip("/")

    path_parts = [part for part in parsed_url.path.split("/") if part]
    slug = None
    if len(path_parts) == 2 and path_parts[0] == "menu":
        slug = path_parts[1]
    elif len(path_parts) == 2 and path_parts[1] == "menu":
        slug = path_parts[0]

    if not slug:
        return cleaned.rstrip("/")

    return urlunparse(
        (
            parsed_url.scheme or "https",
            parsed_url.netloc,
            f"/location/{slug}/menu",
            "",
            "",
            "",
        )
    )


def is_canonical_order_menu_url(value):
    cleaned = clean_text(value)
    if not cleaned:
        return False

    parsed_url = urlparse(cleaned)
    if parsed_url.netloc.lower() != "order.fiveguys.com":
        return False

    path_parts = [part for part in parsed_url.path.split("/") if part]
    return (
        len(path_parts) == 3
        and path_parts[0] == "location"
        and bool(path_parts[1])
        and path_parts[2] == "menu"
    )


def extract_order_url(html):
    for a in html.css("a[href]"):
        href = a.attributes.get("href", "")
        if "order.fiveguys.com" in href and "/menu" in href:
            return canonical_order_menu_url(href)
        if "fiveguys.olo.com/menu" in href:
            return href
    return None


def extract_order_slug(order_url):
    path_parts = [part for part in urlparse(order_url).path.split("/") if part]

    if "location" in path_parts:
        location_index = path_parts.index("location")
        if location_index + 1 < len(path_parts):
            return path_parts[location_index + 1]

    if "menu" in path_parts:
        menu_index = path_parts.index("menu")
        if menu_index + 1 < len(path_parts):
            return path_parts[menu_index + 1]
        if menu_index > 0:
            return path_parts[menu_index - 1]

    return None


def normalize_order_url(value):
    return canonical_order_menu_url(value)


def build_direct_menu_json_url(order_url, restaurant_id):
    restaurant_id = clean_text(restaurant_id)
    if not restaurant_id:
        return None
    return f"https://order.fiveguys.com/restaurants/{restaurant_id}/menu?{ORDER_MENU_QUERY}"


def register_known_restaurant_id(order_url, restaurant_id):
    if not is_canonical_order_menu_url(order_url):
        return

    normalized_order_url = normalize_order_url(order_url)
    restaurant_id = clean_text(restaurant_id)
    if normalized_order_url and restaurant_id:
        KNOWN_RESTAURANT_IDS_BY_ORDER_URL[normalized_order_url] = restaurant_id


def load_known_restaurant_ids():
    global KNOWN_RESTAURANT_IDS_LOADED
    if KNOWN_RESTAURANT_IDS_LOADED:
        return

    KNOWN_RESTAURANT_IDS_LOADED = True

    if MENU_ITEMS_JSON_PATH.exists():
        try:
            with open(MENU_ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            payload = None

        if isinstance(payload, list):
            for row in payload:
                if not isinstance(row, dict):
                    continue

                order_url = row.get("order_url")
                restaurant_id = row.get("restaurant_id")
                register_known_restaurant_id(order_url, restaurant_id)

    if MENU_ITEMS_CSV_PATH.exists():
        try:
            with open(MENU_ITEMS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    register_known_restaurant_id(
                        row.get("order_url"),
                        row.get("restaurant_id"),
                    )
        except Exception:
            pass


def get_known_restaurant_id(order_url):
    load_known_restaurant_ids()
    return KNOWN_RESTAURANT_IDS_BY_ORDER_URL.get(normalize_order_url(order_url))


def restaurant_slug_candidates(menu_json):
    restaurant = menu_json.get("restaurant") or {}
    candidates = set()

    if restaurant.get("slug"):
        candidates.add(restaurant["slug"])

    for key in ("url", "mobileurl"):
        url = restaurant.get(key)
        if not url:
            continue
        path_parts = [part for part in urlparse(url).path.split("/") if part]
        if "menu" in path_parts:
            menu_index = path_parts.index("menu")
            if menu_index + 1 < len(path_parts):
                candidates.add(path_parts[menu_index + 1])
        elif path_parts:
            candidates.add(path_parts[-1])

    return candidates


def slugs_equivalent(expected_slug, candidate_slug):
    expected_slug = slugify(expected_slug)
    candidate_slug = slugify(candidate_slug)
    if not expected_slug or not candidate_slug:
        return False
    if expected_slug == candidate_slug:
        return True
    return (
        expected_slug == f"five-guys-{candidate_slug}"
        or candidate_slug == f"five-guys-{expected_slug}"
    )


def menu_matches_order_url(menu_json, order_url):
    expected_slug = extract_order_slug(order_url)
    if not expected_slug:
        expected_url = normalize_order_url(order_url)
        restaurant = menu_json.get("restaurant") or {}
        return any(
            normalize_order_url(restaurant.get(key)) == expected_url
            for key in ("url", "mobileurl")
        )

    candidates = restaurant_slug_candidates(menu_json)
    return any(slugs_equivalent(expected_slug, candidate) for candidate in candidates)


def parse_menu_json(menu_json):
    items = []
    imagepath = menu_json.get("imagepath", "")
    restaurant = menu_json.get("restaurant") or {}
    restaurant_id = restaurant.get("id")
    location_name = restaurant.get("name")

    for category in menu_json.get("categories", []):
        category_name = category.get("name")
        category_slug = category.get("slug")

        if category_slug in ("single-use-items", "catering"):
            continue

        for product in category.get("products", []):
            metadata = product.get("metadata") or []
            price_override = None
            product_image = None
            has_modifiers = None

            for meta in metadata:
                if meta.get("key") == "nomnom_price_override":
                    price_override = meta.get("value")
                elif meta.get("key") == "product-image":
                    product_image = meta.get("value")
                elif meta.get("key") == "has-modifiers":
                    has_modifiers = meta.get("value")

            cost = product.get("cost")
            price = Decimal(str(cost)) if cost not in (None, "") else None
            base_price = None
            base_price_display = None
            min_price = None
            max_price = None
            price_range_display = None
            price_type = "fixed" if price is not None else None
            pricing_note = None
            option_groups = []

            if category_slug == "classic-combo":
                base_price = parse_money(price_override)
                base_price_display = price_override
                base_price_for_range = base_price or Decimal("0")
                min_upcharge = Decimal("0")
                max_upcharge = Decimal("0")

                for option_group in product.get("optiongroups", []) or []:
                    parsed_options = []
                    option_costs = []
                    options = option_group.get("options") or option_group.get("choices") or []

                    for option in options:
                        option_cost = option.get("cost")
                        option_cost = parse_money(option_cost) if option_cost not in (None, "") else Decimal("0")
                        option_cost = option_cost or Decimal("0")
                        option_costs.append(option_cost)
                        parsed_options.append({
                            "name": option.get("name") or option.get("description"),
                            "cost": option_cost,
                        })

                    min_upcharge += min(option_costs) if option_costs else Decimal("0")
                    max_upcharge += max(option_costs) if option_costs else Decimal("0")
                    option_groups.append({
                        "description": option_group.get("description") or option_group.get("name"),
                        "options": parsed_options,
                    })

                min_price = base_price_for_range + min_upcharge
                max_price = base_price_for_range + max_upcharge
                price = None
                price_type = "configurable"
                price_display = f"From ${min_price:.2f}"
                price_range_display = f"${min_price:.2f} \u2013 ${max_price:.2f}"
                pricing_note = "Base combo price varies with sandwich, fry, and drink choices."
            else:
                price_display = f"${price:.2f}" if price is not None else None

            base_calories = product.get("basecalories")
            max_calories = product.get("maxcalories")
            calories_separator = product.get("caloriesseparator") or "-"

            if base_calories and max_calories:
                calories = f"{base_calories}{calories_separator}{max_calories}"
            else:
                calories = base_calories or max_calories

            image = product_image
            if image and image.startswith("//"):
                image = "https:" + image
            elif image and not image.startswith(("http://", "https://")):
                image = "https://" + image

            if not image and product.get("imagefilename"):
                image = urljoin(imagepath.rstrip("/") + "/", product.get("imagefilename"))

            description = product.get("description")
            if description:
                description = re.sub(r"<[^>]+>", " ", description)
                description = " ".join(description.replace("\xa0", " ").split())

            availability = product.get("availability") or {}
            name = product.get("name")
            if name:
                name = " ".join(name.split())

            items.append({
                "restaurant_id": restaurant_id,
                "location": location_name,
                "category": category_name,
                "category_slug": category_slug,
                "name": name,
                "slug": product.get("slug"),
                "product_id": product.get("id"),
                "chainproductid": product.get("chainproductid"),
                "price": price,
                "price_display": price_display,
                "base_price": base_price,
                "base_price_display": base_price_display,
                "min_price": min_price,
                "max_price": max_price,
                "price_range_display": price_range_display,
                "price_type": price_type,
                "pricing_note": pricing_note,
                "option_groups": option_groups,
                "price_override": price_override,
                "base_calories": base_calories,
                "max_calories": max_calories,
                "calories": calories,
                "description": description,
                "image": image,
                "available": availability.get("now"),
                "has_modifiers": has_modifiers,
                "unavailable_handoff_modes": product.get("unavailablehandoffmodes") or [],
            })

    return items


def get_classic_combo_menu_item(location):
    for item in location.get("menu") or []:
        if (
            item.get("category_slug") == "classic-combo"
            or item.get("slug") == CLASSIC_COMBO_FALLBACK_SLUG
            or (clean_text(item.get("name")) or "").lower() == "classic combo"
        ):
            return item
    return None


def classic_combo_timeout_seconds(location):
    if get_classic_combo_menu_item(location):
        return CLASSIC_COMBO_PRESENT_TIMEOUT_SECONDS
    return CLASSIC_COMBO_FALLBACK_TIMEOUT_SECONDS


def classic_combo_render_attempts(location):
    if get_classic_combo_menu_item(location):
        return CLASSIC_COMBO_PRESENT_RENDER_ATTEMPTS
    return CLASSIC_COMBO_RENDER_ATTEMPTS


def get_menu_location_metadata(location):
    for item in location.get("menu") or []:
        if item.get("restaurant_id") or item.get("location"):
            return {
                "restaurant_id": item.get("restaurant_id"),
                "location": item.get("location"),
            }
    return {}


def classic_combo_url_for_location(location):
    order_url = location.get("order_url")
    combo_item = get_classic_combo_menu_item(location)
    if not order_url:
        return None
    if not combo_item and not CLASSIC_COMBO_PAGE_FALLBACK:
        location["_classic_combo_unavailable"] = True
        print(
            f"Classic Combo is not listed in menu JSON for {location.get('name')}; "
            "skipping Classic Combo page scrape."
        )
        return None

    combo_slug = (
        (combo_item or {}).get("slug")
        or CLASSIC_COMBO_FALLBACK_SLUG
    )
    combo_chain_id = (
        (combo_item or {}).get("chainproductid")
        or CLASSIC_COMBO_FALLBACK_CHAINPRODUCTID
    )
    if not combo_item:
        print(
            f"Classic Combo was not listed in menu JSON for {location.get('name')}; "
            f"CLASSIC_COMBO_PAGE_FALLBACK is enabled, so trying fallback product "
            f"route {combo_slug}/{combo_chain_id}."
        )
    return f"{order_url.rstrip('/')}/{combo_slug}/{combo_chain_id}"


def classic_combo_product_presence_row(
    location,
    classic_combo_url=None,
    detail_status="menu_json_only",
):
    combo_item = get_classic_combo_menu_item(location)
    if not combo_item:
        return None

    order_url = location.get("order_url")
    combo_slug = combo_item.get("slug") or CLASSIC_COMBO_FALLBACK_SLUG
    combo_chain_id = combo_item.get("chainproductid") or CLASSIC_COMBO_FALLBACK_CHAINPRODUCTID
    if not classic_combo_url and order_url:
        classic_combo_url = f"{order_url.rstrip('/')}/{combo_slug}/{combo_chain_id}"

    menu_metadata = get_menu_location_metadata(location)
    return {
        "store_name": location.get("name"),
        "store_street": location.get("street"),
        "store_city": location.get("city"),
        "store_state": location.get("state"),
        "store_zip_code": location.get("zip_code"),
        "order_url": order_url,
        "classic_combo_url": classic_combo_url,
        "restaurant_id": combo_item.get("restaurant_id") or menu_metadata.get("restaurant_id"),
        "location": combo_item.get("location") or menu_metadata.get("location"),
        "classic_combo_product_id": combo_item.get("product_id"),
        "classic_combo_chainproductid": combo_chain_id,
        "row_type": "product",
        "classic_combo_price": combo_item.get("price"),
        "classic_combo_price_display": combo_item.get("price_display"),
        "classic_combo_available": combo_item.get("available"),
        "detail_status": detail_status,
        "group_index": 0,
        "group_name": "Classic Combo Product",
        "group_requirement": "Menu JSON",
        "selected_sandwich": None,
        "selected_sandwich_slug": None,
        "selected_sandwich_price_delta": None,
        "selected_sandwich_price_delta_display": None,
        "item_name": combo_item.get("name") or "Classic Combo",
        "item_slug": combo_item.get("slug") or CLASSIC_COMBO_FALLBACK_SLUG,
        "input_id": None,
        "price_delta": None,
        "price_delta_display": None,
        "calories_delta": None,
        "calories_delta_display": None,
        "image": combo_item.get("image"),
        "selected_by_default": None,
    }


def classic_combo_product_presence_rows(
    location,
    classic_combo_url=None,
    detail_status="menu_json_only",
):
    row = classic_combo_product_presence_row(location, classic_combo_url, detail_status)
    return [row] if row else []


def get_milkshake_menu_item(location):
    for item in location.get("menu") or []:
        if item.get("slug") == "milkshake":
            return item
        if (
            item.get("category_slug") == "shakes"
            and (item.get("name") or "").strip().lower() == "milkshake"
        ):
            return item
    return None


def milkshake_url_for_location(location):
    order_url = location.get("order_url")
    milkshake_item = get_milkshake_menu_item(location)
    if not order_url or not milkshake_item:
        return None

    milkshake_slug = milkshake_item.get("category_slug") or milkshake_item.get("slug") or "shakes"
    milkshake_chain_id = milkshake_item.get("chainproductid") or "105653"
    return f"{order_url.rstrip('/')}/{milkshake_slug}/{milkshake_chain_id}"


def milkshake_detail_product_ids(location):
    milkshake_item = get_milkshake_menu_item(location) or {}
    candidates = set()

    for value in (milkshake_item.get("product_id"), milkshake_item.get("milkshake_product_id")):
        if value not in (None, ""):
            candidates.add(str(value).strip())

    menu_json = location.get("_menu_json")
    if isinstance(menu_json, dict):
        milkshake_product = get_milkshake_product(menu_json)
        if milkshake_product and milkshake_product.get("id") not in (None, ""):
            candidates.add(str(milkshake_product["id"]).strip())

    if candidates:
        return candidates

    for value in (milkshake_item.get("chainproductid"), milkshake_item.get("milkshake_chainproductid")):
        if value not in (None, ""):
            candidates.add(str(value).strip())

    return candidates


def primary_milkshake_detail_product_id(location):
    milkshake_item = get_milkshake_menu_item(location) or {}

    for value in (milkshake_item.get("product_id"), milkshake_item.get("milkshake_product_id")):
        if value not in (None, ""):
            return str(value).strip()

    menu_json = location.get("_menu_json")
    if isinstance(menu_json, dict):
        milkshake_product = get_milkshake_product(menu_json)
        if milkshake_product and milkshake_product.get("id") not in (None, ""):
            return str(milkshake_product["id"]).strip()

    return None


def milkshake_modifiers_url(product_id):
    product_id = clean_text(product_id)
    if not product_id:
        return None
    return f"https://order.fiveguys.com/products/{product_id}/modifiers"


def product_id_from_modifiers_url(url):
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if len(path_parts) >= 3 and path_parts[0] == "products" and path_parts[2] == "modifiers":
        return path_parts[1]
    return None


def find_menu_category(menu_json, slug):
    for category in menu_json.get("categories", []) or []:
        if category.get("slug") == slug:
            return category
    return None


def get_milkshake_product(menu_json):
    shakes_category = find_menu_category(menu_json, "shakes")
    if not shakes_category:
        return None

    for product in shakes_category.get("products", []) or []:
        if product.get("slug") == "milkshake":
            return product
        if clean_text(product.get("name")) == "Milkshake":
            return product
    return None


def parse_option_group_requirement(option_group):
    explicit = clean_text(
        option_group.get("requirement")
        or option_group.get("requirementtext")
        or option_group.get("requiredtext")
        or option_group.get("label")
    )
    if explicit in ("Required", "Optional", "Selected"):
        return explicit

    min_choices = option_group.get("minchoices")
    if min_choices is None:
        min_choices = option_group.get("minchoicecount")
    if min_choices is None:
        min_choices = option_group.get("minimumchoices")
    if min_choices is None:
        min_choices = option_group.get("minimum")
    if min_choices is None:
        min_choices = option_group.get("min")
    if min_choices is None:
        min_choices = option_group.get("minselects")

    try:
        min_choices = int(min_choices)
    except (TypeError, ValueError):
        min_choices = 0

    if option_group.get("required") or option_group.get("mandatory") or min_choices > 0:
        return "Required"
    return "Optional"


def option_group_options(option_group):
    return option_group.get("options") or option_group.get("choices") or []


def option_image(option, imagepath=""):
    metadata = option.get("metadata") or []
    image = None

    for meta in metadata:
        if meta.get("key") == "product-image":
            image = meta.get("value")
            break
        if meta.get("key") == "option-image":
            image = meta.get("value")
            break

    if not image:
        image = option.get("imageurl") or option.get("image")

    if not image:
        images = option.get("images") or []
        preferred_groups = (
            "mobileweb-modifier-choice",
            "mobileapp-modifier-choice",
            "mobile-webapp-customize",
            "mobile-app",
            "marketplace-product",
        )
        chosen = None
        for preferred_group in preferred_groups:
            chosen = next(
                (candidate for candidate in images if candidate.get("groupname") == preferred_group),
                None,
            )
            if chosen:
                break
        if not chosen and images:
            chosen = images[0]
        if chosen:
            image = chosen.get("url") or chosen.get("filename")

    if image and image.startswith("//"):
        image = "https:" + image
    elif image and not image.startswith(("http://", "https://")):
        if imagepath:
            image = urljoin(imagepath.rstrip("/") + "/", image.lstrip("/"))
        else:
            image = "https://" + image.lstrip("/")

    if not image and imagepath and option.get("imagefilename"):
        image = urljoin(imagepath.rstrip("/") + "/", option.get("imagefilename"))

    return image


def is_milkshake_detail_payload(payload):
    if not isinstance(payload, dict):
        return False

    option_groups = payload.get("optiongroups")
    if not isinstance(option_groups, list) or not option_groups:
        return False

    for option_group in option_groups:
        group_name = clean_text(
            option_group.get("description")
            or option_group.get("name")
            or option_group.get("displayname")
            or option_group.get("title")
        )
        options = option_group_options(option_group)
        if options and is_milkshake_mixin_group(group_name):
            return True

    return False


def find_milkshake_detail_payload(payload, max_depth=6):
    if max_depth < 0:
        return None

    if is_milkshake_detail_payload(payload):
        return payload

    if isinstance(payload, str):
        if max_depth == 0:
            return None

        candidate_text = payload.strip()
        if not candidate_text:
            return None

        lowered = candidate_text.lower()
        if (
            "optiongroups" not in lowered
            and "select unlimited mix-ins" not in lowered
            and "whipped cream" not in lowered
            and "oreo" not in lowered
        ):
            return None

        nested_payload = load_json_response_body(candidate_text)
        if nested_payload is None or nested_payload == payload:
            return None

        return find_milkshake_detail_payload(nested_payload, max_depth=max_depth - 1)

    if isinstance(payload, dict):
        for value in payload.values():
            found = find_milkshake_detail_payload(value, max_depth=max_depth - 1)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_milkshake_detail_payload(value, max_depth=max_depth - 1)
            if found is not None:
                return found

    return None


def load_json_response_body(body):
    if isinstance(body, (dict, list)):
        return body
    if not isinstance(body, str):
        return None

    candidates = []
    stripped = body.strip()
    if stripped:
        candidates.append(stripped)

        bom_stripped = stripped.lstrip("\ufeff")
        if bom_stripped and bom_stripped != stripped:
            candidates.append(bom_stripped)

        anti_xssi_stripped = re.sub(r"^\)\]\}',?\s*", "", bom_stripped)
        if anti_xssi_stripped and anti_xssi_stripped not in candidates:
            candidates.append(anti_xssi_stripped)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


def summarize_payload_shape(payload, max_items=6):
    if isinstance(payload, dict):
        keys = list(payload.keys())
        preview = ", ".join(keys[:max_items])
        if len(keys) > max_items:
            preview += ", ..."
        return f"dict[{preview}]" if preview else "dict[]"

    if isinstance(payload, list):
        return f"list(len={len(payload)})"

    if isinstance(payload, str):
        normalized = " ".join(payload.strip().split())
        if len(normalized) > 80:
            normalized = normalized[:77] + "..."
        return f"str[{normalized}]"

    return type(payload).__name__


def parse_milkshake_mixins_from_menu_json(menu_json, location):
    product = get_milkshake_product(menu_json)
    if not product:
        return []

    milkshake_url = milkshake_url_for_location(location)
    restaurant = menu_json.get("restaurant") or {}
    imagepath = menu_json.get("imagepath", "")
    rows = []
    any_mix_group = False

    option_groups = product.get("optiongroups") or []
    for option_group in option_groups:
        group_name = clean_text(
            option_group.get("description")
            or option_group.get("name")
            or option_group.get("displayname")
            or option_group.get("title")
        ) or "Milkshake Options"

        if is_milkshake_mixin_group(group_name):
            any_mix_group = True

        options = option_group_options(option_group)
        if not options:
            continue

        for option in options:
            price_delta = parse_money(option.get("cost")) or Decimal("0.00")
            price_delta_display = (
                f"{price_delta:+.2f}".replace("+", "+$").replace("-$", "-$")
                if price_delta != Decimal("0.00")
                else "+$0.00"
            )
            if price_delta != Decimal("0.00"):
                price_delta_display = f"{'+' if price_delta >= 0 else '-'}${abs(price_delta):.2f}"

            calories_raw = (
                option.get("basecalories")
                or option.get("calories")
                or option.get("maxcalories")
            )
            calories_delta = parse_calories_delta(calories_raw)
            calories_delta_display = f"{calories_delta:+d} Cal" if calories_delta is not None else None

            name = clean_text(option.get("name") or option.get("description"))
            if not name:
                continue

            rows.append({
                "store_name": location.get("name"),
                "store_street": location.get("street"),
                "store_city": location.get("city"),
                "store_state": location.get("state"),
                "store_zip_code": location.get("zip_code"),
                "order_url": location.get("order_url"),
                "milkshake_url": milkshake_url,
                "restaurant_id": restaurant.get("id") or location.get("restaurant_id"),
                "location": restaurant.get("name") or location.get("location"),
                "milkshake_product_id": product.get("id"),
                "milkshake_chainproductid": product.get("chainproductid"),
                "group_index": 0,
                "group_name": group_name,
                "group_requirement": parse_option_group_requirement(option_group),
                "item_name": name,
                "item_slug": slugify(name),
                "input_id": option.get("id") or option.get("chainoptionid"),
                "price_delta": price_delta,
                "price_delta_display": price_delta_display,
                "calories_delta": calories_delta,
                "calories_delta_display": calories_delta_display,
                "image": option_image(option, imagepath=imagepath),
                "selected_by_default": bool(
                    option.get("default")
                    or option.get("isdefault")
                    or option.get("preselected")
                ),
            })

    if any_mix_group:
        rows = [row for row in rows if is_milkshake_mixin_group(row.get("group_name"))]

    return dedupe_milkshake_mixin_rows(reindex_classic_combo_groups(rows))


def parse_milkshake_mixins_from_detail_json(detail_json, location):
    if not is_milkshake_detail_payload(detail_json):
        return []

    milkshake_item = get_milkshake_menu_item(location) or {}
    milkshake_url = milkshake_url_for_location(location)
    imagepath = detail_json.get("imagepath", "")
    rows = []

    for option_group in detail_json.get("optiongroups") or []:
        group_name = clean_text(
            option_group.get("description")
            or option_group.get("name")
            or option_group.get("displayname")
            or option_group.get("title")
        ) or "Milkshake Options"

        if not is_milkshake_mixin_group(group_name):
            continue

        for option in option_group_options(option_group):
            name = clean_text(option.get("name") or option.get("description"))
            if not name:
                continue

            price_delta = parse_money(option.get("cost")) or Decimal("0.00")
            price_delta_display = f"{'+' if price_delta >= 0 else '-'}${abs(price_delta):.2f}"
            if price_delta == Decimal("0.00"):
                price_delta_display = "+$0.00"

            calories_raw = (
                option.get("basecalories")
                or option.get("calories")
                or option.get("maxcalories")
            )
            calories_delta = parse_calories_delta(calories_raw)
            calories_delta_display = f"{calories_delta:+d} Cal" if calories_delta is not None else None

            rows.append({
                "store_name": location.get("name"),
                "store_street": location.get("street"),
                "store_city": location.get("city"),
                "store_state": location.get("state"),
                "store_zip_code": location.get("zip_code"),
                "order_url": location.get("order_url"),
                "milkshake_url": milkshake_url,
                "restaurant_id": milkshake_item.get("restaurant_id"),
                "location": milkshake_item.get("location"),
                "milkshake_product_id": milkshake_item.get("product_id"),
                "milkshake_chainproductid": milkshake_item.get("chainproductid"),
                "group_index": 0,
                "group_name": group_name,
                "group_requirement": parse_option_group_requirement(option_group),
                "item_name": name,
                "item_slug": slugify(name),
                "input_id": option.get("id") or option.get("chainoptionid"),
                "price_delta": price_delta,
                "price_delta_display": price_delta_display,
                "calories_delta": calories_delta,
                "calories_delta_display": calories_delta_display,
                "image": option_image(option, imagepath=imagepath),
                "selected_by_default": bool(
                    option.get("isdefault")
                    or option.get("default")
                    or option.get("preselected")
                ),
            })

    return dedupe_milkshake_mixin_rows(reindex_classic_combo_groups(rows))


def node_classes(node):
    if not node:
        return ""
    classes = node.attributes.get("class")
    return classes or ""


CLASSIC_COMBO_TOP_GROUPS = {
    "choose your sandwich",
    "choose your fries",
    "choose your drink",
}

MILKSHAKE_MIXIN_GROUP_PATTERN = re.compile(r"\bmix[\s-]*ins?\b", re.IGNORECASE)


def parse_combo_detail_text(detail_text):
    detail_text = clean_text(detail_text)
    if not detail_text:
        return None, None, None, None

    price_delta = None
    price_delta_display = None
    calories_delta = None
    calories_delta_display = None

    price_match = re.search(r"[+-]?\$\s*\d+(?:\.\d+)?", detail_text)
    if price_match:
        price_delta_display = price_match.group().replace("$ ", "$")
        price_delta = parse_money(price_delta_display)

    calories_match = re.search(r"[+-]?\d+\s*Cal\.?", detail_text, re.IGNORECASE)
    if calories_match:
        calories_delta_display = clean_text(calories_match.group())
        calories_delta = parse_calories_delta(calories_delta_display)

    return price_delta, price_delta_display, calories_delta, calories_delta_display


def normalize_group_name(value):
    return (clean_text(value) or "").lower()


def is_milkshake_mixin_group(value):
    normalized = clean_text(value) or ""
    return bool(MILKSHAKE_MIXIN_GROUP_PATTERN.search(normalized))


def find_page_group_name(html, matcher):
    for selector in ("h2.modifier-name", ".modifier-name", "h2", "h3"):
        for node in html.css(selector):
            text = clean_text(node.text())
            if text and matcher(text):
                return text
    return None


def has_hidden_ancestor(node):
    current = node
    while current:
        if "hidden" in node_classes(current).split():
            return True
        current = getattr(current, "parent", None)
    return False


def nearest_combo_group_container(node):
    current = node
    while current:
        classes = node_classes(current)
        if (
            "pdp-form-default__modifierGroup__combo-banner__nested-content" in classes
            or "pdp-form-default__modifierGroup__content" in classes
        ):
            return current
        current = getattr(current, "parent", None)
    return None


def first_child_text(node, selectors):
    if not node:
        return None

    for selector in selectors:
        found = node.css_first(selector)
        if found:
            text = clean_text(found.text())
            if text:
                return text
    return None


def find_combo_group_name(container):
    current = getattr(container, "parent", None) or container

    for _ in range(4):
        group_name = first_child_text(current, ["h2.modifier-name", ".modifier-name"])
        if group_name:
            return group_name
        current = getattr(current, "parent", None)
        if not current:
            break

    return "Classic Combo"


def find_combo_group_requirement(container):
    current = getattr(container, "parent", None) or container
    if not current:
        return None

    for _ in range(3):
        for span in current.css("span"):
            text = clean_text(span.text())
            if text in ("Required", "Optional", "Selected"):
                return text
        current = getattr(current, "parent", None)
        if not current:
            break

    return None


def classic_combo_row_key(row):
    return (
        row.get("selected_sandwich_slug"),
        row.get("group_name"),
        row.get("item_slug") or row.get("item_name"),
        row.get("price_delta_display"),
        row.get("calories_delta_display"),
    )


def dedupe_classic_combo_rows(rows):
    unique_rows = []
    seen = set()

    for row in rows:
        key = classic_combo_row_key(row)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    return reindex_classic_combo_groups(unique_rows)


def reindex_classic_combo_groups(rows):
    group_indexes = {}

    for row in rows:
        group_name = row.get("group_name") or "Classic Combo"
        if group_name not in group_indexes:
            group_indexes[group_name] = len(group_indexes) + 1
        row["group_index"] = group_indexes[group_name]

    return rows


def clean_classic_combo_row(row):
    if (row.get("item_name") or "").startswith("A.1."):
        row["item_name"] = "A.1.\u00ae Steak Sauce"
        row["item_slug"] = "a-1-steak-sauce"

    if (row.get("item_name") or "").lower().startswith("no bun"):
        row["group_name"] = "Prefer no bun?"
        row["group_requirement"] = "Optional"

    return row


def milkshake_mixin_row_key(row):
    return (
        row.get("group_name"),
        row.get("item_slug") or row.get("item_name"),
        row.get("price_delta_display"),
        row.get("calories_delta_display"),
    )


def dedupe_milkshake_mixin_rows(rows):
    unique_rows = []
    seen = set()

    for row in rows:
        key = milkshake_mixin_row_key(row)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    return unique_rows


def parse_classic_combo_page(
    html,
    location,
    classic_combo_url,
    selected_sandwich=None,
    skip_group_names=None,
):
    rows = []
    seen = set()
    group_indexes = {}
    combo_item = get_classic_combo_menu_item(location) or {}
    menu_metadata = get_menu_location_metadata(location)
    skip_group_names = {
        normalize_group_name(group_name)
        for group_name in (skip_group_names or [])
    }
    selected_sandwich = selected_sandwich or {}

    for card in html.css("app-custom-checkbox-card-pdp"):
        if has_hidden_ancestor(card):
            continue

        name = first_child_text(card, ["h3"])
        if not name:
            continue

        container = nearest_combo_group_container(card)
        group_name = find_combo_group_name(container)
        if normalize_group_name(group_name) in skip_group_names:
            continue

        if group_name not in group_indexes:
            group_indexes[group_name] = len(group_indexes) + 1

        image_node = card.css_first("img")
        image = image_node.attributes.get("src") if image_node else None
        if image:
            image = image.replace("&amp;", "&")

        input_node = card.css_first("input")
        input_id = input_node.attributes.get("id") if input_node else None

        price_delta = Decimal("0.00")
        price_delta_display = "+$0.00"
        calories_delta = None
        calories_delta_display = None

        for detail in card.css("p"):
            detail_text = clean_text(detail.text())
            if not detail_text:
                continue

            (
                parsed_price_delta,
                parsed_price_delta_display,
                parsed_calories_delta,
                parsed_calories_delta_display,
            ) = parse_combo_detail_text(detail_text)

            if parsed_price_delta is not None:
                price_delta = parsed_price_delta
                price_delta_display = parsed_price_delta_display
            if parsed_calories_delta is not None:
                calories_delta = parsed_calories_delta
                calories_delta_display = parsed_calories_delta_display

        selected_by_default = any(
            "checked" in node_classes(label).split()
            for label in card.css("label")
        )

        row = {
            "store_name": location.get("name"),
            "store_street": location.get("street"),
            "store_city": location.get("city"),
            "store_state": location.get("state"),
            "store_zip_code": location.get("zip_code"),
            "order_url": location.get("order_url"),
            "classic_combo_url": classic_combo_url,
            "restaurant_id": combo_item.get("restaurant_id") or menu_metadata.get("restaurant_id"),
            "location": combo_item.get("location") or menu_metadata.get("location"),
            "classic_combo_product_id": combo_item.get("product_id"),
            "classic_combo_chainproductid": (
                combo_item.get("chainproductid")
                or CLASSIC_COMBO_FALLBACK_CHAINPRODUCTID
            ),
            "row_type": "option",
            "classic_combo_price": combo_item.get("price"),
            "classic_combo_price_display": combo_item.get("price_display"),
            "classic_combo_available": combo_item.get("available"),
            "detail_status": "detail_options",
            "group_index": group_indexes[group_name],
            "group_name": group_name,
            "group_requirement": find_combo_group_requirement(container),
            "selected_sandwich": selected_sandwich.get("item_name"),
            "selected_sandwich_slug": selected_sandwich.get("item_slug"),
            "selected_sandwich_price_delta": selected_sandwich.get("price_delta"),
            "selected_sandwich_price_delta_display": selected_sandwich.get("price_delta_display"),
            "item_name": name,
            "item_slug": slugify(name),
            "input_id": input_id,
            "price_delta": price_delta,
            "price_delta_display": price_delta_display,
            "calories_delta": calories_delta,
            "calories_delta_display": calories_delta_display,
            "image": image,
            "selected_by_default": selected_by_default,
        }
        row = clean_classic_combo_row(row)

        key = (
            row["selected_sandwich_slug"],
            row["group_name"],
            row["item_name"],
            row["price_delta_display"],
            row["calories_delta_display"],
            row["image"],
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    return rows


def parse_milkshake_mixin_page(html, location, milkshake_url):
    rows = []
    seen = set()
    group_indexes = {}
    milkshake_item = get_milkshake_menu_item(location) or {}
    fallback_group_name = find_page_group_name(html, is_milkshake_mixin_group)

    for card in html.css("app-custom-checkbox-card-pdp"):
        if has_hidden_ancestor(card):
            continue

        name = first_child_text(card, ["h3"])
        if not name:
            continue

        container = nearest_combo_group_container(card)
        group_name = find_combo_group_name(container)
        if not is_milkshake_mixin_group(group_name):
            group_name = fallback_group_name or group_name

        if not is_milkshake_mixin_group(group_name):
            group_name = fallback_group_name or "Select Unlimited Mix-Ins"

        if group_name not in group_indexes:
            group_indexes[group_name] = len(group_indexes) + 1

        image_node = card.css_first("img")
        image = image_node.attributes.get("src") if image_node else None
        if image:
            image = image.replace("&amp;", "&")

        input_node = card.css_first("input")
        input_id = input_node.attributes.get("id") if input_node else None

        price_delta = Decimal("0.00")
        price_delta_display = "+$0.00"
        calories_delta = None
        calories_delta_display = None

        for detail in card.css("p"):
            detail_text = clean_text(detail.text())
            if not detail_text:
                continue

            (
                parsed_price_delta,
                parsed_price_delta_display,
                parsed_calories_delta,
                parsed_calories_delta_display,
            ) = parse_combo_detail_text(detail_text)

            if parsed_price_delta is not None:
                price_delta = parsed_price_delta
                price_delta_display = parsed_price_delta_display
            if parsed_calories_delta is not None:
                calories_delta = parsed_calories_delta
                calories_delta_display = parsed_calories_delta_display

        selected_by_default = any(
            "checked" in node_classes(label).split()
            for label in card.css("label")
        )

        row = {
            "store_name": location.get("name"),
            "store_street": location.get("street"),
            "store_city": location.get("city"),
            "store_state": location.get("state"),
            "store_zip_code": location.get("zip_code"),
            "order_url": location.get("order_url"),
            "milkshake_url": milkshake_url,
            "restaurant_id": milkshake_item.get("restaurant_id"),
            "location": milkshake_item.get("location"),
            "milkshake_product_id": milkshake_item.get("product_id"),
            "milkshake_chainproductid": milkshake_item.get("chainproductid"),
            "group_index": group_indexes[group_name],
            "group_name": group_name,
            "group_requirement": find_combo_group_requirement(container),
            "item_name": name,
            "item_slug": slugify(name),
            "input_id": input_id,
            "price_delta": price_delta,
            "price_delta_display": price_delta_display,
            "calories_delta": calories_delta,
            "calories_delta_display": calories_delta_display,
            "image": image,
            "selected_by_default": selected_by_default,
        }

        key = milkshake_mixin_row_key(row)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    return rows


async def click_classic_combo_card(tab, item_name):
    item_name_json = json.dumps(item_name)
    click_script = f"""
    (() => {{
        const itemName = {item_name_json};
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const classList = (node) => ((node && node.className) || "").toString().split(/\\s+/);
        const hasHiddenAncestor = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                if (classList(current).includes("hidden")) {{
                    return true;
                }}
            }}
            return false;
        }};
        const isTopLevelCard = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                const classes = classList(current);
                if (classes.includes("pdp-form-default__modifierGroup__combo-banner__nested-content")) {{
                    return false;
                }}
                if (classes.includes("pdp-form-default__modifierGroup__content")) {{
                    return true;
                }}
            }}
            return false;
        }};
        const cards = Array.from(document.querySelectorAll("app-custom-checkbox-card-pdp"));
        const card = cards.find((candidate) => {{
            const heading = candidate.querySelector("h3");
            return (
                heading
                && normalize(heading.textContent) === itemName
                && !hasHiddenAncestor(candidate)
                && isTopLevelCard(candidate)
            );
        }});

        if (!card) {{
            return false;
        }}

        const label = card.querySelector("label");
        const target = label || card;
        target.scrollIntoView({{block: "center", inline: "center"}});
        const input = card.querySelector("input");

        const clickTarget = (node) => {{
            if (!node) {{
                return false;
            }}

            for (const type of ["pointerdown", "mousedown", "mouseup", "click"]) {{
                node.dispatchEvent(new MouseEvent(type, {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                }}));
            }}

            if (typeof node.click === "function") {{
                node.click();
            }}

            return true;
        }};

        clickTarget(target);
        if (label && classList(label).includes("checked")) {{
            return true;
        }}

        clickTarget(input);
        return !!(label && classList(label).includes("checked"));
    }})();
    """
    clicked = await run_script_value(tab, click_script)

    if not clicked:
        print(f"Could not click Classic Combo option: {item_name}")
        return False

    selected_script = f"""
    (() => {{
        const itemName = {item_name_json};
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const classList = (node) => ((node && node.className) || "").toString().split(/\\s+/);
        const hasHiddenAncestor = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                if (classList(current).includes("hidden")) {{
                    return true;
                }}
            }}
            return false;
        }};
        const isTopLevelCard = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                const classes = classList(current);
                if (classes.includes("pdp-form-default__modifierGroup__combo-banner__nested-content")) {{
                    return false;
                }}
                if (classes.includes("pdp-form-default__modifierGroup__content")) {{
                    return true;
                }}
            }}
            return false;
        }};
        const cards = Array.from(document.querySelectorAll("app-custom-checkbox-card-pdp"));
        const card = cards.find((candidate) => {{
            const heading = candidate.querySelector("h3");
            return (
                heading
                && normalize(heading.textContent) === itemName
                && !hasHiddenAncestor(candidate)
                && isTopLevelCard(candidate)
            );
        }});
        const label = card && card.querySelector("label");
        return !!(label && classList(label).includes("checked"));
    }})();
    """

    selection_confirmed = False
    for _ in range(10):
        if await run_script_value(tab, selected_script):
            selection_confirmed = True
            break
        await asyncio.sleep(0.5)

    if not selection_confirmed:
        print(f"Clicked Classic Combo option; continuing after selection wait timed out: {item_name}")

    await asyncio.sleep(0.8)
    await run_script_value(tab, "window.scrollTo(0, document.body.scrollHeight); return true;")
    await asyncio.sleep(0.4)
    return clicked


async def get_classic_combo_dom_state(tab, item_name):
    item_name_json = json.dumps(item_name)
    state_script = f"""
    (() => {{
        const itemName = {item_name_json};
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const classList = (node) => ((node && node.className) || "").toString().split(/\\s+/);
        const hasHiddenAncestor = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                if (classList(current).includes("hidden")) {{
                    return true;
                }}
            }}
            return false;
        }};
        const isTopLevelCard = (node) => {{
            for (let current = node; current; current = current.parentElement) {{
                const classes = classList(current);
                if (classes.includes("pdp-form-default__modifierGroup__combo-banner__nested-content")) {{
                    return false;
                }}
                if (classes.includes("pdp-form-default__modifierGroup__content")) {{
                    return true;
                }}
            }}
            return false;
        }};

        const cards = Array.from(document.querySelectorAll("app-custom-checkbox-card-pdp"));
        const card = cards.find((candidate) => {{
            const heading = candidate.querySelector("h3");
            return (
                heading
                && normalize(heading.textContent) === itemName
                && !hasHiddenAncestor(candidate)
                && isTopLevelCard(candidate)
            );
        }});

        const label = card && card.querySelector("label");
        const visibleNestedCount = cards.filter(
            (candidate) => !hasHiddenAncestor(candidate) && !isTopLevelCard(candidate)
        ).length;

        return {{
            found: !!card,
            selected: !!(label && classList(label).includes("checked")),
            visible_nested_count: visibleNestedCount,
        }};
    }})();
    """
    return await run_script_value(tab, state_script)


async def wait_for_classic_combo_nested_content(tab, item_name, timeout_seconds=8):
    deadline = time.time() + timeout_seconds
    last_state = None

    while time.time() < deadline:
        last_state = await get_classic_combo_dom_state(tab, item_name)
        if (
            last_state
            and last_state.get("selected")
            and last_state.get("visible_nested_count", 0) > 0
        ):
            return last_state
        await asyncio.sleep(0.4)

    return last_state


async def extract_classic_combo_nested_items_from_tab(
    tab,
    location,
    classic_combo_url,
    sandwich,
    top_level_item_slugs,
):
    return [
        item
        for item in parse_classic_combo_page(
            HTMLParser(await tab.page_source),
            location,
            classic_combo_url,
            selected_sandwich=sandwich,
            skip_group_names=CLASSIC_COMBO_TOP_GROUPS,
        )
        if item.get("item_slug") not in top_level_item_slugs
    ]


async def capture_classic_combo_nested_items(
    tab,
    location,
    classic_combo_url,
    sandwich,
    top_level_item_slugs,
):
    last_state = None

    for attempt in range(2):
        if attempt:
            print(
                f"Retrying Classic Combo nested capture for "
                f"{location.get('name')} / {sandwich['item_name']}"
            )
            clicked = await click_classic_combo_card(tab, sandwich["item_name"])
            if not clicked:
                break

        last_state = await wait_for_classic_combo_nested_content(
            tab,
            sandwich["item_name"],
        )

        for _ in range(20):
            nested_items = await extract_classic_combo_nested_items_from_tab(
                tab,
                location,
                classic_combo_url,
                sandwich,
                top_level_item_slugs,
            )
            if nested_items:
                return nested_items
            await asyncio.sleep(0.4)

    if last_state:
        print(
            f"No nested Classic Combo rows captured for {location.get('name')} / "
            f"{sandwich['item_name']} "
            f"(selected={last_state.get('selected')}, "
            f"visible_nested_cards={last_state.get('visible_nested_count')})"
        )
    else:
        print(
            f"No nested Classic Combo rows captured for "
            f"{location.get('name')} / {sandwich['item_name']}"
        )

    return []


async def wait_for_order_option_cards(
    tab,
    location_name,
    page_url,
    browser,
    option_label,
    render_attempts,
):
    for attempt in range(1, render_attempts + 1):
        if await page_has_cloudflare_challenge_pydoll(tab):
            print(
                f"Cloudflare challenge detected while waiting for {option_label} cards "
                f"for {location_name} (attempt {attempt}/{render_attempts}); waiting..."
            )
            if not await wait_for_turnstile_clear(
                tab,
                f"{location_name} {option_label} cards",
                CHROME_SESSION_READY_WAIT_SECONDS,
            ):
                print(
                    f"Cloudflare did not clear waiting for cards for {location_name}; "
                    "trying helper."
                )
                helper_cleared = await clear_order_cloudflare_with_helper_pydoll(
                    browser, f"{location_name} {option_label} cards"
                )
                if not helper_cleared:
                    print(f"Helper failed for {location_name} {option_label} cards; giving up.")
                    return False
                await go_to_with_turnstile(
                    tab,
                    page_url,
                    f"{location_name} {option_label} post-helper",
                    timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                    activate_page=True,
                    use_cloudflare_bypass_wrapper=False,
                )

        option_cards = None
        try:
            option_cards = await tab.query(
                "app-custom-checkbox-card-pdp",
                timeout=20,
                raise_exc=False,
            )
        except Exception:
            option_cards = None

        if option_cards:
            await scroll_me(tab)
            await asyncio.sleep(1)
            return True

        print(
            f"{option_label} options did not render for {location_name} "
            f"(attempt {attempt}/{render_attempts})."
        )
        await activate_order_page(tab, f"{location_name} {option_label}", page_url)
        await asyncio.sleep(2)

        if attempt < render_attempts:
            await go_to_with_turnstile(
                tab,
                page_url,
                f"{location_name} {option_label} retry",
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                activate_page=True,
                use_cloudflare_bypass_wrapper=False,
            )

    print(f"{option_label} options never rendered for {location_name}.")
    return False


async def wait_for_classic_combo_cards(
    tab,
    location_name,
    classic_combo_url,
    browser,
    render_attempts=None,
):
    return await wait_for_order_option_cards(
        tab,
        location_name,
        classic_combo_url,
        browser,
        "Classic Combo",
        render_attempts or CLASSIC_COMBO_RENDER_ATTEMPTS,
    )


async def fetch_classic_combo_items(tab, location, browser):
    classic_combo_url = classic_combo_url_for_location(location)
    if not classic_combo_url:
        return []

    label = f"{location.get('name')} Classic Combo"
    render_attempts = classic_combo_render_attempts(location)

    async def scrape_detail_page(detail_tab, detail_label):
        try:
            print(f"Opening Classic Combo page: {classic_combo_url}")
            await go_to_with_turnstile(
                detail_tab,
                classic_combo_url,
                detail_label,
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                activate_page=True,
                use_cloudflare_bypass_wrapper=False,
            )

            if await page_has_cloudflare_challenge_pydoll(detail_tab):
                print(f"Cloudflare challenge on Classic Combo page for {location.get('name')}; waiting...")
                if not await wait_for_turnstile_clear(detail_tab, detail_label, CHROME_SESSION_READY_WAIT_SECONDS):
                    print(f"Cloudflare did not clear for {detail_label}; trying helper page.")
                    helper_cleared = await clear_order_cloudflare_with_helper_pydoll(browser, detail_label)
                    if not helper_cleared:
                        print(f"Helper did not clear Cloudflare for {detail_label}; skipping Classic Combo.")
                        return []
                    await go_to_with_turnstile(
                        detail_tab,
                        classic_combo_url,
                        f"{detail_label} post-helper",
                        timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                        activate_page=True,
                        use_cloudflare_bypass_wrapper=False,
                    )
                    if await page_has_cloudflare_challenge_pydoll(detail_tab):
                        print(f"Still blocked by Cloudflare after helper for {detail_label}; skipping.")
                        return []

            if not await wait_for_classic_combo_cards(
                detail_tab,
                location.get("name"),
                classic_combo_url,
                browser,
                render_attempts=render_attempts,
            ):
                product_rows = classic_combo_product_presence_rows(
                    location,
                    classic_combo_url,
                    "detail_options_not_rendered",
                )
                if product_rows:
                    print(
                        f"Classic Combo product is listed for {location.get('name')}; "
                        "detail option cards did not render."
                    )
                return product_rows

            base_items = [
                item for item in parse_classic_combo_page(
                    HTMLParser(await detail_tab.page_source),
                    location,
                    classic_combo_url,
                )
                if normalize_group_name(item.get("group_name")) in CLASSIC_COMBO_TOP_GROUPS
            ]
            sandwich_items = [
                item for item in base_items
                if normalize_group_name(item.get("group_name")) == "choose your sandwich"
            ]
            top_level_item_slugs = {
                item.get("item_slug")
                for item in base_items
                if item.get("item_slug")
            }

            nested_items = []
            for sandwich in sandwich_items:
                clicked = await click_classic_combo_card(detail_tab, sandwich["item_name"])
                if not clicked:
                    continue

                nested_items.extend(await capture_classic_combo_nested_items(
                    detail_tab,
                    location,
                    classic_combo_url,
                    sandwich,
                    top_level_item_slugs,
                ))

            classic_combo_items = dedupe_classic_combo_rows(base_items + nested_items)
            print(f"Classic Combo items: {len(classic_combo_items)}")
            return classic_combo_items
        except Exception as e:
            print(f"Failed to scrape Classic Combo page for {location.get('name')}: {e}")
            return classic_combo_product_presence_rows(
                location,
                classic_combo_url,
                "detail_error",
            )

    semaphore = classic_combo_detail_semaphore()
    if CLASSIC_COMBO_DETAIL_CONCURRENCY == 1:
        print(f"Waiting for Classic Combo detail slot: {location.get('name')}")
    async with semaphore:
        combo_timeout = classic_combo_timeout_seconds(location)
        primary_tab = tab
        primary_label = label
        fresh_primary_tab = None

        if CLASSIC_COMBO_FRESH_TAB_FIRST:
            try:
                print(
                    f"Opening Classic Combo for {location.get('name')} in a fresh tab "
                    "to avoid stale order-page hydration."
                )
                fresh_primary_tab = await browser.new_tab()
                await reset_order_client_state(
                    fresh_primary_tab,
                    f"{label} fresh-tab first attempt",
                )
                primary_tab = fresh_primary_tab
                primary_label = f"{label} fresh-tab first attempt"
            except Exception as e:
                print(
                    f"Could not open fresh Classic Combo tab for "
                    f"{location.get('name')}: {e}. Falling back to worker tab."
                )

        try:
            combo_items = await asyncio.wait_for(
                scrape_detail_page(primary_tab, primary_label),
                timeout=combo_timeout,
            )
        except asyncio.TimeoutError:
            print(
                f"Classic Combo scrape for {location.get('name')} exceeded "
                f"{combo_timeout}s after getting a detail slot."
            )
            return classic_combo_product_presence_rows(
                location,
                classic_combo_url,
                "detail_timeout",
            )
        finally:
            if fresh_primary_tab is not None:
                with suppress(Exception):
                    await fresh_primary_tab.close()

        if (
            combo_items
            and get_classic_combo_menu_item(location)
            and all(is_classic_combo_product_row(row) for row in combo_items)
            and (combo_items[0].get("detail_status") == "detail_options_not_rendered")
        ):
            fresh_tab = None
            try:
                print(
                    f"Classic Combo detail did not hydrate for {location.get('name')}; "
                    "retrying once in a fresh tab."
                )
                fresh_tab = await browser.new_tab()
                await reset_order_client_state(
                    fresh_tab,
                    f"{label} fresh-tab retry",
                )
                fresh_combo_items = await asyncio.wait_for(
                    scrape_detail_page(fresh_tab, f"{label} fresh-tab retry"),
                    timeout=combo_timeout,
                )
                if fresh_combo_items:
                    return fresh_combo_items
            except asyncio.TimeoutError:
                print(
                    f"Fresh-tab Classic Combo retry for {location.get('name')} "
                    f"exceeded {combo_timeout}s."
                )
            except Exception as e:
                print(
                    f"Fresh-tab Classic Combo retry failed for "
                    f"{location.get('name')}: {e}"
                )
            finally:
                if fresh_tab is not None:
                    with suppress(Exception):
                        await fresh_tab.close()

        return combo_items


async def wait_for_milkshake_mixin_cards(tab, location, milkshake_url, browser):
    location_name = location.get("name")
    for attempt in range(1, MILKSHAKE_RENDER_ATTEMPTS + 1):
        if await page_has_cloudflare_challenge_pydoll(tab):
            print(
                f"Cloudflare challenge detected while waiting for Milkshake mix-in cards "
                f"for {location_name} (attempt {attempt}/{MILKSHAKE_RENDER_ATTEMPTS}); waiting..."
            )
            if not await wait_for_turnstile_clear(
                tab,
                f"{location_name} Milkshake mix-in cards",
                CHROME_SESSION_READY_WAIT_SECONDS,
            ):
                print(
                    f"Cloudflare did not clear waiting for milkshake mix-ins for "
                    f"{location_name}; trying helper."
                )
                helper_cleared = await clear_order_cloudflare_with_helper_pydoll(
                    browser, f"{location_name} Milkshake mix-in cards"
                )
                if not helper_cleared:
                    print(f"Helper failed for {location_name} Milkshake mix-in cards; giving up.")
                    return []
                await go_to_with_turnstile(
                    tab,
                    milkshake_url,
                    f"{location_name} Milkshake post-helper",
                    timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                    activate_page=True,
                    use_cloudflare_bypass_wrapper=False,
                )

        await scroll_me(tab)
        await asyncio.sleep(1)

        rows = parse_milkshake_mixin_page(
            HTMLParser(await tab.page_source),
            location,
            milkshake_url,
        )
        if rows:
            return rows

        if await wait_for_five_guys_not_found(tab, 1.5):
            location["_milkshake_unavailable"] = True
            print(
                f"Milkshake page is not available for {location_name}; "
                "skipping mix-ins."
            )
            return []

        print(
            f"Milkshake mix-in options did not render for {location_name} "
            f"(attempt {attempt}/{MILKSHAKE_RENDER_ATTEMPTS})."
        )
        await activate_order_page(tab, f"{location_name} Milkshake mix-in", milkshake_url)
        await asyncio.sleep(2)

        if attempt < MILKSHAKE_RENDER_ATTEMPTS:
            await go_to_with_turnstile(
                tab,
                milkshake_url,
                f"{location_name} Milkshake mix-in retry",
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                activate_page=True,
                use_cloudflare_bypass_wrapper=False,
            )

    print(f"Milkshake mix-in options never rendered for {location_name}.")
    return []


async def fetch_milkshake_mixin_items(tab, location, browser):
    menu_json = location.get("_menu_json")
    if isinstance(menu_json, dict):
        mixins_from_menu_json = parse_milkshake_mixins_from_menu_json(menu_json, location)
        if mixins_from_menu_json:
            print(f"Milkshake mix-ins: {len(mixins_from_menu_json)} (from menu JSON)")
            return mixins_from_menu_json

        product = get_milkshake_product(menu_json)
        if product:
            option_group_count = len(product.get("optiongroups") or [])
            print(
                f"Milkshake menu JSON had 0 parsed rows for {location.get('name')} "
                f"(option groups: {option_group_count}); trying direct modifiers API."
            )

    milkshake_url = milkshake_url_for_location(location)
    if not milkshake_url:
        return []

    label = f"{location.get('name')} Milkshake"
    expected_detail_product_ids = milkshake_detail_product_ids(location)

    async def fetch_milkshake_detail_json_via_request():
        product_id = primary_milkshake_detail_product_id(location)
        modifiers_url = milkshake_modifiers_url(product_id)
        if not modifiers_url:
            return None

        try:
            response = await tab.request.get(modifiers_url)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(
                f"Direct milkshake modifiers request failed for "
                f"{location.get('name')}: {e}"
            )
            return None

        detail_payload = find_milkshake_detail_payload(payload)
        if detail_payload is not None:
            print(
                f"Captured milkshake detail JSON directly for "
                f"{location.get('name')}: {modifiers_url}"
            )
            return detail_payload

        print(
            f"Direct milkshake modifiers response for {location.get('name')} "
            f"did not contain mix-ins: {summarize_payload_shape(payload)}"
        )
        return None

    async def fetch_milkshake_detail_json():
        loop = asyncio.get_running_loop()
        detail_future = loop.create_future()
        callback_id = None
        matching_modifiers_responses = []
        body_read_fail_urls = []
        json_parse_fail_urls = []

        async def inspect_response(event):
            if detail_future.done():
                return

            params = event.get("params", {})
            response = params.get("response") or {}
            status = int(response.get("status") or 0)
            if status != 200:
                return

            response_url = response.get("url", "")
            response_product_id = product_id_from_modifiers_url(response_url)
            if not response_product_id:
                return

            if expected_detail_product_ids and response_product_id not in expected_detail_product_ids:
                return

            request_id = params.get("requestId")
            if not request_id:
                return

            if len(matching_modifiers_responses) < 5:
                matching_modifiers_responses.append(response_url)

            try:
                body = await tab.get_network_response_body(request_id)
            except Exception as e:
                if len(body_read_fail_urls) < 5:
                    body_read_fail_urls.append(
                        f"{response_url} [{type(e).__name__}]"
                    )
                return

            payload = load_json_response_body(body)
            if payload is None:
                if len(json_parse_fail_urls) < 5:
                    json_parse_fail_urls.append(response_url)
                return

            detail_payload = find_milkshake_detail_payload(payload)
            if detail_payload is not None:
                detail_future.set_result(
                    {
                        "detail_url": response_url,
                        "detail_json": detail_payload,
                    }
                )
                return

            if len(json_parse_fail_urls) < 5:
                json_parse_fail_urls.append(
                    (
                        f"{response_url} [{summarize_payload_shape(payload)}]"
                    )
                )

        try:
            if not tab.network_events_enabled:
                await tab.enable_network_events()
            callback_id = await tab.on("Network.responseReceived", inspect_response)

            print(f"Opening Milkshake page: {milkshake_url}")
            await go_to_with_turnstile(
                tab,
                milkshake_url,
                label,
                timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                activate_page=True,
                use_cloudflare_bypass_wrapper=False,
            )

            if await wait_for_five_guys_not_found(
                tab,
                MILKSHAKE_NOT_FOUND_WAIT_SECONDS,
            ):
                location["_milkshake_unavailable"] = True
                print(
                    f"Milkshake page is not available for {location.get('name')}; "
                    "skipping mix-ins."
                )
                return None

            if await page_has_cloudflare_challenge_pydoll(tab):
                print(f"Cloudflare challenge on Milkshake page for {location.get('name')}; waiting...")
                if not await wait_for_turnstile_clear(tab, label, CHROME_SESSION_READY_WAIT_SECONDS):
                    print(f"Cloudflare did not clear for {label}; trying helper page.")
                    helper_cleared = await clear_order_cloudflare_with_helper_pydoll(browser, label)
                    if not helper_cleared:
                        print(f"Helper did not clear Cloudflare for {label}; skipping Milkshake mix-ins.")
                        return None
                    await go_to_with_turnstile(
                        tab,
                        milkshake_url,
                        f"{label} post-helper",
                        timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                        activate_page=True,
                        use_cloudflare_bypass_wrapper=False,
                    )
                    if await wait_for_five_guys_not_found(
                        tab,
                        MILKSHAKE_NOT_FOUND_WAIT_SECONDS,
                    ):
                        location["_milkshake_unavailable"] = True
                        print(
                            f"Milkshake page is not available for {location.get('name')} "
                            "after helper; skipping mix-ins."
                        )
                        return None
                    if await page_has_cloudflare_challenge_pydoll(tab):
                        print(f"Still blocked by Cloudflare after helper for {label}; skipping.")
                        return None

            captured = await asyncio.wait_for(
                detail_future,
                timeout=MILKSHAKE_DETAIL_WAIT_SECONDS,
            )
            print(
                f"Captured milkshake detail JSON for {location.get('name')}: "
                f"{captured['detail_url']}"
            )
            return captured["detail_json"]
        except asyncio.TimeoutError:
            print(f"Timed out waiting for milkshake detail JSON for {location.get('name')}.")
            if expected_detail_product_ids:
                print(
                    f"Expected milkshake modifiers product ids for {location.get('name')}: "
                    + ", ".join(sorted(expected_detail_product_ids))
                )
            if matching_modifiers_responses:
                print(
                    f"Observed matching milkshake modifiers responses for {location.get('name')}: "
                    + " | ".join(matching_modifiers_responses[:5])
                )
            if body_read_fail_urls:
                print(
                    f"Could not read matching milkshake modifiers responses for {location.get('name')}: "
                    + " | ".join(body_read_fail_urls[:5])
                )
            if json_parse_fail_urls:
                print(
                    f"JSON parse failed for matching modifiers responses for {location.get('name')}: "
                    + " | ".join(json_parse_fail_urls[:5])
                )
            return None
        finally:
            if callback_id is not None:
                await tab.remove_callback(callback_id)

    async def fetch_milkshake_items_from_page():
        milkshake_detail_json = await fetch_milkshake_detail_json()
        if milkshake_detail_json:
            mixin_items = parse_milkshake_mixins_from_detail_json(
                milkshake_detail_json,
                location,
            )
            if mixin_items:
                print(f"Milkshake mix-ins: {len(mixin_items)} (from detail JSON)")
                return mixin_items
            print(
                f"Milkshake detail JSON was captured for {location.get('name')}, "
                "but no mix-ins were parsed; falling back to page scrape."
            )

        mixin_items = dedupe_milkshake_mixin_rows(
            await wait_for_milkshake_mixin_cards(
                tab,
                location,
                milkshake_url,
                browser,
            )
        )
        print(f"Milkshake mix-ins: {len(mixin_items)}")
        return mixin_items

    try:
        try:
            milkshake_detail_json = await asyncio.wait_for(
                fetch_milkshake_detail_json_via_request(),
                timeout=MILKSHAKE_DIRECT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            print(
                f"Direct milkshake modifiers request timed out for "
                f"{location.get('name')} after {MILKSHAKE_DIRECT_TIMEOUT_SECONDS}s."
            )
            milkshake_detail_json = None

        if milkshake_detail_json:
            mixin_items = parse_milkshake_mixins_from_detail_json(
                milkshake_detail_json,
                location,
            )
            if mixin_items:
                print(f"Milkshake mix-ins: {len(mixin_items)} (from direct detail JSON)")
                return mixin_items
            print(
                f"Direct milkshake detail JSON was captured for {location.get('name')}, "
                "but no mix-ins were parsed; trying rendered page fallback."
            )

        try:
            return await asyncio.wait_for(
                fetch_milkshake_items_from_page(),
                timeout=MILKSHAKE_PAGE_FALLBACK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            print(
                f"Milkshake page fallback timed out for {location.get('name')} "
                f"after {MILKSHAKE_PAGE_FALLBACK_TIMEOUT_SECONDS}s."
            )
            return []
    except Exception as e:
        print(f"Failed to scrape Milkshake page for {location.get('name')}: {e}")
        return []


def extract_menu_json_url_from_html(html_text):
    if not html_text:
        return None

    patterns = (
        r"https://order\.fiveguys\.com/restaurants/\d+/menu(?:\?[^\"'\s<]+)?",
        r"/restaurants/\d+/menu(?:\?[^\"'\s<]+)?",
    )

    for pattern in patterns:
        match = re.search(pattern, html_text)
        if not match:
            continue

        menu_url = match.group(0).replace("&amp;", "&")
        if menu_url.startswith("/"):
            menu_url = urljoin(CHROME_START_URL, menu_url)
        return menu_url

    return None


async def extract_menu_json_url_from_runtime(tab):
    runtime_script = """
    (() => {
        const urls = [];
        const seen = new Set();
        const add = (value) => {
            if (!value || seen.has(value)) {
                return;
            }
            seen.add(value);
            urls.push(value);
        };

        try {
            for (const entry of performance.getEntriesByType("resource")) {
                if (entry && entry.name) {
                    add(entry.name);
                }
            }
        } catch (e) {}

        try {
            const pattern = /https:\\/\\/order\\.fiveguys\\.com\\/restaurants\\/\\d+\\/menu(?:\\?[^"'\\s<]+)?|\\/restaurants\\/\\d+\\/menu(?:\\?[^"'\\s<]+)?/g;
            for (const script of Array.from(document.scripts || [])) {
                const text = script.textContent || "";
                const matches = text.match(pattern) || [];
                for (const match of matches) {
                    add(match);
                }
            }
        } catch (e) {}

        return urls;
    })();
    """

    try:
        urls = await run_script_value(tab, runtime_script)
    except Exception:
        urls = None

    if not isinstance(urls, list):
        return None

    for value in urls:
        menu_url = extract_menu_json_url_from_html(value)
        if menu_url:
            return menu_url

    return None


async def fetch_menu_json_via_browser_request(tab, menu_url, order_url, label):
    response = await tab.request.get(menu_url)
    response.raise_for_status()
    menu_json = response.json()
    if menu_matches_order_url(menu_json, order_url):
        restaurant_id = (menu_json.get("restaurant") or {}).get("id")
        register_known_restaurant_id(order_url, restaurant_id)
        print(f"Fetched menu JSON via browser-context request for {label}.")
        return menu_json
    raise ValueError(f"Browser-context request returned mismatched menu for {label}.")


async def resolve_menu_from_loaded_page_html(
    tab,
    browser,
    order_url,
    label,
    menu_future,
    seen_menus,
):
    deadline = time.time() + ORDER_MENU_HTML_FALLBACK_WAIT_SECONDS
    announced_menu_url = None
    mismatch_counts = {}
    stale_state_reset_used = False
    stalled_polls = 0
    reactivation_count = 0

    while not menu_future.done() and time.time() < deadline:
        if await page_has_cloudflare_challenge_pydoll(tab):
            stalled_polls = 0
            await asyncio.sleep(ORDER_MENU_HTML_FALLBACK_POLL_SECONDS)
            continue

        if await page_looks_blank_pydoll(tab):
            stalled_polls += 1
            reactivation_count = await reactivate_order_page_if_stalled(
                tab,
                label,
                order_url,
                stalled_polls,
                reactivation_count,
            )
            await asyncio.sleep(ORDER_MENU_HTML_FALLBACK_POLL_SECONDS)
            continue

        try:
            html_text = await tab.page_source
        except Exception:
            html_text = None

        menu_url = extract_menu_json_url_from_html(html_text)
        if not menu_url:
            menu_url = await extract_menu_json_url_from_runtime(tab)
        if not menu_url:
            stalled_polls += 1
            reactivation_count = await reactivate_order_page_if_stalled(
                tab,
                label,
                order_url,
                stalled_polls,
                reactivation_count,
            )
            await asyncio.sleep(ORDER_MENU_HTML_FALLBACK_POLL_SECONDS)
            continue
        stalled_polls = 0

        if menu_url != announced_menu_url:
            print(f"Discovered menu endpoint in loaded page for {label}: {menu_url}")
            announced_menu_url = menu_url

        seen_menus.append(menu_url)
        try:
            menu_json = await fetch_menu_json_via_browser_request(
                tab,
                menu_url,
                order_url,
                label,
            )
        except Exception as e:
            error_text = str(e)
            if "mismatched menu" in error_text.lower():
                mismatch_counts[menu_url] = mismatch_counts.get(menu_url, 0) + 1
                print(
                    f"Loaded-page browser-context request failed for {label}: {e} "
                    f"(attempt {mismatch_counts[menu_url]}/3)"
                )

                if mismatch_counts[menu_url] >= 3:
                    if stale_state_reset_used:
                        print(
                            f"Loaded page still resolves to the wrong store for {label} "
                            "after clearing order app state; giving up on this menu."
                        )
                        if not menu_future.done():
                            menu_future.set_result(None)
                        return

                    stale_state_reset_used = True
                    print(
                        f"Loaded page keeps resolving to the wrong store for {label}; "
                        "clearing stale order app state and reloading the target page."
                    )
                    await reset_order_client_state(tab, label)
                    await go_to_with_turnstile(
                        tab,
                        order_url,
                        f"{label} state-reset reload",
                        timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                        use_cloudflare_bypass_wrapper=False,
                    )
                    announced_menu_url = None
                    mismatch_counts.clear()
                    await asyncio.sleep(2)
                    continue
            else:
                print(f"Loaded-page browser-context request failed for {label}: {e}")
            await asyncio.sleep(ORDER_MENU_HTML_FALLBACK_POLL_SECONDS)
            continue

        if not menu_future.done():
            menu_future.set_result(
                {
                    "source": "browser_request",
                    "menu_url": menu_url,
                    "menu_json": menu_json,
                }
            )
        return


async def fetch_menu_json_pydoll(tab, browser, order_url):
    order_url = canonical_order_menu_url(order_url) or order_url
    expected_slug = extract_order_slug(order_url)
    await reset_order_client_state(tab, expected_slug or order_url)
    known_restaurant_id = get_known_restaurant_id(order_url)
    direct_menu_url = None
    if known_restaurant_id:
        direct_menu_url = build_direct_menu_json_url(order_url, known_restaurant_id)
        try:
            print(
                f"Using known restaurant_id {known_restaurant_id} for "
                f"{expected_slug or order_url}."
            )
            return await fetch_menu_json_via_browser_request(
                tab,
                direct_menu_url,
                order_url,
                expected_slug or order_url,
            )
        except Exception as e:
            print(
                f"Known restaurant_id request failed for {expected_slug or order_url}: {e}. "
                "Falling back to page/network discovery."
            )

    loop = asyncio.get_running_loop()
    menu_future = loop.create_future()
    seen_menus = []
    callback_id = None
    watchdog_task = None
    loaded_page_fallback_task = None

    async def inspect_response(event):
        if menu_future.done():
            return

        params = event.get("params", {})
        response = params.get("response") or {}
        response_url = response.get("url", "")
        if "/restaurants/" not in response_url or "/menu" not in response_url:
            return

        status = int(response.get("status") or 0)
        if status != 200:
            print(f"Menu JSON failed: {status} {response_url}")
            return

        request_id = params.get("requestId")
        if not request_id:
            return

        try:
            body = await tab.get_network_response_body(request_id)
            menu_json = json.loads(body)
        except Exception:
            return

        candidates = sorted(restaurant_slug_candidates(menu_json))
        seen_menus.append(", ".join(candidates) or response_url)

        if menu_matches_order_url(menu_json, order_url):
            if not menu_future.done():
                menu_future.set_result(
                    {
                        "source": "network",
                        "menu_url": response_url,
                        "menu_json": menu_json,
                    }
                )
            return

        print(f"Ignored menu JSON for {candidates or 'unknown store'} while waiting for {expected_slug}")

    try:
        if not tab.network_events_enabled:
            await tab.enable_network_events()
        callback_id = await tab.on("Network.responseReceived", inspect_response)

        print("Opening order page with automatic Cloudflare handling.")
        await go_to_with_turnstile(
            tab,
            order_url,
            expected_slug or order_url,
            timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
            activate_page=True,
            use_cloudflare_bypass_wrapper=False,
        )

        if await page_has_cloudflare_challenge_pydoll(tab):
            print(
                f"Cloudflare challenge on order page for {expected_slug or order_url}; waiting..."
            )
            if not await wait_for_turnstile_clear(
                tab,
                expected_slug or order_url,
                CHROME_SESSION_READY_WAIT_SECONDS,
            ):
                if not ORDER_CLOUDFLARE_HELPER_ENABLED:
                    print(
                        f"Cloudflare did not clear for {expected_slug or order_url}; "
                        "skipping menu capture so this store can retry with a fresh browser."
                    )
                    return None

                print(
                    f"Cloudflare did not clear for {expected_slug or order_url}; "
                    "trying helper page."
                )
                helper_cleared = await clear_order_cloudflare_with_helper_pydoll(
                    browser,
                    expected_slug or order_url,
                )
                if not helper_cleared:
                    print(
                        f"Helper did not clear Cloudflare for {expected_slug or order_url}; "
                        "skipping menu capture."
                    )
                    return None

                await go_to_with_turnstile(
                    tab,
                    order_url,
                    f"{expected_slug or order_url} post-helper",
                    timeout_seconds=ORDER_NAVIGATION_TIMEOUT_SECONDS,
                    activate_page=True,
                    use_cloudflare_bypass_wrapper=False,
                )
                if await page_has_cloudflare_challenge_pydoll(tab):
                    print(
                        f"Still blocked by Cloudflare after helper for "
                        f"{expected_slug or order_url}; skipping."
                    )
                    return None

        if direct_menu_url:
            for attempt in range(1, 4):
                try:
                    print(
                        f"Retrying known restaurant_id request for "
                        f"{expected_slug or order_url} (attempt {attempt}/3)."
                    )
                    return await fetch_menu_json_via_browser_request(
                        tab,
                        direct_menu_url,
                        order_url,
                        expected_slug or order_url,
                    )
                except Exception as e:
                    print(
                        f"Post-navigation known restaurant_id request failed for "
                        f"{expected_slug or order_url} on attempt {attempt}/3: {e}"
                    )
                    if attempt < 3:
                        await asyncio.sleep(2)

        watchdog_task = asyncio.create_task(
            reload_blank_order_page_until_done_pydoll(
                tab,
                browser,
                menu_future,
                expected_slug or order_url,
                order_url,
            )
        )
        loaded_page_fallback_task = asyncio.create_task(
            resolve_menu_from_loaded_page_html(
                tab,
                browser,
                order_url,
                expected_slug or order_url,
                menu_future,
                seen_menus,
            )
        )
        captured = await asyncio.wait_for(menu_future, timeout=ORDER_MENU_WAIT_SECONDS)
        if not captured:
            return None

        source = captured.get("source")
        menu_url = captured["menu_url"]
        captured_menu_json = captured["menu_json"]

        if source == "browser_request":
            return captured_menu_json

        try:
            return await fetch_menu_json_via_browser_request(
                tab,
                menu_url,
                order_url,
                expected_slug,
            )
        except Exception as e:
            print(
                f"Browser-context request failed for {expected_slug}: {e}. "
                "Using the captured network response."
            )

        return captured_menu_json
    except asyncio.TimeoutError:
        try:
            fallback_menu_url = extract_menu_json_url_from_html(await tab.page_source)
        except Exception:
            fallback_menu_url = None

        if fallback_menu_url:
            try:
                return await fetch_menu_json_via_browser_request(
                    tab,
                    fallback_menu_url,
                    order_url,
                    expected_slug,
                )
            except Exception as e:
                print(f"Fallback browser-context request failed for {expected_slug}: {e}")

        seen = "; ".join(dict.fromkeys(seen_menus)) or "no menu JSON responses"
        print(f"Timed out waiting for menu JSON matching {expected_slug}. Saw: {seen}")
        return None
    except Exception as e:
        print(f"Failed to capture menu JSON from {order_url}: {e}")
        return None
    finally:
        if watchdog_task:
            watchdog_task.cancel()
        if loaded_page_fallback_task:
            loaded_page_fallback_task.cancel()
        if callback_id is not None:
            await tab.remove_callback(callback_id)


def location_csv_field_names():
    return [
        field.name
        for field in fields(FiveGuysLocation)
        if field.name not in ("menu", "reviews")
    ]


def location_csv_key(location):
    return (
        clean_text(location.get("order_url"))
        or clean_text(location.get("google_maps_cid"))
        or "|".join(
            filter(
                None,
                (
                    clean_text(location.get("name")),
                    clean_text(location.get("street")),
                    clean_text(location.get("zip_code")),
                ),
            )
        )
    )


def reset_locations_csv():
    global LOCATION_CSV_WRITTEN_KEYS
    LOCATION_CSV_WRITTEN_KEYS = set()
    with open(LOCATIONS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, location_csv_field_names())
        writer.writeheader()


def append_location_to_csv(location):
    key = location_csv_key(location)
    if not key:
        return

    field_names = location_csv_field_names()
    with LOCATION_CSV_APPEND_LOCK:
        if key in LOCATION_CSV_WRITTEN_KEYS:
            return
        LOCATION_CSV_WRITTEN_KEYS.add(key)

        with open(LOCATIONS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, field_names)
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow({
                field_name: serialize_csv_value(location.get(field_name))
                for field_name in field_names
            })
            f.flush()


def export_locations_to_csv(locations):
    field_names = location_csv_field_names()
    with open(LOCATIONS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, field_names)
        writer.writeheader()
        for location in locations:
            row = {}
            for field_name in field_names:
                value = location.get(field_name)
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, default=str)
                row[field_name] = value
            writer.writerow(row)
    print("saved locations to csv")


def export_locations_to_json(locations):
    field_names = [
        field.name
        for field in fields(FiveGuysLocation)
        if field.name not in ("menu", "reviews")
    ]
    rows = [
        {
            field_name: location.get(field_name)
            for field_name in field_names
        }
        for location in locations
    ]

    with open(LOCATIONS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4, default=str)

    print("saved locations to json")


MENU_CSV_FIELDS = [
    "store_name",
    "store_street",
    "store_city",
    "store_state",
    "store_zip_code",
    "order_url",
    "restaurant_id",
    "location",
    "category",
    "category_slug",
    "name",
    "slug",
    "product_id",
    "chainproductid",
    "price",
    "price_display",
    "base_price",
    "base_price_display",
    "min_price",
    "max_price",
    "price_range_display",
    "price_type",
    "pricing_note",
    "option_groups",
    "price_override",
    "base_calories",
    "max_calories",
    "calories",
    "description",
    "image",
    "available",
    "has_modifiers",
    "unavailable_handoff_modes",
]


CLASSIC_COMBO_CSV_FIELDS = [
    "store_name",
    "store_street",
    "store_city",
    "store_state",
    "store_zip_code",
    "order_url",
    "classic_combo_url",
    "restaurant_id",
    "location",
    "classic_combo_product_id",
    "classic_combo_chainproductid",
    "row_type",
    "classic_combo_price",
    "classic_combo_price_display",
    "classic_combo_available",
    "detail_status",
    "group_index",
    "group_name",
    "group_requirement",
    "selected_sandwich",
    "selected_sandwich_slug",
    "selected_sandwich_price_delta",
    "selected_sandwich_price_delta_display",
    "item_name",
    "item_slug",
    "input_id",
    "price_delta",
    "price_delta_display",
    "calories_delta",
    "calories_delta_display",
    "image",
    "selected_by_default",
]

MILKSHAKE_MIXIN_CSV_FIELDS = [
    "store_name",
    "store_street",
    "store_city",
    "store_state",
    "store_zip_code",
    "order_url",
    "milkshake_url",
    "restaurant_id",
    "location",
    "milkshake_product_id",
    "milkshake_chainproductid",
    "group_index",
    "group_name",
    "group_requirement",
    "item_name",
    "item_slug",
    "input_id",
    "price_delta",
    "price_delta_display",
    "calories_delta",
    "calories_delta_display",
    "image",
    "selected_by_default",
]


GOOGLE_REVIEW_CSV_FIELDS = [
    "store_name",
    "store_street",
    "store_city",
    "store_state",
    "store_zip_code",
    "google_maps_cid",
    "google_maps_url",
    "location_rating",
    "location_review_count",
    "review_rank",
    "review_id",
    "author_name",
    "author_url",
    "author_info",
    "review_rating",
    "relative_date",
    "review_text",
]


SCRAPE_FAILURE_CSV_FIELDS = [
    "store_name",
    "url",
    "stage",
    "reason",
]


def read_csv_dicts(path):
    path = Path(path)
    if not path.exists():
        return []

    with open(path, "r", newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if isinstance(row, dict)]


def serialize_csv_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


def classic_combo_detail_semaphore():
    global CLASSIC_COMBO_DETAIL_SEMAPHORE
    if CLASSIC_COMBO_DETAIL_SEMAPHORE is None:
        CLASSIC_COMBO_DETAIL_SEMAPHORE = asyncio.Semaphore(
            CLASSIC_COMBO_DETAIL_CONCURRENCY
        )
    return CLASSIC_COMBO_DETAIL_SEMAPHORE


def is_classic_combo_product_row(row):
    return (row or {}).get("row_type") == "product"


def classic_combo_item_rows(location):
    return [
        row
        for row in location.get("classic_combo_items") or []
        if not is_classic_combo_product_row(row)
    ]


def menu_csv_key(location):
    return clean_text(location.get("order_url")) or location_csv_key(location)


def reset_menu_csv():
    global MENU_CSV_WRITTEN_KEYS
    MENU_CSV_WRITTEN_KEYS = set()
    with open(MENU_ITEMS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, MENU_CSV_FIELDS)
        writer.writeheader()


def append_menu_to_csv(location):
    rows = location.get("menu") or []
    if not rows:
        return

    key = menu_csv_key(location)
    if not key:
        return

    with MENU_CSV_APPEND_LOCK:
        if key in MENU_CSV_WRITTEN_KEYS:
            return
        MENU_CSV_WRITTEN_KEYS.add(key)

        with open(MENU_ITEMS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, MENU_CSV_FIELDS)
            if f.tell() == 0:
                writer.writeheader()

            for item in rows:
                row = {
                    "store_name": location.get("name"),
                    "store_street": location.get("street"),
                    "store_city": location.get("city"),
                    "store_state": location.get("state"),
                    "store_zip_code": location.get("zip_code"),
                    "order_url": location.get("order_url"),
                }
                for field_name in MENU_CSV_FIELDS:
                    if field_name not in row:
                        row[field_name] = serialize_csv_value(item.get(field_name))
                writer.writerow(row)
            f.flush()


def reset_scrape_failures_csv():
    with open(SCRAPE_FAILURES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, SCRAPE_FAILURE_CSV_FIELDS)
        writer.writeheader()


def append_scrape_failure_to_csv(store_name, url, stage, reason):
    with SCRAPE_FAILURE_CSV_APPEND_LOCK:
        with open(SCRAPE_FAILURES_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, SCRAPE_FAILURE_CSV_FIELDS)
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow({
                "store_name": store_name,
                "url": url,
                "stage": stage,
                "reason": shorten_debug_text(reason, limit=500),
            })
            f.flush()


def write_scrape_failures_csv(rows):
    with SCRAPE_FAILURE_CSV_APPEND_LOCK:
        with open(SCRAPE_FAILURES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, SCRAPE_FAILURE_CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field_name: serialize_csv_value(row.get(field_name))
                    for field_name in SCRAPE_FAILURE_CSV_FIELDS
                })


def prime_incremental_csv_duplicate_guards():
    global LOCATION_CSV_WRITTEN_KEYS, MENU_CSV_WRITTEN_KEYS

    LOCATION_CSV_WRITTEN_KEYS = {
        key
        for key in (
            location_csv_key(row)
            for row in read_csv_dicts(LOCATIONS_CSV_PATH)
        )
        if key
    }
    MENU_CSV_WRITTEN_KEYS = {
        key
        for key in (
            menu_csv_key({"order_url": row.get("order_url")})
            for row in read_csv_dicts(MENU_ITEMS_CSV_PATH)
        )
        if key
    }


def reset_classic_combo_csv():
    with open(CLASSIC_COMBO_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, CLASSIC_COMBO_CSV_FIELDS)
        writer.writeheader()


def append_classic_combo_to_csv(location):
    rows = classic_combo_item_rows(location)
    if not rows:
        return

    with CLASSIC_COMBO_CSV_APPEND_LOCK:
        with open(CLASSIC_COMBO_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, CLASSIC_COMBO_CSV_FIELDS)
            if f.tell() == 0:
                writer.writeheader()

            for row in rows:
                writer.writerow({
                    field_name: serialize_csv_value(row.get(field_name))
                    for field_name in CLASSIC_COMBO_CSV_FIELDS
                })
                f.flush()


def reset_milkshake_mixins_csv():
    with open(MILKSHAKE_MIXIN_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, MILKSHAKE_MIXIN_CSV_FIELDS)
        writer.writeheader()


def append_milkshake_mixins_to_csv(location):
    rows = location.get("milkshake_mixin_items") or []
    if not rows:
        return

    with MILKSHAKE_MIXIN_CSV_APPEND_LOCK:
        with open(MILKSHAKE_MIXIN_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, MILKSHAKE_MIXIN_CSV_FIELDS)
            if f.tell() == 0:
                writer.writeheader()

            for row in rows:
                writer.writerow({
                    field_name: serialize_csv_value(row.get(field_name))
                    for field_name in MILKSHAKE_MIXIN_CSV_FIELDS
                })
                f.flush()


def reset_google_reviews_csv():
    with open(GOOGLE_REVIEWS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, GOOGLE_REVIEW_CSV_FIELDS)
        writer.writeheader()


def append_google_reviews_to_csv(location):
    rows = location.get("reviews") or []
    if not rows:
        return

    with GOOGLE_REVIEW_CSV_APPEND_LOCK:
        with open(GOOGLE_REVIEWS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, GOOGLE_REVIEW_CSV_FIELDS)
            if f.tell() == 0:
                writer.writeheader()

            for row in rows:
                writer.writerow({
                    field_name: serialize_csv_value(row.get(field_name))
                    for field_name in GOOGLE_REVIEW_CSV_FIELDS
                })
                f.flush()


def export_classic_combo_to_csv(locations):
    with open(CLASSIC_COMBO_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, CLASSIC_COMBO_CSV_FIELDS)
        writer.writeheader()

        for location in locations:
            for item in classic_combo_item_rows(location):
                writer.writerow({
                    field_name: serialize_csv_value(item.get(field_name))
                    for field_name in CLASSIC_COMBO_CSV_FIELDS
                })

    print("saved classic combo items to csv")


def export_classic_combo_to_json(locations):
    rows = []
    for location in locations:
        for item in classic_combo_item_rows(location):
            rows.append({
                field_name: item.get(field_name)
                for field_name in CLASSIC_COMBO_CSV_FIELDS
            })

    with open(CLASSIC_COMBO_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4, default=str)

    print("saved classic combo items to json")


def export_milkshake_mixins_to_csv(locations):
    with open(MILKSHAKE_MIXIN_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, MILKSHAKE_MIXIN_CSV_FIELDS)
        writer.writeheader()

        for location in locations:
            for item in location.get("milkshake_mixin_items") or []:
                writer.writerow({
                    field_name: serialize_csv_value(item.get(field_name))
                    for field_name in MILKSHAKE_MIXIN_CSV_FIELDS
                })

    print("saved milkshake mix-in items to csv")


def export_milkshake_mixins_to_json(locations):
    rows = []
    for location in locations:
        for item in location.get("milkshake_mixin_items") or []:
            rows.append({
                field_name: item.get(field_name)
                for field_name in MILKSHAKE_MIXIN_CSV_FIELDS
            })

    with open(MILKSHAKE_MIXIN_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4, default=str)

    print("saved milkshake mix-in items to json")


def export_google_reviews_to_csv(locations):
    with open(GOOGLE_REVIEWS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, GOOGLE_REVIEW_CSV_FIELDS)
        writer.writeheader()

        for location in locations:
            for review in location.get("reviews") or []:
                writer.writerow({
                    field_name: serialize_csv_value(review.get(field_name))
                    for field_name in GOOGLE_REVIEW_CSV_FIELDS
                })

    print("saved google reviews to csv")


def export_google_reviews_to_json(locations):
    rows = []
    for location in locations:
        for review in location.get("reviews") or []:
            rows.append({
                field_name: review.get(field_name)
                for field_name in GOOGLE_REVIEW_CSV_FIELDS
            })

    with open(GOOGLE_REVIEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4, default=str)

    print("saved google reviews to json")


def export_menu_to_csv(locations):
    field_names = MENU_CSV_FIELDS

    with open(MENU_ITEMS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, field_names)
        writer.writeheader()
        for location in locations:
            for item in location.get("menu") or []:
                row = {
                    "store_name": location.get("name"),
                    "store_street": location.get("street"),
                    "store_city": location.get("city"),
                    "store_state": location.get("state"),
                    "store_zip_code": location.get("zip_code"),
                    "order_url": location.get("order_url"),
                }
                for field_name in field_names:
                    if field_name not in row:
                        value = item.get(field_name)
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False, default=str)
                        row[field_name] = value
                writer.writerow(row)
    print("saved menu items to csv")


def export_menu_to_json(locations):
    rows = []

    for location in locations:
        for item in location.get("menu") or []:
            row = {
                "store_name": location.get("name"),
                "store_street": location.get("street"),
                "store_city": location.get("city"),
                "store_state": location.get("state"),
                "store_zip_code": location.get("zip_code"),
                "order_url": location.get("order_url"),
            }
            for field_name in MENU_CSV_FIELDS:
                if field_name not in row:
                    row[field_name] = item.get(field_name)
            rows.append(row)

    with open(MENU_ITEMS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4, default=str)

    print("saved menu items to json")


def load_json_list(path):
    path = Path(path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    return payload if isinstance(payload, list) else []


def stable_row_fingerprint(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)


def merge_json_rows(path, new_rows, key_func, label):
    new_rows = [row for row in new_rows if isinstance(row, dict)]
    if not new_rows:
        return

    rows = load_json_list(path)
    merged = []
    index_by_key = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        key = key_func(row) or ("row", stable_row_fingerprint(row))
        if key in index_by_key:
            merged[index_by_key[key]] = row
        else:
            index_by_key[key] = len(merged)
            merged.append(row)

    for row in new_rows:
        key = key_func(row) or ("row", stable_row_fingerprint(row))
        if key in index_by_key:
            merged[index_by_key[key]] = row
        else:
            index_by_key[key] = len(merged)
            merged.append(row)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4, default=str)

    print(f"merged {len(new_rows)} {label} into {path.name}")


def location_json_row(location):
    return {
        field_name: location.get(field_name)
        for field_name in location_csv_field_names()
    }


def menu_json_rows_for_location(location):
    rows = []
    for item in location.get("menu") or []:
        row = {
            "store_name": location.get("name"),
            "store_street": location.get("street"),
            "store_city": location.get("city"),
            "store_state": location.get("state"),
            "store_zip_code": location.get("zip_code"),
            "order_url": location.get("order_url"),
        }
        for field_name in MENU_CSV_FIELDS:
            if field_name not in row:
                row[field_name] = item.get(field_name)
        rows.append(row)
    return rows


def location_json_key(row):
    key = location_csv_key(row)
    return ("location", key) if key else None


def menu_json_key(row):
    order_url = clean_text(row.get("order_url"))
    product_id = clean_text(row.get("product_id"))
    chainproductid = clean_text(row.get("chainproductid"))
    category_slug = clean_text(row.get("category_slug"))
    slug = clean_text(row.get("slug"))
    name = clean_text(row.get("name"))
    if not any((order_url, product_id, chainproductid, category_slug, slug, name)):
        return None
    return ("menu", order_url, product_id, chainproductid, category_slug, slug, name)


def classic_combo_json_key(row):
    order_url = clean_text(row.get("order_url"))
    combo_url = clean_text(row.get("classic_combo_url"))
    selected_sandwich_slug = clean_text(row.get("selected_sandwich_slug"))
    group_index = clean_text(row.get("group_index"))
    group_name = clean_text(row.get("group_name"))
    item_slug = clean_text(row.get("item_slug"))
    input_id = clean_text(row.get("input_id"))
    item_name = clean_text(row.get("item_name"))
    if not any((order_url, combo_url, selected_sandwich_slug, group_name, item_slug, item_name)):
        return None
    return (
        "classic_combo",
        order_url,
        combo_url,
        selected_sandwich_slug,
        group_index,
        group_name,
        item_slug,
        input_id,
        item_name,
    )


def milkshake_json_key(row):
    order_url = clean_text(row.get("order_url"))
    milkshake_url = clean_text(row.get("milkshake_url"))
    group_index = clean_text(row.get("group_index"))
    group_name = clean_text(row.get("group_name"))
    item_slug = clean_text(row.get("item_slug"))
    input_id = clean_text(row.get("input_id"))
    item_name = clean_text(row.get("item_name"))
    if not any((order_url, milkshake_url, group_name, item_slug, item_name)):
        return None
    return (
        "milkshake",
        order_url,
        milkshake_url,
        group_index,
        group_name,
        item_slug,
        input_id,
        item_name,
    )


def google_review_json_key(row):
    review_id = clean_text(row.get("review_id"))
    if review_id:
        return ("review_id", review_id)

    cid = clean_text(row.get("google_maps_cid"))
    rank = clean_text(row.get("review_rank"))
    author = clean_text(row.get("author_name"))
    text = clean_text(row.get("review_text"))
    if not any((cid, rank, author, text)):
        return None
    return ("review", cid, rank, author, text)


def merge_recovered_output_json(recovered_locations):
    recovered_locations = [
        location for location in recovered_locations if isinstance(location, dict)
    ]
    if not recovered_locations:
        return

    merge_json_rows(
        LOCATIONS_JSON_PATH,
        [location_json_row(location) for location in recovered_locations],
        location_json_key,
        "locations",
    )
    merge_json_rows(
        MENU_ITEMS_JSON_PATH,
        [
            row
            for location in recovered_locations
            for row in menu_json_rows_for_location(location)
        ],
        menu_json_key,
        "menu rows",
    )
    merge_json_rows(
        CLASSIC_COMBO_JSON_PATH,
        [
            {field_name: item.get(field_name) for field_name in CLASSIC_COMBO_CSV_FIELDS}
            for location in recovered_locations
            for item in classic_combo_item_rows(location)
        ],
        classic_combo_json_key,
        "Classic Combo rows",
    )
    merge_json_rows(
        MILKSHAKE_MIXIN_JSON_PATH,
        [
            {field_name: item.get(field_name) for field_name in MILKSHAKE_MIXIN_CSV_FIELDS}
            for location in recovered_locations
            for item in location.get("milkshake_mixin_items") or []
        ],
        milkshake_json_key,
        "milkshake rows",
    )
    merge_json_rows(
        GOOGLE_REVIEWS_JSON_PATH,
        [
            {field_name: review.get(field_name) for field_name in GOOGLE_REVIEW_CSV_FIELDS}
            for location in recovered_locations
            for review in location.get("reviews") or []
        ],
        google_review_json_key,
        "Google review rows",
    )


def merge_recovered_locations_csv(recovered_locations):
    recovered_rows = [
        location_json_row(location)
        for location in recovered_locations
        if isinstance(location, dict)
    ]
    if not recovered_rows:
        return

    merged = []
    index_by_key = {}

    for row in read_csv_dicts(LOCATIONS_CSV_PATH):
        key = location_csv_key(row)
        if not key:
            continue
        if key in index_by_key:
            merged[index_by_key[key]] = row
        else:
            index_by_key[key] = len(merged)
            merged.append(row)

    for row in recovered_rows:
        key = location_csv_key(row)
        if not key:
            continue
        if key in index_by_key:
            merged[index_by_key[key]] = row
        else:
            index_by_key[key] = len(merged)
            merged.append(row)

    with open(LOCATIONS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, location_csv_field_names())
        writer.writeheader()
        for row in merged:
            writer.writerow({
                field_name: serialize_csv_value(row.get(field_name))
                for field_name in location_csv_field_names()
            })

    print(f"merged {len(recovered_rows)} recovered locations into locations.csv")


async def scroll_me(tab):
    previous_height = None
    while True:
        current_height = await run_script_value(tab, "return document.body.scrollHeight;")
        if current_height == previous_height:
            break
        previous_height = current_height
        await run_script_value(
            tab,
            "window.scrollTo(0, document.body.scrollHeight); return true;",
        )
        await asyncio.sleep(2)


def extract_google_maps_cid(google_maps_url):
    google_maps_url = clean_text(google_maps_url)
    if not google_maps_url:
        return None

    parsed_url = urlparse(google_maps_url)
    query = parse_qs(parsed_url.query)
    cid_values = query.get("cid") or query.get("lci")
    if cid_values:
        return clean_text(cid_values[0])

    match = re.search(r"(?:[?&]cid=|/cid/)(\d+)", google_maps_url)
    return match.group(1) if match else None


def force_google_maps_locale(google_maps_url):
    google_maps_url = clean_text(google_maps_url)
    if not google_maps_url:
        return None

    parsed_url = urlparse(google_maps_url)
    query = parse_qs(parsed_url.query, keep_blank_values=True)
    query["hl"] = [GOOGLE_MAPS_LANGUAGE]
    query["gl"] = [GOOGLE_MAPS_REGION]
    localized_url = parsed_url._replace(query=urlencode(query, doseq=True))
    return urlunparse(localized_url)


def google_maps_url_for_cid(cid):
    cid = clean_text(cid)
    if not cid:
        return None
    return force_google_maps_locale(f"https://www.google.com/maps?cid={cid}")


def google_maps_place_url_for_location(location):
    cid_url = google_maps_url_for_cid(location.get("google_maps_cid"))
    if cid_url:
        return cid_url

    google_maps_url = clean_text(location.get("google_maps_url"))
    if google_maps_url and "google." in urlparse(google_maps_url).netloc.lower():
        return force_google_maps_locale(google_maps_url)

    return None


def google_maps_expected_cid_hex(location):
    cid = clean_text(location.get("google_maps_cid"))
    if cid and cid.isdigit():
        return f"0x{int(cid):x}"
    return None


def google_maps_active_place_label_from_url(url):
    url = clean_text(url)
    if not url:
        return None

    parsed_url = urlparse(url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    try:
        place_index = path_parts.index("place")
    except ValueError:
        return None

    if place_index + 1 >= len(path_parts):
        return None

    return clean_text(unquote(path_parts[place_index + 1]).replace("+", " "))


def google_maps_label_looks_like_five_guys(value):
    return "five guys" in ((clean_text(value) or "").lower())


def google_maps_url_matches_location(url, location):
    url = clean_text(url)
    if not url:
        return False

    lowered_url = url.lower()
    cid = clean_text(location.get("google_maps_cid"))
    cid_hex = google_maps_expected_cid_hex(location)

    if cid and cid in lowered_url:
        return True
    if cid_hex and cid_hex.lower() in lowered_url:
        return google_maps_label_looks_like_five_guys(
            google_maps_active_place_label_from_url(url)
        )

    return False


async def google_maps_active_place_name(tab):
    active_name_script = """
    (() => {
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const heading = document.querySelector("h1.DUwDvf, h1");
        const ariaMain = document.querySelector("[role='main'] [aria-label]");
        return {
            heading: normalize(heading && (heading.innerText || heading.textContent)),
            aria: normalize(ariaMain && ariaMain.getAttribute("aria-label")),
            title: normalize(document.title),
            url_label: normalize(decodeURIComponent(
                ((window.location.pathname.match(/\\/place\\/([^/]+)/) || [])[1] || "")
                    .replace(/\\+/g, " ")
            )),
        };
    })();
    """

    try:
        active_name = await run_script_value(tab, active_name_script)
    except Exception:
        active_name = None

    return active_name if isinstance(active_name, dict) else {}


async def google_maps_tab_matches_location(tab, location):
    try:
        current_url = await tab.current_url
    except Exception:
        current_url = None

    active_name = await google_maps_active_place_name(tab)
    active_name_values = [
        active_name.get("heading"),
        active_name.get("title"),
        active_name.get("url_label"),
        google_maps_active_place_label_from_url(current_url),
    ]
    if not any(google_maps_label_looks_like_five_guys(value) for value in active_name_values):
        return False

    cid_hex = google_maps_expected_cid_hex(location)
    cid = clean_text(location.get("google_maps_cid"))
    current_url_lower = (current_url or "").lower()
    if cid and cid in current_url_lower:
        return True
    if cid_hex and cid_hex.lower() in current_url_lower:
        return True

    return False


def google_maps_reviews_url_from_href(href):
    href = clean_text(href)
    if not href:
        return None

    parsed_url = urlparse(href)
    if "google." not in parsed_url.netloc.lower():
        return None

    path = parsed_url.path
    if "/maps/place/" not in path or "/data=" not in path:
        return None

    if "!9m1!1b1" not in path:
        return None

    if not google_maps_label_looks_like_five_guys(
        google_maps_active_place_label_from_url(href)
    ):
        return None

    return force_google_maps_locale(urlunparse(parsed_url._replace(path=path)))


def google_maps_reviews_url_from_current_place_url(href, location):
    href = clean_text(href)
    if not href:
        return None

    if not google_maps_url_matches_location(href, location):
        return None

    parsed_url = urlparse(href)
    if "google." not in parsed_url.netloc.lower():
        return None

    path = parsed_url.path
    if "/maps/place/" not in path or "/data=" not in path:
        return None

    if not google_maps_label_looks_like_five_guys(
        google_maps_active_place_label_from_url(href)
    ):
        return None

    feature_match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", path, re.IGNORECASE)
    coords_match = re.search(
        r"!8m2!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)",
        path,
        re.IGNORECASE,
    )
    if not feature_match or not coords_match:
        return None

    feature_id = feature_match.group(1)
    latitude = coords_match.group(1)
    longitude = coords_match.group(2)
    cid_hex = google_maps_expected_cid_hex(location)
    if cid_hex and not feature_id.lower().endswith(f":{cid_hex.lower()}"):
        return None

    place_segment = quote("Five Guys").replace("%20", "+")
    extra_place_id = ""
    place_id_match = re.search(r"(!16s[^!?/]+)", path)
    if place_id_match:
        extra_place_id = place_id_match.group(1)

    reviews_path = (
        f"/maps/place/{place_segment}/@{latitude},{longitude},17z/"
        f"data=!4m8!3m7!1s{feature_id}!8m2!3d{latitude}!4d{longitude}"
        f"!9m1!1b1{extra_place_id}"
    )
    return force_google_maps_locale(urlunparse(parsed_url._replace(path=reviews_path)))


def google_maps_reviews_url_from_feature_id(location, feature_id, latitude, longitude):
    feature_id = clean_text(feature_id)
    latitude = clean_text(latitude)
    longitude = clean_text(longitude)
    if not feature_id or not latitude or not longitude:
        return None

    name = quote("Five Guys")
    url = (
        f"https://www.google.com/maps/place/{name}/@{latitude},{longitude},17z/"
        f"data=!4m8!3m7!1s{feature_id}!8m2!3d{latitude}!4d{longitude}!9m1!1b1"
    )
    return force_google_maps_locale(url)


async def build_google_maps_reviews_url_from_loaded_page(tab, location):
    try:
        href = await run_script_value(tab, "return window.location.href;")
    except Exception:
        href = None

    reviews_url = google_maps_reviews_url_from_href(href)
    if reviews_url:
        return reviews_url

    return google_maps_reviews_url_from_current_place_url(href, location)


def normalize_google_review_key(review):
    review_id = clean_text(review.get("review_id"))
    if review_id:
        return ("id", review_id)

    return (
        "fallback",
        clean_text(review.get("author_name")),
        clean_text(review.get("relative_date")),
        clean_text(review.get("review_text")),
        review.get("review_rating"),
    )


GOOGLE_OWNER_RESPONSE_TEXT_RE = re.compile(
    r"("
    r"^thank you so much for being our customer!?$"
    r"|^thank you for your rating\b"
    r"|taking the time to review this location"
    r"|provide us a more detailed experience"
    r"|fiveguys\.com/contact-us"
    r"|we appreciate the time you took to rate us"
    r"|thank you,\s*five guys\b"
    r")",
    re.IGNORECASE,
)


def is_google_owner_response_text(value):
    text = clean_text(value) or ""
    return bool(GOOGLE_OWNER_RESPONSE_TEXT_RE.search(text))


def should_keep_google_review(review):
    review_text = clean_text(review.get("review_text"))
    if GOOGLE_MAPS_REQUIRE_REVIEW_TEXT and not review_text:
        return False
    if review_text and is_google_owner_response_text(review_text):
        return False
    return True


async def accept_google_maps_consent(tab):
    consent_script = """
    (() => {
        const candidates = Array.from(document.querySelectorAll("button, div[role='button']"));
        const labels = [
            "accept all",
            "i agree",
            "accept",
            "agree",
            "t\\u00fcm\\u00fcn\\u00fc kabul et",
            "kabul ediyorum",
            "kabul et",
        ];

        for (const candidate of candidates) {
            const text = (candidate.innerText || candidate.textContent || "").trim().toLowerCase();
            const aria = (candidate.getAttribute("aria-label") || "").trim().toLowerCase();
            if (!text && !aria) {
                continue;
            }

            if (labels.some((label) => text === label || aria === label || text.includes(label))) {
                candidate.click();
                return text || aria;
            }
        }

        return null;
    })();
    """

    try:
        clicked = await run_script_value(tab, consent_script)
    except Exception:
        clicked = None

    if clicked:
        await asyncio.sleep(2)
        print(f"Accepted Google consent prompt with: {clicked}")


async def get_google_maps_summary(tab):
    summary_script = """
    (() => {
        const text = document.body ? document.body.innerText || "" : "";
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const normalizeCount = (value) => {
            if (!value) {
                return null;
            }
            const digits = value.replace(/[^0-9]/g, "");
            return digits ? Number(digits) : null;
        };
        const parseVisibleSummary = (value) => {
            const normalized = normalize(value);
            const match = normalized.match(
                /\\b([1-5][\\.,][0-9])\\s+([0-9][0-9,\\.]*)\\s+(?:reviews?|yorum)\\b/i
            );
            if (!match) {
                return null;
            }
            return {
                rating: Number(match[1].replace(",", ".")),
                review_count: normalizeCount(match[2]),
            };
        };

        let rating = null;
        let reviewCount = null;

        const visibleSummaryNodes = Array.from(document.querySelectorAll(
            "div[role='main'], div[aria-label], h1, h2, span, button"
        ));
        for (const node of visibleSummaryNodes) {
            const parsed = parseVisibleSummary(node.innerText || node.textContent);
            if (parsed) {
                rating = parsed.rating;
                reviewCount = parsed.review_count;
                break;
            }
        }

        if (rating === null || reviewCount === null) {
            const parsed = parseVisibleSummary(text);
            if (parsed) {
                rating = parsed.rating;
                reviewCount = parsed.review_count;
            }
        }

        for (const node of Array.from(document.querySelectorAll("[aria-label]"))) {
            const label = node.getAttribute("aria-label") || "";
            if (rating === null) {
                const isHistogramRow = /^\\s*[1-5]\\s*(?:stars?|star|y\\u0131ld\\u0131z|yildiz)\\s*,\\s*[0-9]/i.test(label);
                const ratingMatch = !isHistogramRow && label.match(
                    /([1-5][\\.,][0-9])\\s*(?:stars?|star|y\\u0131ld\\u0131z|yildiz)/i
                );
                if (ratingMatch) {
                    rating = Number(ratingMatch[1].replace(",", "."));
                }
            }

            if (reviewCount === null) {
                const isHistogramRow = /^\\s*[1-5]\\s*(?:stars?|star|y\\u0131ld\\u0131z|yildiz)\\s*,\\s*[0-9]/i.test(label);
                const reviewMatch = !isHistogramRow && label.match(
                    /([0-9][0-9,\\.\\s]*)\\s+(?:reviews?|yorum)/i
                );
                if (reviewMatch) {
                    reviewCount = normalizeCount(reviewMatch[1]);
                }
            }
        }

        if (reviewCount === null) {
            const reviewMatch = text.match(/([0-9][0-9,\\.\\s]*)\\s+(?:reviews?|yorum)/i);
            if (reviewMatch) {
                reviewCount = normalizeCount(reviewMatch[1]);
            }
        }

        if (reviewCount === null) {
            const moreReviewsMatch = text.match(
                /(?:more\\s+reviews?|daha\\s+fazla\\s+yorum|yorumlar)\\s*\\(([0-9][0-9,\\.\\s]*)\\)/i
            );
            if (moreReviewsMatch) {
                reviewCount = normalizeCount(moreReviewsMatch[1]);
            }
        }

        if (reviewCount === null) {
            const ratingCountMatch = text.match(
                /\\b[0-9](?:[\\.,][0-9])?\\s*\\(([0-9][0-9,\\.\\s]*)\\)/
            );
            if (ratingCountMatch) {
                reviewCount = normalizeCount(ratingCountMatch[1]);
            }
        }

        if (rating === null) {
            const ratingMatch = text.match(/\\b([0-9](?:[\\.,][0-9])?)\\s*(?:stars?|star|y\\u0131ld\\u0131z|yildiz)\\b/i);
            if (ratingMatch) {
                rating = Number(ratingMatch[1].replace(",", "."));
            }
        }

        return { rating, review_count: reviewCount };
    })();
    """

    try:
        summary = await run_script_value(tab, summary_script)
    except Exception:
        summary = None

    return summary if isinstance(summary, dict) else {}


async def wait_for_google_maps_ready(tab):
    deadline = time.time() + GOOGLE_MAPS_READY_WAIT_SECONDS

    while time.time() < deadline:
        await accept_google_maps_consent(tab)
        summary = await get_google_maps_summary(tab)
        if summary.get("rating") is not None or summary.get("review_count") is not None:
            return summary

        try:
            body_text = await run_script_value(
                tab,
                "return document.body ? document.body.innerText : '';",
            )
        except Exception:
            body_text = None

        if body_text and ("reviews" in body_text.lower() or "yorum" in body_text.lower()):
            return summary

        await asyncio.sleep(1)

    return await get_google_maps_summary(tab)


async def click_google_maps_reviews_panel(tab):
    click_target_script = """
    (() => {
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const hasReviewsTabLabel = (value) => (
            /\breviews\b/.test(value)
            || /\breview\b/.test(value)
            || /\byorumlar\b/.test(value)
            || /\byorum\b/.test(value)
        );
        const tabNodes = Array.from(document.querySelectorAll("button[role='tab'], div[role='tab']"));
        const looksLikeReviewsTab = (candidate) => {
            const label = `${candidate.text} ${candidate.aria}`;
            return hasReviewsTabLabel(label) && !label.includes("overview");
        };
        const visibleCenter = (node) => {
            const rect = node.getBoundingClientRect();
            return {
                x: Math.min(Math.max(rect.left + rect.width / 2, 1), window.innerWidth - 1),
                y: Math.min(Math.max(rect.top + rect.height / 2, 1), window.innerHeight - 1),
            };
        };
        const targetFromNode = (node, kind) => {
            node.scrollIntoView({ block: "center", inline: "center" });
            const point = visibleCenter(node);
            return {
                kind,
                x: point.x,
                y: point.y,
                text: normalize(node.innerText || node.textContent),
                aria: normalize(node.getAttribute("aria-label")),
                href: node.href || node.getAttribute("href") || null,
            };
        };

        const candidates = tabNodes
            .map((node) => {
                const rect = node.getBoundingClientRect();
                return {
                    node,
                    text: normalize(node.innerText || node.textContent),
                    aria: normalize(node.getAttribute("aria-label")),
                    role: normalize(node.getAttribute("role")),
                    dataTabIndex: normalize(node.getAttribute("data-tab-index")),
                    jsaction: normalize(node.getAttribute("jsaction")),
                    selected: normalize(node.getAttribute("aria-selected")),
                    title: normalize(node.getAttribute("title")),
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                };
            })
            .filter((candidate) => (
                looksLikeReviewsTab(candidate)
                && candidate.width > 0
                && candidate.height > 0
            ));

        const selectedReviewsTab = candidates.find((candidate) => (
            candidate.selected === "true"
        ));
        if (selectedReviewsTab) {
            return { kind: "reviews-tab-selected", already_selected: true };
        }

        const preferred = candidates.find((candidate) => (
            candidate.dataTabIndex === "2"
            && candidate.jsaction.includes("pane.wfvdle5tabs.tabclick")
        )) || candidates.find((candidate) => (
            candidate.text === "reviews" || candidate.text === "yorumlar"
        )) || candidates.find((candidate) => (
            candidate.aria.includes("reviews") || candidate.aria.includes("yorumlar")
        )) || candidates.find((candidate) => (
            candidate.jsaction.includes("pane.wfvdle5tabs.tabclick")
        )) || candidates[0];

        if (preferred) {
            return targetFromNode(preferred.node, "reviews-tab");
        }

        return {
            kind: "reviews-tab-not-found",
            found: false,
            tabs: tabNodes.map((node) => ({
                text: normalize(node.innerText || node.textContent),
                aria: normalize(node.getAttribute("aria-label")),
                selected: normalize(node.getAttribute("aria-selected")),
            })),
        };
    })();
    """

    try:
        target = await run_script_value(tab, click_target_script)
    except Exception:
        target = None

    if not isinstance(target, dict):
        return False

    if target.get("already_selected"):
        return True

    if target.get("found") is False:
        print(f"Google Maps reviews tab was not found. Visible tabs: {target.get('tabs')}")
        return False

    if target.get("x") is None or target.get("y") is None:
        return False

    click_x = int(round(float(target["x"])))
    click_y = int(round(float(target["y"])))
    try:
        await tab.mouse.click(click_x, click_y, humanize=False)
    except Exception:
        return False

    print(
        "Clicked Google Maps reviews target: "
        f"{target.get('kind')} at ({click_x}, {click_y}) "
        f"[{target.get('text') or target.get('aria') or 'unlabeled'}]"
    )
    await asyncio.sleep(2)
    return True


async def get_google_maps_reviews_panel_state(tab):
    panel_state_script = """
    (() => {
                    const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const isReviewsLabel = (value) => (
                        /^reviews$/.test(value)
                        || /^yorumlar$/.test(value)
                        || /^yorum$/.test(value)
                        || value.includes("reviews for ")
                        || value.includes(" ile ilgili yorumlar")
                    );
                    const cardSelector = "div.jftiEf, [data-review-id]";
                    const cardNodes = Array.from(document.querySelectorAll(cardSelector));
                    const uniqueCards = [];
                    const seenCards = new Set();
                    for (const node of cardNodes) {
                        const card = node.closest("div.jftiEf") || node;
                        if (seenCards.has(card)) {
                            continue;
                        }
                        seenCards.add(card);
                        uniqueCards.push(card);
                    }
                    const cards = uniqueCards.length;
                    const feed = document.querySelector("div[role='feed']");
                    const reviewsHeading = Array.from(document.querySelectorAll(
                        "h1, h2, h3, div[role='heading']"
                    )).find((node) => {
                        const text = normalize(node.innerText || node.textContent);
                        const aria = normalize(node.getAttribute("aria-label"));
                        return isReviewsLabel(`${text} ${aria}`);
                    });
                    const selectedTab = Array.from(document.querySelectorAll(
                        "button[role='tab'][aria-selected='true'], div[role='tab'][aria-selected='true']"
                    )).find((node) => {
                        const text = normalize(node.innerText || node.textContent);
                        const aria = normalize(node.getAttribute("aria-label"));
                        return isReviewsLabel(`${text} ${aria}`);
                    });
                    const sortButton = Array.from(document.querySelectorAll("button, div[role='button']"))
                        .find((node) => {
                            const text = normalize(node.innerText || node.textContent);
                            const aria = normalize(node.getAttribute("aria-label"));
                            return (
                                text === "sort"
                                || aria.includes("sort")
                                || text.includes("sort")
                                || text === "s\\u0131rala"
                                || text === "sirala"
                                || aria.includes("s\\u0131rala")
                                || aria.includes("sirala")
                            );
                        });
                    const inReviewsMode = !!selectedTab || !!sortButton;
                    return {
                        cards,
                        has_feed: !!feed,
                        has_sort: !!sortButton,
                        reviews_heading: !!reviewsHeading,
                        reviews_tab_selected: !!selectedTab,
                        surface_ready: inReviewsMode,
                        open: inReviewsMode && (
                            (!!selectedTab && (!!feed || !!sortButton))
                            || !!sortButton
                        ),
                    };
                })();
    """

    try:
        panel_state = await run_script_value(tab, panel_state_script)
    except Exception:
        panel_state = None

    return panel_state if isinstance(panel_state, dict) else {}


async def prime_google_reviews_panel_scroll(tab):
    focus_script = """
    (() => {
        const cardSelector = "[data-review-id], div.jftiEf";
        const isVisible = (node) => {
            if (!node) {
                return false;
            }
            const rect = node.getBoundingClientRect();
            return rect.width > 120 && rect.height > 120 && rect.bottom > 0 && rect.right > 0;
        };
        const isScrollable = (node) => node && node.scrollHeight > node.clientHeight + 100;
        const scoreNode = (node) => {
            const rect = node.getBoundingClientRect();
            let score = node.scrollHeight - node.clientHeight;
            if (node.getAttribute("role") === "feed") {
                score += 300000;
            }
            if (node.querySelector(cardSelector)) {
                score += 200000;
            }
            if (rect.left < window.innerWidth * 0.55) {
                score += 100000;
            }
            if ((node.innerText || "").toLowerCase().includes("reviews")) {
                score += 25000;
            }
            return score;
        };
        const candidates = Array.from(document.querySelectorAll("div, section, main"))
            .filter((node) => isVisible(node) && isScrollable(node))
            .sort((a, b) => scoreNode(b) - scoreNode(a));
        const container = document.querySelector("div[role='feed']")
            || candidates[0]
            || document.scrollingElement
            || document.documentElement;

        if (container.tabIndex < 0) {
            container.tabIndex = -1;
        }
        container.focus?.({ preventScroll: true });

        return {
            container: container.getAttribute?.("role") || container.className || container.tagName || "window",
            candidate_count: candidates.length,
        };
    })();
    """
    primer_script = """
    (() => {
        const isVisible = (node) => {
            const rect = node.getBoundingClientRect();
            return rect.width > 120 && rect.height > 120 && rect.bottom > 0 && rect.right > 0;
        };
        const isScrollable = (node) => node && node.scrollHeight > node.clientHeight + 100;
        const scoreNode = (node) => {
            const rect = node.getBoundingClientRect();
            let score = node.scrollHeight - node.clientHeight;
            if (rect.left < window.innerWidth * 0.55) {
                score += 100000;
            }
            if (node.getAttribute("role") === "main") {
                score += 50000;
            }
            if ((node.innerText || "").toLowerCase().includes("reviews")) {
                score += 25000;
            }
            return score;
        };
        const candidates = Array.from(document.querySelectorAll("div, section, main"))
            .filter((node) => isVisible(node) && isScrollable(node))
            .sort((a, b) => scoreNode(b) - scoreNode(a));
        const container = candidates[0] || document.scrollingElement || document.documentElement;
        const before = container.scrollTop || window.scrollY || 0;
        container.focus?.();
        for (const eventName of ["keydown", "keyup"]) {
            container.dispatchEvent(new KeyboardEvent(eventName, {
                bubbles: true,
                cancelable: true,
                key: "End",
                code: "End",
            }));
            document.dispatchEvent(new KeyboardEvent(eventName, {
                bubbles: true,
                cancelable: true,
                key: "End",
                code: "End",
            }));
        }
        if ("scrollTop" in container) {
            container.scrollTop = Math.min(
                container.scrollHeight,
                container.scrollTop + Math.max(1200, container.clientHeight * 2)
            );
            container.dispatchEvent(new Event("scroll", { bubbles: true }));
            container.dispatchEvent(new WheelEvent("wheel", {
                bubbles: true,
                cancelable: true,
                deltaY: Math.max(1200, container.clientHeight * 2),
            }));
        } else {
            window.scrollBy(0, Math.max(1200, window.innerHeight * 2));
        }
        window.dispatchEvent(new WheelEvent("wheel", {
            bubbles: true,
            cancelable: true,
            deltaY: Math.max(1200, window.innerHeight * 2),
        }));
        return {
            container: container.getAttribute?.("role") || container.className || container.tagName || "window",
            before,
            after: container.scrollTop || window.scrollY || 0,
            candidate_count: candidates.length,
        };
    })();
    """

    with suppress(Exception):
        await tab.bring_to_front()

    with suppress(Exception):
        await run_script_value(tab, focus_script)

    try:
        return await run_script_value(tab, primer_script)
    except Exception:
        return None


async def wait_for_google_maps_reviews_panel(tab):
    deadline = time.time() + GOOGLE_MAPS_REVIEW_PANEL_WAIT_SECONDS

    while time.time() < deadline:
        panel_state = await get_google_maps_reviews_panel_state(tab)

        if panel_state and panel_state.get("open"):
            return True

        clicked = await click_google_maps_reviews_panel(tab)
        if clicked:
            await asyncio.sleep(1)
            continue

        if panel_state and panel_state.get("surface_ready"):
            await prime_google_reviews_panel_scroll(tab)
            await asyncio.sleep(GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS)
            continue

        await prime_google_reviews_panel_scroll(tab)
        await asyncio.sleep(GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS)

    return False


async def sort_google_maps_reviews_most_relevant(tab):
    sort_script = """
    (() => {
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const buttons = Array.from(document.querySelectorAll("button, div[role='button']"));
        const sortButton = buttons.find((node) => {
            const text = normalize(node.innerText || node.textContent);
            const aria = normalize(node.getAttribute("aria-label"));
            return (
                text === "sort"
                || aria.includes("sort")
                || text.includes("sort")
                || text === "s\\u0131rala"
                || text === "sirala"
                || aria.includes("s\\u0131rala")
                || aria.includes("sirala")
            );
        });

        if (!sortButton) {
            return null;
        }

        sortButton.click();
        return true;
    })();
    """
    option_script = """
    (() => {
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const options = Array.from(document.querySelectorAll(
            "div[role='menuitem'], div[role='option'], li, button"
        ));
        const option = options.find((node) => {
            const text = normalize(node.innerText || node.textContent);
            const aria = normalize(node.getAttribute("aria-label"));
            return (
                text.includes("most relevant")
                || aria.includes("most relevant")
                || text.includes("en alakal\\u0131")
                || text.includes("en alakali")
                || aria.includes("en alakal\\u0131")
                || aria.includes("en alakali")
            );
        });

        if (!option) {
            return null;
        }

        option.click();
        return true;
    })();
    """

    try:
        clicked_sort = await run_script_value(tab, sort_script)
    except Exception:
        clicked_sort = None

    if not clicked_sort:
        return False

    await asyncio.sleep(1)

    try:
        clicked_option = await run_script_value(tab, option_script)
    except Exception:
        clicked_option = None

    if clicked_option:
        await asyncio.sleep(2)
        return True

    return False


async def expand_google_review_texts(tab):
    expand_script = """
    (() => {
        let clicked = 0;
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const cardSelector = "[data-review-id], div.jftiEf";
        const cards = Array.from(document.querySelectorAll(cardSelector));
        const buttons = cards.flatMap((card) => Array.from(
            card.querySelectorAll("button, div[role='button']")
        ));

        for (const button of buttons) {
            const text = normalize(button.innerText || button.textContent);
            const aria = normalize(button.getAttribute("aria-label"));
            if (text === "more" || aria === "more" || text === "daha fazla" || aria === "daha fazla") {
                button.click();
                clicked += 1;
            }
        }

        return clicked;
    })();
    """

    with suppress(Exception):
        await run_script_value(tab, expand_script)


async def collect_google_review_cards(tab):
    collect_script = """
    (() => {
        const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
        const normalizeUrl = (value) => {
            if (!value) {
                return null;
            }
            try {
                return new URL(value, window.location.origin).href;
            } catch (_error) {
                return value;
            }
        };
        const looksLikeOwnerResponse = (value) => {
            const text = normalize(value).toLowerCase();
            return (
                /^thank you so much for being our customer!?$/.test(text)
                || text.startsWith("thank you for your rating")
                || text.includes("taking the time to review this location")
                || text.includes("provide us a more detailed experience")
                || text.includes("fiveguys.com/contact-us")
                || text.includes("we appreciate the time you took to rate us")
                || /thank you,\\s*five guys\\b/.test(text)
            );
        };
        const isOwnerResponseNode = (node) => {
            if (!node) {
                return false;
            }
            const ownerContainer = node.closest(".CDe7pd, [data-owner-response], [aria-label*='Owner'], [aria-label*='owner']");
            if (!ownerContainer) {
                return looksLikeOwnerResponse(node.innerText || node.textContent);
            }
            const containerText = normalize(ownerContainer.innerText || ownerContainer.textContent).toLowerCase();
            return (
                containerText.includes("response from the owner")
                || containerText.includes("owner")
                || looksLikeOwnerResponse(node.innerText || node.textContent)
            );
        };
        const parseRating = (card) => {
            const ratingNode = Array.from(card.querySelectorAll("[aria-label]")).find((node) => {
                const label = node.getAttribute("aria-label") || "";
                return /[0-9](?:[\\.,][0-9])?\\s*(?:stars?|star|y\\u0131ld\\u0131z|yildiz)/i.test(label);
            });
            if (!ratingNode) {
                return null;
            }

            const match = (ratingNode.getAttribute("aria-label") || "").match(/([0-9](?:[\\.,][0-9])?)/);
            return match ? Number(match[1].replace(",", ".")) : null;
        };

        const cardSelector = "div.jftiEf, [data-review-id]";
        const feed = document.querySelector("div[role='feed']");
        const scrollableContainers = Array.from(document.querySelectorAll("div"))
            .filter((node) => (
                node.scrollHeight > node.clientHeight + 100
                && node.querySelector(cardSelector)
            ))
            .sort((a, b) => b.querySelectorAll(cardSelector).length - a.querySelectorAll(cardSelector).length);
        const root = feed || scrollableContainers[0] || null;
        if (!root) {
            return [];
        }
        const cards = [];
        const seenCards = new Set();
        for (const node of Array.from(root.querySelectorAll(cardSelector))) {
            const card = node.closest("div.jftiEf") || node;
            if (seenCards.has(card)) {
                continue;
            }
            seenCards.add(card);
            if (
                !card.getAttribute("data-review-id")
                && !card.querySelector("[data-review-id]")
                && !card.querySelector(".d4r55, .wiI7pd")
            ) {
                continue;
            }
            cards.push(card);
        }
        return cards.map((card, index) => {
            const reviewId = card.getAttribute("data-review-id")
                || (card.querySelector("[data-review-id]") || {}).getAttribute?.("data-review-id")
                || null;
            const authorNode = card.querySelector(".d4r55")
                || card.querySelector("button[aria-label][data-href]")
                || card.querySelector("a[href*='/maps/contrib/']");
            const authorLink = card.querySelector("a[href*='/maps/contrib/']");
            const authorUrl = normalizeUrl(
                authorLink?.href
                || authorNode?.getAttribute?.("data-href")
                || authorNode?.closest?.("a")?.href
            );
            const textCandidates = Array.from(card.querySelectorAll(
                ".MyEned .wiI7pd, .MyEned span, .wiI7pd, [data-expandable-section]"
            )).filter((node) => (
                normalize(node.innerText || node.textContent)
                && !isOwnerResponseNode(node)
            ));
            const textNode = textCandidates[0] || null;
            const dateNode = card.querySelector(".rsqaWe")
                || Array.from(card.querySelectorAll("span")).find((node) => {
                    const text = normalize(node.innerText || node.textContent).toLowerCase();
                    return /ago$|yesterday|today|week|month|year/.test(text);
                });
            const authorInfoNode = card.querySelector(".RfnDt")
                || card.querySelector(".WNxzHc")
                || null;

            return {
                rank: index + 1,
                review_id: reviewId,
                author_name: normalize(authorNode && (authorNode.innerText || authorNode.textContent)),
                author_url: authorUrl,
                author_info: normalize(authorInfoNode && (authorInfoNode.innerText || authorInfoNode.textContent)),
                review_rating: parseRating(card),
                relative_date: normalize(dateNode && (dateNode.innerText || dateNode.textContent)),
                review_text: normalize(textNode && (textNode.innerText || textNode.textContent)),
            };
        }).filter((review) => review.author_name || review.review_text || review.review_id);
    })();
    """

    try:
        reviews = await run_script_value(tab, collect_script)
    except Exception:
        reviews = None

    return reviews if isinstance(reviews, list) else []


async def scroll_google_reviews_panel(tab):
    scroll_script = """
    (() => {
        const cardSelector = "div.jftiEf, [data-review-id]";
        const uniqueCardsIn = (root) => {
            const cards = [];
            const seen = new Set();
            for (const node of Array.from(root.querySelectorAll(cardSelector))) {
                const card = node.closest("div.jftiEf") || node;
                if (seen.has(card)) {
                    continue;
                }
                seen.add(card);
                cards.push(card);
            }
            return cards;
        };
        const cards = uniqueCardsIn(document);
        const isScrollable = (node) => node && node.scrollHeight > node.clientHeight + 100;
        const candidates = Array.from(document.querySelectorAll("div"))
            .filter((node) => (
                isScrollable(node)
                && node.querySelector(cardSelector)
            ))
            .sort((a, b) => {
                const aCards = uniqueCardsIn(a).length;
                const bCards = uniqueCardsIn(b).length;
                return bCards - aCards || b.scrollHeight - a.scrollHeight;
            });

        const feed = document.querySelector("div[role='feed']");
        const lastCard = cards[cards.length - 1];
        const scrollableAncestor = lastCard
            ? (() => {
                let node = lastCard.parentElement;
                while (node && node !== document.body) {
                    if (isScrollable(node)) {
                        return node;
                    }
                    node = node.parentElement;
                }
                return null;
            })()
            : null;
        const container = candidates[0] || scrollableAncestor || (isScrollable(feed) ? feed : null);

        if (!container) {
            window.scrollBy(0, Math.max(500, window.innerHeight * 0.8));
            window.dispatchEvent(new WheelEvent("wheel", {
                bubbles: true,
                cancelable: true,
                deltaY: Math.max(700, window.innerHeight),
            }));
            return {
                scrolled: true,
                container: "window",
                card_count: cards.length,
                scroll_top: window.scrollY,
                scroll_height: document.body ? document.body.scrollHeight : 0,
            };
        }

        const before = container.scrollTop;
        container.focus?.();
        if (lastCard) {
            lastCard.scrollIntoView({ block: "end", inline: "nearest" });
        }
        container.scrollTop = Math.min(
            container.scrollHeight,
            container.scrollTop + Math.max(900, container.clientHeight * 1.75)
        );
        container.dispatchEvent(new Event("scroll", { bubbles: true }));
        container.dispatchEvent(new WheelEvent("wheel", {
            bubbles: true,
            cancelable: true,
            deltaY: Math.max(900, container.clientHeight * 1.75),
        }));
        if (container.scrollTop === before && lastCard) {
            lastCard.dispatchEvent(new WheelEvent("wheel", {
                bubbles: true,
                cancelable: true,
                deltaY: Math.max(900, container.clientHeight * 1.75),
            }));
        }

        return {
            scrolled: container.scrollTop !== before,
            container: container.getAttribute("role") || container.className || "div",
            card_count: cards.length,
            scroll_top: container.scrollTop,
            scroll_height: container.scrollHeight,
        };
    })();
    """

    try:
        return await run_script_value(tab, scroll_script)
    except Exception:
        return None


async def collect_google_maps_reviews(tab, location, google_maps_url, limit=GOOGLE_MAPS_REVIEW_LIMIT):
    reviews_by_key = {}
    seen_raw_review_keys = set()
    no_progress_scrolls = 0
    last_count = 0
    last_raw_review_count = 0
    panel_reopen_attempts = 0
    stall_recovery_attempts = 0
    available_review_total = parse_int(location.get("review_count"))
    target_limit = (
        min(limit, available_review_total)
        if available_review_total and available_review_total < limit
        else limit
    )

    async def reopen_reviews_panel(reason):
        nonlocal panel_reopen_attempts
        if panel_reopen_attempts >= 2:
            return False

        if not await ensure_google_maps_expected_location(tab, location, reason):
            return False

        direct_reviews_url = google_maps_reviews_url_from_href(google_maps_url)
        if direct_reviews_url and not google_maps_url_matches_location(
            direct_reviews_url,
            location,
        ):
            direct_reviews_url = None
        if not direct_reviews_url:
            direct_reviews_url = await build_safe_google_maps_reviews_url(tab, location)

        if not direct_reviews_url:
            if await click_google_maps_reviews_panel(tab):
                panel_state = await get_google_maps_reviews_panel_state(tab)
                if panel_state.get("open"):
                    return True
            return await wait_for_google_maps_reviews_panel(tab)

        panel_reopen_attempts += 1
        print(
            f"Google reviews panel {reason} for {location.get('name')}; "
            f"reopening direct reviews URL ({panel_reopen_attempts}/2)."
        )
        await tab.go_to(direct_reviews_url, timeout=GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS)
        await wait_for_google_maps_ready(tab)
        if not await google_maps_tab_matches_location(tab, location):
            print(
                f"Direct reviews URL moved away from {location.get('name')}; "
                "not clicking or scraping this wrong page."
            )
            return False

        await prime_google_reviews_panel_scroll(tab)
        panel_state = await get_google_maps_reviews_panel_state(tab)
        if panel_state.get("open"):
            return True

        if await click_google_maps_reviews_panel(tab):
            panel_state = await get_google_maps_reviews_panel_state(tab)
            if panel_state.get("open"):
                return True
        return await wait_for_google_maps_reviews_panel(tab)

    for scroll_attempt in range(1, GOOGLE_MAPS_REVIEW_MAX_SCROLLS + 1):
        if not await google_maps_tab_matches_location(tab, location):
            if not await reopen_reviews_panel("moved away from the expected store"):
                if reviews_by_key:
                    print(
                        f"Google Maps moved away from {location.get('name')}; "
                        f"returning {len(reviews_by_key)} reviews collected before it moved."
                    )
                break
            continue

        panel_state = await get_google_maps_reviews_panel_state(tab)
        if not panel_state.get("open"):
            if panel_state.get("surface_ready"):
                await prime_google_reviews_panel_scroll(tab)
                await asyncio.sleep(GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS)
                continue

            if not await reopen_reviews_panel("is not on the reviews panel"):
                if reviews_by_key:
                    print(
                        f"Could not reopen Google reviews panel for {location.get('name')}; "
                        f"returning {len(reviews_by_key)} reviews collected before the panel changed."
                    )
                break
            continue

        await expand_google_review_texts(tab)
        raw_reviews = await collect_google_review_cards(tab)
        raw_review_keys = {
            normalize_google_review_key(raw_review)
            for raw_review in raw_reviews
        }
        raw_reviews_progressed = bool(raw_review_keys - seen_raw_review_keys)
        seen_raw_review_keys.update(raw_review_keys)

        panel_card_count = panel_state.get("cards", 0) or 0
        try:
            panel_card_count = int(panel_card_count)
        except (TypeError, ValueError):
            panel_card_count = 0

        current_raw_review_count = max(len(seen_raw_review_keys), panel_card_count)
        raw_reviews_progressed = (
            raw_reviews_progressed
            or current_raw_review_count > last_raw_review_count
        )
        last_raw_review_count = max(last_raw_review_count, current_raw_review_count)
        if not raw_reviews:
            await prime_google_reviews_panel_scroll(tab)
            await asyncio.sleep(GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS)
            continue

        for raw_review in raw_reviews:
            if len(reviews_by_key) >= target_limit:
                break
            if not should_keep_google_review(raw_review):
                continue

            key = normalize_google_review_key(raw_review)
            if key in reviews_by_key:
                continue

            review_rank = len(reviews_by_key) + 1
            reviews_by_key[key] = {
                "store_name": location.get("name"),
                "store_street": location.get("street"),
                "store_city": location.get("city"),
                "store_state": location.get("state"),
                "store_zip_code": location.get("zip_code"),
                "google_maps_cid": location.get("google_maps_cid"),
                "google_maps_url": google_maps_url,
                "location_rating": location.get("rating"),
                "location_review_count": location.get("review_count"),
                "review_rank": review_rank,
                "review_id": raw_review.get("review_id"),
                "author_name": raw_review.get("author_name"),
                "author_url": raw_review.get("author_url"),
                "author_info": raw_review.get("author_info"),
                "review_rating": raw_review.get("review_rating"),
                "relative_date": raw_review.get("relative_date"),
                "review_text": raw_review.get("review_text"),
            }

        current_count = len(reviews_by_key)
        if current_count >= target_limit:
            break

        if (
            available_review_total
            and available_review_total <= limit
            and panel_state.get("cards", 0) >= available_review_total
            and current_count == last_count
        ):
            print(
                f"Loaded all {available_review_total} Google review cards for "
                f"{location.get('name')}; kept {current_count} customer text reviews "
                "after filtering blank/owner-response rows."
            )
            break

        if current_count > last_count or raw_reviews_progressed:
            no_progress_scrolls = 0
            last_count = max(last_count, current_count)
        else:
            no_progress_scrolls += 1

        if no_progress_scrolls >= GOOGLE_MAPS_REVIEW_NO_PROGRESS_SCROLLS:
            if stall_recovery_attempts < 2 and current_count < target_limit:
                stall_recovery_attempts += 1
                no_progress_scrolls = 0
                print(
                    f"Google review scroll stalled at {current_count} rows for "
                    f"{location.get('name')}; refreshing reviews panel "
                    f"({stall_recovery_attempts}/2)."
                )
                if await reopen_reviews_panel("stalled while scrolling"):
                    continue
            break

        await scroll_google_reviews_panel(tab)
        await asyncio.sleep(GOOGLE_MAPS_REVIEW_SCROLL_PAUSE_SECONDS)

    if len(reviews_by_key) <= 3 and target_limit > 3:
        print(
            f"Google reviews for {location.get('name')} only yielded "
            f"{len(reviews_by_key)} kept rows from {last_raw_review_count} raw cards; "
            "returning the partial rows instead of discarding them."
        )

    return list(reviews_by_key.values())[:target_limit]


async def ensure_google_maps_expected_location(tab, location, reason):
    if await google_maps_tab_matches_location(tab, location):
        return True

    google_maps_url = google_maps_place_url_for_location(location)
    if not google_maps_url:
        print(
            f"Google Maps is not on the expected store for {location.get('name')} "
            f"while {reason}, and no CID URL is available."
        )
        return False

    try:
        current_url = await tab.current_url
    except Exception:
        current_url = None

    print(
        f"Google Maps moved away from {location.get('name')} while {reason}; "
        f"current URL was {current_url!r}. Reopening expected store URL."
    )
    await tab.go_to(google_maps_url, timeout=GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS)
    await wait_for_google_maps_ready(tab)

    if await google_maps_tab_matches_location(tab, location):
        return True

    try:
        current_url = await tab.current_url
    except Exception:
        current_url = None

    print(
        f"Google Maps still does not match {location.get('name')} after reopening "
        f"the expected store URL. Current URL: {current_url!r}"
    )
    return False


async def build_safe_google_maps_reviews_url(tab, location):
    if not await ensure_google_maps_expected_location(
        tab,
        location,
        "building the direct reviews URL",
    ):
        return None

    deadline = time.time() + 10
    direct_reviews_url = None
    last_url = None

    while time.time() < deadline:
        try:
            last_url = await tab.current_url
        except Exception:
            last_url = None

        direct_reviews_url = await build_google_maps_reviews_url_from_loaded_page(tab, location)
        if direct_reviews_url:
            break

        await asyncio.sleep(0.5)

    if not direct_reviews_url:
        print(
            f"Could not build a safe direct Google reviews URL for "
            f"{location.get('name')} from current URL {last_url!r}; "
            "falling back to the Reviews tab click."
        )
        return None

    if not google_maps_url_matches_location(direct_reviews_url, location):
        print(
            f"Ignoring direct reviews URL for {location.get('name')} because it "
            f"does not contain the expected CID/feature id: {direct_reviews_url}"
        )
        return None

    print(f"Built safe direct Google reviews URL for {location.get('name')}.")
    return direct_reviews_url


async def fetch_google_maps_reviews(browser, location, limit=GOOGLE_MAPS_REVIEW_LIMIT):
    google_maps_url = google_maps_place_url_for_location(location)
    if not google_maps_url:
        print(f"No Google Maps URL found for {location.get('name')}; skipping reviews.")
        return {
            "rating": None,
            "review_count": None,
            "reviews": [],
        }

    tab = await browser.new_tab()
    try:
        print(f"Opening Google Maps reviews for {location.get('name')}: {google_maps_url}")
        await tab.go_to(google_maps_url, timeout=GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS)
        summary = await wait_for_google_maps_ready(tab)
        location["rating"] = summary.get("rating")
        location["review_count"] = summary.get("review_count")

        if not await ensure_google_maps_expected_location(
            tab,
            location,
            "opening the store page",
        ):
            return {
                "rating": location.get("rating"),
                "review_count": location.get("review_count"),
                "reviews": [],
            }

        review_source_url = google_maps_url
        reviews_panel_open = False
        direct_reviews_url = await build_safe_google_maps_reviews_url(tab, location)

        if direct_reviews_url:
            print(f"Opening direct Google reviews URL for {location.get('name')}.")
            review_source_url = direct_reviews_url
            await tab.go_to(
                direct_reviews_url,
                timeout=GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS,
            )
            await wait_for_google_maps_ready(tab)
            if await google_maps_tab_matches_location(tab, location):
                await prime_google_reviews_panel_scroll(tab)
                reviews_panel_open = await wait_for_google_maps_reviews_panel(tab)
            else:
                print(
                    f"Direct Google reviews URL did not stay on {location.get('name')}; "
                    "falling back to the expected store page."
                )
                review_source_url = google_maps_url
                reviews_panel_open = False
                await ensure_google_maps_expected_location(
                    tab,
                    location,
                    "recovering from a bad direct reviews URL",
                )

        if not reviews_panel_open:
            if not await ensure_google_maps_expected_location(
                tab,
                location,
                "opening the reviews panel",
            ):
                return {
                    "rating": location.get("rating"),
                    "review_count": location.get("review_count"),
                    "reviews": [],
                }
            await click_google_maps_reviews_panel(tab)
            if await google_maps_tab_matches_location(tab, location):
                reviews_panel_open = await wait_for_google_maps_reviews_panel(tab)

        if not reviews_panel_open:
            direct_reviews_url = (
                direct_reviews_url
                or await build_safe_google_maps_reviews_url(tab, location)
            )
            if direct_reviews_url:
                print(
                    f"Reviews tab hidden for {location.get('name')}; "
                    f"opening direct reviews URL."
                )
                review_source_url = direct_reviews_url
                await tab.go_to(
                    direct_reviews_url,
                    timeout=GOOGLE_MAPS_NAVIGATION_TIMEOUT_SECONDS,
                )
                await wait_for_google_maps_ready(tab)
                if await google_maps_tab_matches_location(tab, location):
                    reviews_panel_open = await wait_for_google_maps_reviews_panel(tab)
                else:
                    print(
                        f"Fallback direct reviews URL moved away from "
                        f"{location.get('name')}; not scraping the wrong page."
                    )
                    reviews_panel_open = False

        if not reviews_panel_open:
            print(f"Google reviews panel did not open for {location.get('name')}.")
            return {
                "rating": location.get("rating"),
                "review_count": location.get("review_count"),
                "reviews": [],
            }

        if not await google_maps_tab_matches_location(tab, location):
            print(
                f"Google Maps is no longer on {location.get('name')} before collection; "
                "skipping this store instead of scraping the wrong page."
            )
            return {
                "rating": location.get("rating"),
                "review_count": location.get("review_count"),
                "reviews": [],
            }

        sorted_reviews = await sort_google_maps_reviews_most_relevant(tab)
        if sorted_reviews:
            print(f"Sorted Google reviews by Most relevant for {location.get('name')}.")

        reviews = await collect_google_maps_reviews(
            tab,
            location,
            review_source_url,
            limit=limit,
        )
        print(f"Google reviews: {len(reviews)} for {location.get('name')}")
        return {
            "rating": location.get("rating"),
            "review_count": location.get("review_count"),
            "reviews": reviews,
        }
    except Exception as e:
        print(f"Failed to scrape Google reviews for {location.get('name')}: {e}")
        return {
            "rating": location.get("rating"),
            "review_count": location.get("review_count"),
            "reviews": location.get("reviews") or [],
        }
    finally:
        with suppress(Exception):
            await tab.close()


def load_saved_locations_from_outputs(mode_name, purpose_label):
    json_locations = []
    csv_locations = []

    if LOCATIONS_JSON_PATH.exists():
        with open(LOCATIONS_JSON_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, list):
            raise ValueError("locations.json did not contain a list of locations.")

        json_locations = [location for location in payload if isinstance(location, dict)]

    if LOCATIONS_CSV_PATH.exists():
        with open(LOCATIONS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
            csv_locations = [row for row in csv.DictReader(f) if isinstance(row, dict)]

    locations = csv_locations if len(csv_locations) > len(json_locations) else json_locations

    if not locations:
        raise FileNotFoundError(
            f"locations.json or locations.csv is required for SCRAPER_MODE={mode_name}. "
            "Run the core scraper first."
        )

    if csv_locations and locations is csv_locations:
        print(
            f"Using locations.csv for {purpose_label} "
            f"({len(csv_locations)} rows; locations.json has {len(json_locations)})."
        )

    normalized_locations = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        order_url = canonical_order_menu_url(location.get("order_url"))
        if order_url:
            location["order_url"] = order_url
        normalized_locations.append(location)

    return normalized_locations


def load_saved_locations_for_google_reviews():
    locations = load_saved_locations_from_outputs("google_reviews", "Google reviews")

    for location in locations:
        if not location.get("google_maps_cid"):
            location["google_maps_cid"] = extract_google_maps_cid(
                location.get("google_maps_url")
            )
        location["reviews"] = []

    return locations


def load_saved_menu_items_by_order_url():
    menu_rows = []

    if MENU_ITEMS_CSV_PATH.exists():
        with open(MENU_ITEMS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
            menu_rows = [row for row in csv.DictReader(f) if isinstance(row, dict)]
    elif MENU_ITEMS_JSON_PATH.exists():
        with open(MENU_ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            menu_rows = [row for row in payload if isinstance(row, dict)]

    menu_by_order_url = {}
    for row in menu_rows:
        order_url = normalize_order_url(row.get("order_url"))
        if not order_url:
            continue
        menu_by_order_url.setdefault(order_url, []).append(row)

    return menu_by_order_url


def load_saved_locations_for_classic_combo():
    locations = load_saved_locations_from_outputs(
        "classic_combo",
        "Classic Combo recovery",
    )
    menu_by_order_url = load_saved_menu_items_by_order_url()

    if not menu_by_order_url:
        raise FileNotFoundError(
            "menu_items.csv or menu_items.json is required for "
            "SCRAPER_MODE=classic_combo. Run the core scraper first."
        )

    target_locations = []
    for location in locations:
        order_url = normalize_order_url(location.get("order_url"))
        if not order_url:
            continue

        location["menu"] = menu_by_order_url.get(order_url, [])
        location["classic_combo_items"] = []
        target_locations.append(location)

    if FIVE_GUYS_MAX_LOCATIONS > 0:
        target_locations = target_locations[:FIVE_GUYS_MAX_LOCATIONS]

    return target_locations


def filter_google_review_locations(locations):
    filtered_locations = list(locations)

    if GOOGLE_MAPS_DEBUG_STORE_NAME:
        debug_name = GOOGLE_MAPS_DEBUG_STORE_NAME.lower()
        filtered_locations = [
            location
            for location in filtered_locations
            if debug_name in (location.get("name") or "").lower()
        ]

    if GOOGLE_MAPS_DEBUG_STORE_LIMIT > 0:
        filtered_locations = filtered_locations[:GOOGLE_MAPS_DEBUG_STORE_LIMIT]

    return filtered_locations


def google_review_location_key(location):
    cid = clean_text(location.get("google_maps_cid"))
    if not cid:
        cid = extract_google_maps_cid(location.get("google_maps_url"))
    if cid:
        return ("cid", cid)

    google_maps_url = clean_text(location.get("google_maps_url"))
    if google_maps_url:
        return ("url", google_maps_url.lower())

    name = clean_text(location.get("name"))
    street = clean_text(location.get("street"))
    if name and street:
        return ("name_street", name.lower(), street.lower())
    if name:
        return ("name", name.lower())

    return None


def merge_google_review_fields(locations, reviewed_locations):
    locations_by_key = {}
    locations_by_name = {}

    for location in locations:
        key = google_review_location_key(location)
        if key:
            locations_by_key.setdefault(key, location)

        name = clean_text(location.get("name"))
        if name:
            locations_by_name.setdefault(name.lower(), location)

    for reviewed_location in reviewed_locations:
        key = google_review_location_key(reviewed_location)
        target_location = locations_by_key.get(key)

        if not target_location:
            name = clean_text(reviewed_location.get("name"))
            target_location = locations_by_name.get(name.lower()) if name else None

        if not target_location:
            continue

        target_location["rating"] = reviewed_location.get("rating")
        target_location["review_count"] = reviewed_location.get("review_count")
        target_location["reviews"] = reviewed_location.get("reviews") or []


async def scrape_google_reviews_for_locations(locations, reset_csv_file=True):
    run_namespace = (
        f"reviews-{time.strftime('%Y%m%d-%H%M%S')}-"
        f"{int(time.time() * 1000) % 1000:03d}"
    )
    profile_dir = google_maps_review_profile_dir(run_namespace)
    options = build_chrome_options(profile_dir)
    browser = Chrome(options=options)

    try:
        await browser.start()
        if reset_csv_file:
            reset_google_reviews_csv()

        total_locations = len(locations)
        review_concurrency = min(GOOGLE_MAPS_SCRAPE_CONCURRENCY, max(1, total_locations))
        review_semaphore = asyncio.Semaphore(review_concurrency)

        print(
            f"Scraping Google reviews for {total_locations} "
            f"{'store' if total_locations == 1 else 'stores'} "
            f"with up to {review_concurrency} concurrent "
            f"{'tab' if review_concurrency == 1 else 'tabs'}."
        )
        print(f"Using fresh Google Maps Chrome profile: {profile_dir}")

        async def scrape_one_google_review_location(index, location):
            async with review_semaphore:
                print(
                    f"Google reviews task {index}/{total_locations}: "
                    f"{location.get('name')}"
                )
                review_result = await fetch_google_maps_reviews(
                    browser,
                    location,
                    limit=GOOGLE_MAPS_REVIEW_LIMIT,
                )
                location["rating"] = review_result.get("rating")
                location["review_count"] = review_result.get("review_count")
                location["reviews"] = review_result.get("reviews") or []
                append_google_reviews_to_csv(location)
                return location

        await asyncio.gather(
            *(
                scrape_one_google_review_location(index, location)
                for index, location in enumerate(locations, start=1)
            )
        )
    finally:
        await close_browser_safely(browser)


async def scrape_google_reviews_from_saved_locations():
    locations = load_saved_locations_for_google_reviews()
    target_locations = filter_google_review_locations(locations)
    if not target_locations:
        raise RuntimeError("No saved locations matched the Google review debug filters.")

    await scrape_google_reviews_for_locations(target_locations, reset_csv_file=True)

    export_google_reviews_to_csv(target_locations)
    export_google_reviews_to_json(target_locations)
    merge_google_review_fields(locations, target_locations)

    export_locations_to_csv(locations)
    export_locations_to_json(locations)
    return locations, target_locations


async def main_google_reviews_only():
    started_at = time.perf_counter()
    try:
        await scrape_google_reviews_from_saved_locations()
    finally:
        print_elapsed_time(started_at, "Google reviews run")


def normalize_restaurants_url(href, base_url=FIVE_GUYS_DIRECTORY_ROOT_URL):
    href = clean_text(href)
    if not href:
        return None

    url = urljoin(base_url, href)
    parsed_url = urlparse(url)
    if parsed_url.netloc.lower() != "restaurants.fiveguys.com":
        return None

    normalized = parsed_url._replace(fragment="")
    return urlunparse(normalized)


def restaurant_slug_from_url(url):
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if not path_parts:
        return None
    return unquote(path_parts[-1])


def location_entry_from_url(url, name=None, cid=None, google_maps_url=None):
    url = normalize_restaurants_url(url)
    if not url:
        return None

    slug = restaurant_slug_from_url(url)
    if not slug:
        return None

    return (
        slug,
        url,
        clean_text(name),
        clean_text(cid),
        clean_text(google_maps_url),
    )


def location_entry_key(location_entry):
    _slug, url, _name, cid, google_maps_url = location_entry
    if cid:
        return ("cid", cid)
    if google_maps_url:
        return ("maps", google_maps_url.lower())
    return ("url", (url or "").rstrip("/").lower())


def dedupe_location_entries(location_entries):
    deduped = []
    seen = set()
    for location_entry in location_entries:
        key = location_entry_key(location_entry)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(location_entry)
    return deduped


def parse_location_url_entries(value):
    location_entries = []
    for raw_url in re.split(r"[\n,;]+", value or ""):
        location_entry = location_entry_from_url(raw_url)
        if location_entry:
            location_entries.append(location_entry)
        elif clean_text(raw_url):
            print(f"Ignoring invalid Five Guys test location URL: {raw_url}")

    return dedupe_location_entries(location_entries)


def load_failed_store_retry_entries():
    failure_rows = read_csv_dicts(SCRAPE_FAILURES_CSV_PATH)
    retry_entries = []
    retained_failure_rows = []
    ignored_rows = 0

    for row in failure_rows:
        stage = (clean_text(row.get("stage")) or "").lower()
        if stage not in FAILED_STORE_RETRY_STAGES:
            retained_failure_rows.append(row)
            continue

        entry = location_entry_from_url(row.get("url"), row.get("store_name"))
        if not entry:
            ignored_rows += 1
            retained_failure_rows.append(row)
            continue

        retry_entries.append(entry)

    retry_entries = dedupe_location_entries(retry_entries)
    if FIVE_GUYS_MAX_LOCATIONS > 0:
        retry_entries = retry_entries[:FIVE_GUYS_MAX_LOCATIONS]

    if ignored_rows:
        print(
            f"Ignored {ignored_rows} failed-store "
            f"{'row' if ignored_rows == 1 else 'rows'} with non-directory URLs."
        )

    return retry_entries, retained_failure_rows


def extract_google_maps_url(html):
    maps_link = html.css_first("a.c-get-directions-button[href]")
    if maps_link:
        return clean_text(maps_link.attributes.get("href"))

    for a in html.css("a[href]"):
        href = clean_text(a.attributes.get("href"))
        if href and "google" in urlparse(href).netloc.lower() and "/maps" in href:
            return href
    return None


def parse_locations_page(html: HTMLParser, page_url=FIVE_GUYS_DIRECTORY_ROOT_URL):
    locations = html.css("article.Teaser--directory")
    for location in locations:
        a = location.css_first("a.Teaser-contentWrapper")
        if not a:
            continue

        url = normalize_restaurants_url(a.attributes.get("href"), page_url)
        if not url:
            continue

        name = extract_text(location, "span.LocationName-geo")
        google_maps_url = extract_google_maps_url(location)
        cid = extract_google_maps_cid(google_maps_url)
        location_entry = location_entry_from_url(url, name, cid, google_maps_url)
        if location_entry:
            yield location_entry


def parse_directory_template_name(html):
    monitoring_node = html.css_first("script#monitoring-data")
    if not monitoring_node:
        return None

    try:
        monitoring_data = json.loads(monitoring_node.text())
    except (TypeError, ValueError):
        return None

    return clean_text(monitoring_data.get("soyTemplateName"))


def parse_directory_links(html, page_url):
    for a in html.css("section.Directory a.Directory-listLink[href]"):
        url = normalize_restaurants_url(a.attributes.get("href"), page_url)
        if not url:
            continue

        yield {
            "url": url,
            "name": clean_text(a.text()),
            "count": parse_int(a.attributes.get("data-count")),
        }


def parse_single_location_entry(html, page_url):
    if not html.css_first("span.LocationName-geo"):
        return None

    google_maps_url = extract_google_maps_url(html)
    return location_entry_from_url(
        page_url,
        extract_text(html, "span.LocationName-geo"),
        extract_google_maps_cid(google_maps_url),
        google_maps_url,
    )


def directory_link_points_to_single_location(link, template_name):
    return template_name == "directory.cityList" and link.get("count") == 1


async def load_directory_html(tab, url):
    last_html = None
    for attempt in range(1, FIVE_GUYS_DIRECTORY_DISCOVERY_ATTEMPTS + 1):
        if attempt > 1:
            print(
                f"Retrying directory discovery page {url} "
                f"({attempt}/{FIVE_GUYS_DIRECTORY_DISCOVERY_ATTEMPTS})"
            )

        last_html = await get_restaurants_html(
            url,
            tab,
            ready_selector=FIVE_GUYS_DIRECTORY_READY_SELECTOR,
        )
        if last_html is not None:
            return last_html

    return last_html


async def discover_location_entries(tab, root_url=FIVE_GUYS_DIRECTORY_ROOT_URL):
    pending_urls = [root_url]
    visited_urls = set()
    location_entries = []
    discovered_direct_entries = 0

    while pending_urls:
        page_url = normalize_restaurants_url(pending_urls.pop(0), root_url)
        if not page_url:
            continue

        page_key = page_url.rstrip("/").lower()
        if page_key in visited_urls:
            continue
        visited_urls.add(page_key)

        print(
            f"Discovering Five Guys locations from directory page "
            f"{len(visited_urls)}: {page_url}"
        )
        html = await load_directory_html(tab, page_url)
        if html is None:
            raise RuntimeError(f"Failed to load Five Guys directory page: {page_url}")

        page_location_entries = list(parse_locations_page(html, page_url))
        if page_location_entries:
            location_entries.extend(page_location_entries)
            print(
                f"Discovered {len(page_location_entries)} store cards from {page_url}."
            )
            continue

        single_location_entry = parse_single_location_entry(html, page_url)
        if single_location_entry:
            location_entries.append(single_location_entry)
            discovered_direct_entries += 1
            continue

        template_name = parse_directory_template_name(html)
        directory_links = list(parse_directory_links(html, page_url))
        if not directory_links:
            print(f"No directory links or store cards found on {page_url}.")
            continue

        for link in directory_links:
            if directory_link_points_to_single_location(link, template_name):
                direct_entry = location_entry_from_url(link["url"], link.get("name"))
                if direct_entry:
                    location_entries.append(direct_entry)
                    discovered_direct_entries += 1
                continue

            pending_urls.append(link["url"])

    location_entries = dedupe_location_entries(location_entries)
    if FIVE_GUYS_MAX_LOCATIONS > 0:
        location_entries = location_entries[:FIVE_GUYS_MAX_LOCATIONS]

    print(
        f"Discovered {len(location_entries)} unique Five Guys store URLs "
        f"from {len(visited_urls)} directory pages "
        f"({discovered_direct_entries} one-store city links queued directly)."
    )
    return location_entries


def parse_location_page(html, cid=None, google_maps_url=None):
    hours_node = html.css_first("div.c-hours-details-wrapper.js-hours-table")
    hours = json.loads(hours_node.attributes["data-days"]) if hours_node else None

    delivery_node = html.css_first("div.Core-deliveryHours div.c-hours-details-wrapper")
    delivery_hours = json.loads(delivery_node.attributes["data-days"]) if delivery_node else None

    google_maps_url = clean_text(google_maps_url) or extract_google_maps_url(html)
    cid = clean_text(cid) or extract_google_maps_cid(google_maps_url)

    new_location = FiveGuysLocation(
        name=extract_text(html, "span.LocationName-geo"),
        street=extract_text(html, "span.c-address-street-1"),
        city=extract_text(html, "span.c-address-city"),
        state=extract_text(html, "abbr.c-address-state"),
        zip_code=extract_text(html, "span.c-address-postal-code"),
        phone=extract_text(html, "div.Phone-display"),
        google_maps_cid=cid,
        google_maps_url=google_maps_url,
        order_url=extract_order_url(html),
        hours=hours,
        delivery_hours=delivery_hours,
        services=[el.text() for el in html.css("li.About-service span[itemprop='name']")],
        payment_methods=[el.text() for el in html.css("div.About-paymentMethodText")],
        rating=None,
        review_count=None,
        reviews=None,
        menu=None
    )
    return asdict(new_location)


def is_browser_command_timeout(error):
    message = str(error).lower()
    return (
        "command execution timed out" in message
        or "command timeout" in message
        or "targetmethod.create_target" in message
        or "pagemethod.enable" in message
        or "remote computer refused" in message
        or "websocket connection" in message
        or "server rejected websocket" in message
        or "http 500" in message
        or "winerror 1225" in message
    )


async def scrape_location(url, cid, google_maps_url, name, browser, tab):
    recycle_browser = False

    for attempt in range(1, SCRAPE_LOCATION_ATTEMPTS + 1):
        try:
            if attempt > 1:
                print(
                    f"Retrying {name or url} "
                    f"({attempt}/{SCRAPE_LOCATION_ATTEMPTS})"
            )

            print(f"Scraping: {name or url}")
            html = await get_restaurants_html(
                url,
                tab,
                ready_selector="span.LocationName-geo",
            )
            if html is None:
                if attempt < SCRAPE_LOCATION_ATTEMPTS:
                    continue
                return None, recycle_browser

            location = parse_location_page(
                html,
                cid=cid,
                google_maps_url=google_maps_url,
            )
            append_location_to_csv(location)
            order_url = location.get("order_url")
            if order_url:
                menu_json = await fetch_menu_json_pydoll(tab, browser, order_url)
                if not menu_json:
                    print(
                        f"No menu JSON captured for {location['name']}; "
                        "recycling this browser and marking store for retry."
                    )
                    return None, True

                location["_menu_json"] = menu_json
                location["menu"] = parse_menu_json(menu_json)
                print(f"Menu items: {len(location['menu'])}")
                append_menu_to_csv(location)
                if SCRAPE_CLASSIC_COMBO:
                    combo_items = await fetch_classic_combo_items(
                        tab,
                        location,
                        browser,
                    )
                    if (
                        not combo_items
                        and not location.get("_classic_combo_unavailable")
                    ):
                        print(
                            f"Classic Combo scrape for {location['name']} returned "
                            "0 rows."
                        )
                    elif combo_items and not any(
                        not is_classic_combo_product_row(row)
                        for row in combo_items
                    ):
                        detail_status = (
                            combo_items[0].get("detail_status")
                            or "detail_options_not_captured"
                        )
                        print(
                            f"Classic Combo product is listed for {location['name']}, "
                            f"but full option rows were not captured ({detail_status})."
                        )
                        append_scrape_failure_to_csv(
                            location.get("name"),
                            location.get("order_url"),
                            "classic_combo_detail",
                            detail_status,
                        )
                    location["classic_combo_items"] = combo_items
                    append_classic_combo_to_csv(location)
                else:
                    location["classic_combo_items"] = []
                    print(f"Skipping Classic Combo scrape for {location['name']}.")

                if SCRAPE_MILKSHAKE_MIXINS:
                    milkshake_mixin_items = await fetch_milkshake_mixin_items(
                        tab,
                        location,
                        browser,
                    )
                    if (
                        get_milkshake_menu_item(location)
                        and not location.get("_milkshake_unavailable")
                        and len(milkshake_mixin_items) < MILKSHAKE_MIN_EXPECTED_ROWS
                    ):
                        print(
                            f"Milkshake mix-in scrape for {location['name']} returned "
                            f"{len(milkshake_mixin_items)} rows after bounded "
                            "direct/page attempts."
                        )
                    location["milkshake_mixin_items"] = milkshake_mixin_items
                    append_milkshake_mixins_to_csv(location)
                else:
                    location["milkshake_mixin_items"] = []
                    print(f"Skipping Milkshake mix-in scrape for {location['name']}.")
            else:
                print(f"No order URL found for {location['name']}")

            print(f"Done: {location['name']}")
            return location, recycle_browser
        except Exception as e:
            if is_browser_command_timeout(e):
                recycle_browser = True

            print(
                f"Failed while scraping {name or url} "
                f"(attempt {attempt}/{SCRAPE_LOCATION_ATTEMPTS}): {e}"
            )
            if recycle_browser:
                print(
                    f"Browser command timeout while scraping {name or url}; "
                    "recycling this worker browser before the next store."
                )
                return None, recycle_browser
            if attempt >= SCRAPE_LOCATION_ATTEMPTS:
                return None, recycle_browser

    return None, recycle_browser


async def start_worker_browser(
    worker_id,
    worker_label,
    base_profile_dir,
    run_namespace,
    cycle_index,
    startup_semaphore,
    session_cookies=None,
):
    profile_dir = worker_profile_dir(run_namespace, worker_id, cycle_index)

    async with startup_semaphore:
        last_error = None
        for attempt in range(1, WORKER_BROWSER_START_ATTEMPTS + 1):
            browser = None
            print(
                f"{worker_label} is preparing browser cycle {cycle_index} "
                f"with profile: {profile_dir} "
                f"(attempt {attempt}/{WORKER_BROWSER_START_ATTEMPTS})"
            )
            try:
                clone_base_profile_to_worker(base_profile_dir, profile_dir)
                options = build_chrome_options(profile_dir)
                browser = Chrome(options=options)
                initial_tab = await browser.start()

                if session_cookies:
                    await inject_session_cookies(initial_tab, session_cookies)

                print(f"{worker_label} is bootstrapping Cloudflare session...")
                await ensure_initial_order_session(initial_tab, browser)

                print(
                    f"{worker_label} started browser cycle {cycle_index} "
                    f"with reusable store tab."
                )
                return browser, initial_tab
            except Exception as e:
                last_error = e
                if browser is not None:
                    with suppress(Exception):
                        await close_browser_safely(browser)
                if attempt >= WORKER_BROWSER_START_ATTEMPTS:
                    break
                print(
                    f"{worker_label} browser start/bootstrap failed: {e}. "
                    f"Retrying in {WORKER_BROWSER_START_RETRY_SECONDS:g}s."
                )
                await asyncio.sleep(WORKER_BROWSER_START_RETRY_SECONDS)

        raise last_error or RuntimeError(f"{worker_label} failed to start browser.")


async def browser_worker(
    worker_id,
    location_queue,
    base_profile_dir,
    run_namespace,
    startup_semaphore,
    session_cookies=None,
    record_failures=True,
):
    worker_label = f"Worker {worker_id}"
    browser = None
    tab = None
    cycle_index = 0
    stores_since_recycle = 0
    worker_locations = []
    failed_location_entries = []

    try:
        while True:
            location_entry = await location_queue.get()
            try:
                if location_entry is None:
                    return {
                        "locations": worker_locations,
                        "failed_entries": failed_location_entries,
                    }

                _slug, url, name, cid, google_maps_url = location_entry
                print(f"{worker_label} picked up: {name}")

                if browser is None:
                    try:
                        browser, tab = await start_worker_browser(
                            worker_id,
                            worker_label,
                            base_profile_dir,
                            run_namespace,
                            cycle_index,
                            startup_semaphore,
                            session_cookies,
                        )
                    except Exception as e:
                        print(f"{worker_label} failed to start before {name}: {e}")
                        failed_location_entries.append(location_entry)
                        if record_failures:
                            append_scrape_failure_to_csv(
                                name,
                                url,
                                "worker_start",
                                str(e),
                            )
                        return {
                            "locations": worker_locations,
                            "failed_entries": failed_location_entries,
                        }

                failure_recorded = False
                try:
                    location, recycle_requested = await asyncio.wait_for(
                        scrape_location(
                            url,
                            cid,
                            google_maps_url,
                            name,
                            browser,
                            tab,
                        ),
                        timeout=SCRAPE_LOCATION_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    location = None
                    recycle_requested = True
                    reason = (
                        f"store exceeded {SCRAPE_LOCATION_TIMEOUT_SECONDS}s "
                        "hard timeout"
                    )
                    print(f"{worker_label} timed out on {name}: {reason}")
                    if record_failures:
                        append_scrape_failure_to_csv(name, url, "store_timeout", reason)
                    failure_recorded = True
                except Exception as e:
                    location = None
                    recycle_requested = is_browser_command_timeout(e)
                    print(f"{worker_label} failed on {name}: {e}")
                    if record_failures:
                        append_scrape_failure_to_csv(
                            name,
                            url,
                            "store_scrape",
                            str(e),
                        )
                    failure_recorded = True
                stores_since_recycle += 1
                if location is not None:
                    worker_locations.append(location)
                else:
                    failed_location_entries.append(location_entry)
                    if record_failures and not failure_recorded:
                        append_scrape_failure_to_csv(
                            name,
                            url,
                            "store_scrape",
                            "location returned no rows",
                        )

                recycle_reason = None
                if recycle_requested:
                    recycle_reason = f"browser command timeout after {name}"
                elif (
                    WORKER_BROWSER_RECYCLE_STORES > 0
                    and stores_since_recycle >= WORKER_BROWSER_RECYCLE_STORES
                ):
                    recycle_reason = f"{stores_since_recycle} stores processed"

                if recycle_reason:
                    cycle_index += 1
                    print(
                        f"{worker_label} recycling browser "
                        f"({recycle_reason})."
                    )
                    await close_browser_safely(browser)
                    browser = None
                    tab = None
                    if WORKER_BROWSER_RECYCLE_PAUSE_SECONDS > 0:
                        await asyncio.sleep(WORKER_BROWSER_RECYCLE_PAUSE_SECONDS)
                    stores_since_recycle = 0
            finally:
                location_queue.task_done()
    except Exception as e:
        print(f"{worker_label} failed to start or crashed: {e}")
        return {
            "locations": worker_locations,
            "failed_entries": failed_location_entries,
        }
    finally:
        if browser is not None:
            await close_browser_safely(browser)


async def classic_combo_worker(
    worker_id,
    location_queue,
    base_profile_dir,
    run_namespace,
    startup_semaphore,
    session_cookies=None,
):
    worker_label = f"Classic Combo worker {worker_id}"
    browser = None
    tab = None
    cycle_index = 0
    stores_since_recycle = 0
    worker_locations = []

    try:
        browser, tab = await start_worker_browser(
            worker_id,
            worker_label,
            base_profile_dir,
            run_namespace,
            cycle_index,
            startup_semaphore,
            session_cookies,
        )

        while True:
            location = await location_queue.get()
            try:
                if location is None:
                    return worker_locations

                name = location.get("name") or location.get("order_url")
                print(f"{worker_label} picked up: {name}")
                combo_items = []
                recycle_requested = False

                try:
                    combo_items = await fetch_classic_combo_items(
                        tab,
                        location,
                        browser,
                    )
                    if (
                        len(combo_items) < CLASSIC_COMBO_MIN_EXPECTED_ROWS
                        and not location.get("_classic_combo_unavailable")
                        and CLASSIC_COMBO_PAGE_FALLBACK
                    ):
                        print(
                            f"Classic Combo recovery for {name} returned "
                            f"{len(combo_items)} rows; retrying once."
                        )
                        combo_items = await fetch_classic_combo_items(
                            tab,
                            location,
                            browser,
                        )
                except asyncio.TimeoutError:
                    recycle_requested = True
                    reason = (
                        f"classic combo exceeded {classic_combo_timeout_seconds(location)}s "
                        "hard timeout"
                    )
                    print(f"{worker_label} timed out on {name}: {reason}")
                    combo_items = classic_combo_product_presence_rows(
                        location,
                        detail_status="detail_timeout",
                    )
                    if combo_items:
                        print(
                            f"Classic Combo product is listed for {name}; "
                            "saved product-level row after detail timeout."
                        )
                    append_scrape_failure_to_csv(
                        name,
                        location.get("order_url"),
                        "classic_combo_timeout",
                        reason,
                    )
                except Exception as e:
                    recycle_requested = is_browser_command_timeout(e)
                    print(f"{worker_label} failed on {name}: {e}")
                    append_scrape_failure_to_csv(
                        name,
                        location.get("order_url"),
                        "classic_combo",
                        str(e),
                    )

                location["classic_combo_items"] = combo_items
                append_classic_combo_to_csv(location)
                worker_locations.append(location)
                stores_since_recycle += 1

                if combo_items:
                    if any(
                        not is_classic_combo_product_row(row)
                        for row in combo_items
                    ):
                        print(f"Classic Combo recovery rows: {len(combo_items)} for {name}")
                    else:
                        detail_status = (
                            combo_items[0].get("detail_status")
                            or "detail_options_not_captured"
                        )
                        print(
                            f"Classic Combo product is listed for {name}, but full "
                            f"option rows were not captured ({detail_status})."
                        )
                else:
                    print(f"Classic Combo recovery captured 0 rows for {name}.")

                recycle_reason = None
                if recycle_requested:
                    recycle_reason = f"browser command timeout after {name}"
                elif (
                    WORKER_BROWSER_RECYCLE_STORES > 0
                    and stores_since_recycle >= WORKER_BROWSER_RECYCLE_STORES
                ):
                    recycle_reason = f"{stores_since_recycle} stores processed"

                if recycle_reason:
                    cycle_index += 1
                    print(
                        f"{worker_label} recycling browser "
                        f"({recycle_reason})."
                    )
                    await close_browser_safely(browser)
                    browser = None
                    tab = None
                    if WORKER_BROWSER_RECYCLE_PAUSE_SECONDS > 0:
                        await asyncio.sleep(WORKER_BROWSER_RECYCLE_PAUSE_SECONDS)
                    browser, tab = await start_worker_browser(
                        worker_id,
                        worker_label,
                        base_profile_dir,
                        run_namespace,
                        cycle_index,
                        startup_semaphore,
                        session_cookies,
                    )
                    stores_since_recycle = 0
            finally:
                location_queue.task_done()
    except Exception as e:
        print(f"{worker_label} failed to start or crashed: {e}")
        return worker_locations
    finally:
        if browser is not None:
            await close_browser_safely(browser)


def drain_unprocessed_location_entries(location_queue):
    pending_entries = []
    while not location_queue.empty():
        try:
            location_entry = location_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if location_entry is not None:
            pending_entries.append(location_entry)
    return pending_entries


def collect_browser_worker_results(worker_results, location_queue):
    locations = []
    failed_entries = []

    for result in worker_results:
        if isinstance(result, Exception):
            print(f"Worker error: {result}")
            continue

        if isinstance(result, dict):
            locations.extend(result.get("locations") or [])
            failed_entries.extend(result.get("failed_entries") or [])
        else:
            locations.extend(result or [])

    failed_entries.extend(drain_unprocessed_location_entries(location_queue))
    return locations, dedupe_location_entries(failed_entries)


def csv_row_count(path):
    if not path.exists():
        return 0
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            return sum(1 for _row in csv.DictReader(f))
    except Exception:
        return 0


def format_elapsed_seconds(elapsed_seconds):
    elapsed_seconds = max(0, float(elapsed_seconds or 0))
    total_seconds = int(round(elapsed_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def print_elapsed_time(started_at, label="Run"):
    elapsed_seconds = time.perf_counter() - started_at
    print(
        f"{label} elapsed time: "
        f"{format_elapsed_seconds(elapsed_seconds)} "
        f"({elapsed_seconds:.1f}s)."
    )


def run_before_google_reviews_command():
    if not BEFORE_GOOGLE_REVIEWS_COMMAND:
        return

    print(
        "Running before-Google-reviews command: "
        f"{BEFORE_GOOGLE_REVIEWS_COMMAND}"
    )
    try:
        result = subprocess.run(
            BEFORE_GOOGLE_REVIEWS_COMMAND,
            shell=True,
            text=True,
            capture_output=True,
            timeout=BEFORE_GOOGLE_REVIEWS_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(
            "Before-Google-reviews command timed out after "
            f"{BEFORE_GOOGLE_REVIEWS_COMMAND_TIMEOUT_SECONDS}s; continuing."
        )
        return
    except Exception as e:
        print(f"Before-Google-reviews command failed to run: {e}; continuing.")
        return

    if result.stdout.strip():
        print("Before-Google-reviews command stdout:")
        print(result.stdout.strip())
    if result.stderr.strip():
        print("Before-Google-reviews command stderr:")
        print(result.stderr.strip())

    if result.returncode != 0:
        print(
            "Before-Google-reviews command exited with "
            f"code {result.returncode}; continuing."
        )
    else:
        print("Before-Google-reviews command finished successfully.")

    if BEFORE_GOOGLE_REVIEWS_WAIT_SECONDS > 0:
        print(
            f"Waiting {BEFORE_GOOGLE_REVIEWS_WAIT_SECONDS:g}s before "
            "starting Google reviews."
        )
        time.sleep(BEFORE_GOOGLE_REVIEWS_WAIT_SECONDS)


async def collect_warmed_order_session_cookies():
    last_bootstrap_error = None

    for bootstrap_attempt in range(1, BOOTSTRAP_SESSION_ATTEMPTS + 1):
        browser = Chrome(options=build_bootstrap_chrome_options())
        try:
            if bootstrap_attempt > 1:
                print(
                    f"Retrying initial Cloudflare/session bootstrap "
                    f"({bootstrap_attempt}/{BOOTSTRAP_SESSION_ATTEMPTS})."
                )

            initial_tab = await browser.start()
            await ensure_initial_order_session(initial_tab, browser)

            session_cookies = await collect_session_cookies(initial_tab)
            if not session_cookies:
                raise RuntimeError(
                    "Initial Cloudflare bootstrap looked ready, but no reusable "
                    "session cookies were captured."
                )
            return session_cookies
        except Exception as e:
            last_bootstrap_error = e
            if bootstrap_attempt >= BOOTSTRAP_SESSION_ATTEMPTS:
                if isinstance(e, ManagedCloudflareChallengeError):
                    raise RuntimeError(
                        "Base profile never reached a known-good warmed Five Guys "
                        "session, so worker fan-out is being aborted. "
                        f"{e}"
                    ) from e
                raise

            print(
                f"Initial Cloudflare/session bootstrap failed: {e}. "
                f"Retrying in {BOOTSTRAP_SESSION_RETRY_SECONDS:g}s."
            )
            await asyncio.sleep(BOOTSTRAP_SESSION_RETRY_SECONDS)
        finally:
            await close_browser_safely(browser)

    raise RuntimeError(
        "Initial browser session did not produce reusable cookies. "
        f"Last error: {last_bootstrap_error}"
    )


async def run_browser_worker_batch(
    location_entries,
    worker_count,
    base_profile_dir,
    run_namespace,
    startup_semaphore,
    session_cookies,
    record_failures,
):
    location_queue = asyncio.Queue()
    for slug, url, name, cid, google_maps_url in location_entries:
        print(f"Queuing: {name or slug or url}")
        await location_queue.put((slug, url, name, cid, google_maps_url))

    for _ in range(worker_count):
        await location_queue.put(None)

    worker_tasks = [
        asyncio.create_task(
            browser_worker(
                worker_id,
                location_queue,
                base_profile_dir,
                run_namespace,
                startup_semaphore,
                session_cookies,
                record_failures=record_failures,
            )
        )
        for worker_id in range(1, worker_count + 1)
    ]
    worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
    return collect_browser_worker_results(worker_results, location_queue)


def print_core_run_summary(locations, failed_entries, reviewed_locations=None):
    location_row_count = csv_row_count(LOCATIONS_CSV_PATH)
    menu_store_count = sum(1 for location in locations if location.get("menu"))
    menu_row_count = sum(len(location.get("menu") or []) for location in locations)
    combo_store_count = sum(
        1 for location in locations if classic_combo_item_rows(location)
    )
    combo_row_count = sum(
        len(classic_combo_item_rows(location))
        for location in locations
    )
    milkshake_store_count = sum(
        1 for location in locations if location.get("milkshake_mixin_items")
    )
    milkshake_row_count = sum(
        len(location.get("milkshake_mixin_items") or [])
        for location in locations
    )
    reviewed_locations = reviewed_locations or []
    review_store_count = sum(
        1 for location in reviewed_locations if location.get("reviews")
    )
    review_row_count = sum(
        len(location.get("reviews") or [])
        for location in reviewed_locations
    )

    print(
        "Run summary: "
        f"completed_core_stores={len(locations)}, "
        f"location_rows={location_row_count}, "
        f"menu_stores={menu_store_count}, menu_rows={menu_row_count}, "
        f"classic_combo_stores={combo_store_count}, classic_combo_rows={combo_row_count}, "
        f"milkshake_stores={milkshake_store_count}, milkshake_rows={milkshake_row_count}, "
        f"google_review_stores={review_store_count}, google_review_rows={review_row_count}, "
        f"failed_stores={len(failed_entries)}."
    )
    if failed_entries:
        failed_names = ", ".join(
            name or url
            for _slug, url, name, _cid, _google_maps_url in failed_entries
        )
        print(f"Failed stores: {failed_names}")


def print_failed_store_retry_summary(attempted_count, recovered_locations, failed_entries):
    recovered_count = len(recovered_locations)
    print(
        "Failed-store retry summary: "
        f"attempted={attempted_count}, recovered={recovered_count}, "
        f"still_failed={len(failed_entries)}, "
        f"location_rows={csv_row_count(LOCATIONS_CSV_PATH)}, "
        f"menu_rows={csv_row_count(MENU_ITEMS_CSV_PATH)}, "
        f"classic_combo_rows={csv_row_count(CLASSIC_COMBO_CSV_PATH)}, "
        f"milkshake_rows={csv_row_count(MILKSHAKE_MIXIN_CSV_PATH)}, "
        f"google_review_rows={csv_row_count(GOOGLE_REVIEWS_CSV_PATH)}."
    )
    if failed_entries:
        failed_names = ", ".join(
            name or url
            for _slug, url, name, _cid, _google_maps_url in failed_entries
        )
        print(f"Still failed stores: {failed_names}")


async def main_failed_stores_only():
    started_at = time.perf_counter()
    try:
        retry_entries, retained_failure_rows = load_failed_store_retry_entries()
        if not retry_entries:
            print(
                "No store-level failures found in scrape_failures.csv for "
                f"stages: {', '.join(sorted(FAILED_STORE_RETRY_STAGES))}."
            )
            return

        print(
            f"Retrying {len(retry_entries)} failed "
            f"{'store' if len(retry_entries) == 1 else 'stores'} from "
            "scrape_failures.csv."
        )

        prime_incremental_csv_duplicate_guards()
        write_scrape_failures_csv(retained_failure_rows)

        session_cookies = await collect_warmed_order_session_cookies()
        base_profile_dir = Path(CHROME_USER_DATA_DIR)
        run_namespace = time.strftime("failed-stores-%Y%m%d-%H%M%S")
        worker_count = min(FAILED_STORE_RETRY_CONCURRENCY, len(retry_entries))
        startup_semaphore = asyncio.Semaphore(WORKER_BOOTSTRAP_CONCURRENCY)

        print(
            f"Base profile warmed successfully; retrying failures with "
            f"{worker_count} worker {'browser' if worker_count == 1 else 'browsers'}."
        )

        recovered_locations, failed_entries = await run_browser_worker_batch(
            retry_entries,
            worker_count,
            base_profile_dir,
            run_namespace,
            startup_semaphore,
            session_cookies,
            record_failures=False,
        )

        for _slug, url, name, _cid, _google_maps_url in failed_entries:
            append_scrape_failure_to_csv(
                name,
                url,
                "store_unrecovered",
                "store failed during failed-store retry mode",
            )

        if recovered_locations and (
            SCRAPER_MODE in (
                "failed_stores_with_reviews",
                "retry_failed_with_reviews",
                "failures_with_reviews",
            )
            or RUN_GOOGLE_REVIEWS_AFTER_CORE
        ):
            run_before_google_reviews_command()
            await scrape_google_reviews_for_locations(
                recovered_locations,
                reset_csv_file=False,
            )

        merge_recovered_locations_csv(recovered_locations)
        merge_recovered_output_json(recovered_locations)
        print_failed_store_retry_summary(
            len(retry_entries),
            recovered_locations,
            failed_entries,
        )
    finally:
        print_elapsed_time(started_at, "Failed-store retry run")


async def main_classic_combo_only():
    started_at = time.perf_counter()
    locations = load_saved_locations_for_classic_combo()
    try:
        if not locations:
            raise RuntimeError(
                "No saved locations with order URLs were available for Classic Combo recovery."
            )

        base_profile_dir = Path(CHROME_USER_DATA_DIR)
        options = build_bootstrap_chrome_options()
        browser = Chrome(options=options)
        run_namespace = time.strftime("combo-%Y%m%d-%H%M%S")
        session_cookies = []

        try:
            initial_tab = await browser.start()
            await ensure_initial_order_session(initial_tab, browser)

            session_cookies = await collect_session_cookies(initial_tab)
            if not session_cookies:
                raise RuntimeError(
                    "Initial Cloudflare bootstrap looked ready, but no reusable session "
                    "cookies were captured. Refusing to fan out worker browsers from "
                    "an unwarmed base profile."
                )
        except ManagedCloudflareChallengeError as e:
            raise RuntimeError(
                "Base profile never reached a known-good warmed Five Guys session, "
                "so Classic Combo recovery is being aborted. "
                f"{e}"
            ) from e
        finally:
            await close_browser_safely(browser)

        worker_count = min(SCRAPE_CONCURRENCY, len(locations))
        print(
            f"Base profile warmed successfully; starting Classic Combo recovery with "
            f"{worker_count} worker {'browser' if worker_count == 1 else 'browsers'}."
        )

        reset_classic_combo_csv()

        startup_semaphore = asyncio.Semaphore(WORKER_BOOTSTRAP_CONCURRENCY)
        location_queue = asyncio.Queue()
        for location in locations:
            print(
                "Queuing Classic Combo recovery: "
                f"{location.get('name') or location.get('order_url')}"
            )
            await location_queue.put(location)

        for _ in range(worker_count):
            await location_queue.put(None)

        worker_tasks = [
            asyncio.create_task(
                classic_combo_worker(
                    worker_id,
                    location_queue,
                    base_profile_dir,
                    run_namespace,
                    startup_semaphore,
                    session_cookies,
                )
            )
            for worker_id in range(1, worker_count + 1)
        ]
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

        recovered_locations = []
        for result in worker_results:
            if isinstance(result, Exception):
                print(f"Classic Combo worker error: {result}")
                continue
            recovered_locations.extend(result)

        export_classic_combo_to_json(recovered_locations)
        row_count = sum(
            len(classic_combo_item_rows(location))
            for location in recovered_locations
        )
        store_count = sum(
            1
            for location in recovered_locations
            if classic_combo_item_rows(location)
        )
        print(
            f"Classic Combo recovery finished: {row_count} rows across "
            f"{store_count}/{len(recovered_locations)} processed stores."
        )
    finally:
        print_elapsed_time(started_at, "Classic Combo run")


async def main():
    started_at = time.perf_counter()
    locations = []
    base_profile_dir = Path(CHROME_USER_DATA_DIR)
    run_namespace = time.strftime("run-%Y%m%d-%H%M%S")
    session_cookies = []
    location_entries = []
    last_bootstrap_error = None

    for bootstrap_attempt in range(1, BOOTSTRAP_SESSION_ATTEMPTS + 1):
        browser = Chrome(options=build_bootstrap_chrome_options())
        try:
            if bootstrap_attempt > 1:
                print(
                    f"Retrying initial Cloudflare/session bootstrap "
                    f"({bootstrap_attempt}/{BOOTSTRAP_SESSION_ATTEMPTS})."
                )

            initial_tab = await browser.start()
            await ensure_initial_order_session(initial_tab, browser)

            session_cookies = await collect_session_cookies(initial_tab)
            if not session_cookies:
                raise RuntimeError(
                    "Initial Cloudflare bootstrap looked ready, but no reusable "
                    "session cookies were captured."
                )

            if FIVE_GUYS_LOCATION_URLS:
                location_entries = parse_location_url_entries(FIVE_GUYS_LOCATION_URLS)
                print(
                    f"Using {len(location_entries)} location URL "
                    f"{'entry' if len(location_entries) == 1 else 'entries'} "
                    "from FIVE_GUYS_LOCATION_URLS."
                )
            else:
                location_entries = await discover_location_entries(initial_tab)

            if not location_entries:
                raise RuntimeError(
                    "No Five Guys locations were available. Set FIVE_GUYS_LOCATION_URLS "
                    f"to one or more restaurants.fiveguys.com store URLs, or check "
                    f"FIVE_GUYS_DIRECTORY_ROOT_URL={FIVE_GUYS_DIRECTORY_ROOT_URL!r}."
                )
            break
        except Exception as e:
            last_bootstrap_error = e
            if bootstrap_attempt >= BOOTSTRAP_SESSION_ATTEMPTS:
                if isinstance(e, ManagedCloudflareChallengeError):
                    raise RuntimeError(
                        "Base profile never reached a known-good warmed Five Guys "
                        "session, so worker fan-out is being aborted. "
                        f"{e}"
                    ) from e
                raise

            print(
                f"Initial Cloudflare/session bootstrap failed: {e}. "
                f"Retrying in {BOOTSTRAP_SESSION_RETRY_SECONDS:g}s."
            )
            await asyncio.sleep(BOOTSTRAP_SESSION_RETRY_SECONDS)
        finally:
            await close_browser_safely(browser)

    if not session_cookies or not location_entries:
        raise RuntimeError(
            "Initial browser session did not produce reusable cookies/location "
            f"entries. Last error: {last_bootstrap_error}"
        )

    worker_count = min(SCRAPE_CONCURRENCY, len(location_entries))
    print(
        f"Base profile warmed successfully; starting {worker_count} worker "
        f"{'browser' if worker_count == 1 else 'browsers'} from "
        f"{CHROME_WORKER_PROFILE_ROOT}."
    )
    startup_semaphore = asyncio.Semaphore(WORKER_BOOTSTRAP_CONCURRENCY)

    reset_locations_csv()
    reset_menu_csv()
    reset_scrape_failures_csv()
    reset_classic_combo_csv()
    reset_milkshake_mixins_csv()

    first_pass_locations, failed_location_entries = await run_browser_worker_batch(
        location_entries,
        worker_count,
        base_profile_dir,
        run_namespace,
        startup_semaphore,
        session_cookies,
        record_failures=False,
    )
    locations.extend(first_pass_locations)

    if failed_location_entries:
        retry_worker_count = min(
            FAILED_STORE_RETRY_CONCURRENCY,
            len(failed_location_entries),
        )
        print(
            f"Retrying {len(failed_location_entries)} failed "
            f"{'store' if len(failed_location_entries) == 1 else 'stores'} "
            f"with {retry_worker_count} low-concurrency worker "
            f"{'browser' if retry_worker_count == 1 else 'browsers'}."
        )
        retry_locations, retry_failed_entries = await run_browser_worker_batch(
            failed_location_entries,
            retry_worker_count,
            base_profile_dir,
            f"{run_namespace}-retry",
            asyncio.Semaphore(1),
            session_cookies,
            record_failures=False,
        )
        locations.extend(retry_locations)
        failed_location_entries = retry_failed_entries
        for _slug, url, name, _cid, _google_maps_url in failed_location_entries:
            append_scrape_failure_to_csv(
                name,
                url,
                "store_unrecovered",
                "store failed after first pass and one automatic retry",
            )
    else:
        failed_location_entries = []

    export_locations_to_json(locations)
    export_menu_to_json(locations)
    export_classic_combo_to_json(locations)
    export_milkshake_mixins_to_json(locations)

    reviewed_locations = []
    if SCRAPER_MODE in ("full_with_reviews", "all") or RUN_GOOGLE_REVIEWS_AFTER_CORE:
        run_before_google_reviews_command()
        reviewed_locations, _target_review_locations = (
            await scrape_google_reviews_from_saved_locations()
        )
        merge_google_review_fields(locations, reviewed_locations)
    else:
        print(
            "Core scrape finished. Google reviews are skipped in this run; "
            "run with SCRAPER_MODE=google_reviews after checking locations.csv."
        )

    print_core_run_summary(locations, failed_location_entries, reviewed_locations)
    print_elapsed_time(started_at)

if __name__ == "__main__":
    setup_terminal_log()
    try:
        if SCRAPER_MODE in ("google_reviews", "reviews", "maps_reviews"):
            asyncio.run(main_google_reviews_only())
        elif SCRAPER_MODE in ("classic_combo", "classic_combos", "combo", "combos"):
            asyncio.run(main_classic_combo_only())
        elif SCRAPER_MODE in (
            "failed_stores",
            "retry_failed",
            "failures",
            "failed_stores_with_reviews",
            "retry_failed_with_reviews",
            "failures_with_reviews",
        ):
            asyncio.run(main_failed_stores_only())
        else:
            asyncio.run(main())
    finally:
        close_terminal_log()
