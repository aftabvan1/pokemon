"""Session and cookie management with JWT auth and bot protection tracking."""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote

import httpx

from . import logger
from .endpoints import BASE_URL, REQUIRED_COOKIES

log = logger.get("SESSION")

COOKIES_DIR = Path("data")
DEFAULT_COOKIES_PATH = COOKIES_DIR / "cookies.json"
SESSION_EXPIRY = 3600  # 1 hour


def extract_auth_token(cookies_list: List[dict]) -> Optional[str]:
    """
    Extract JWT access_token from the 'auth' cookie.

    The auth cookie contains a JSON object like:
    {
        "access_token": "<token>",
        "token_type": "bearer",
        "expires_in": 604799,
        ...
    }
    """
    for cookie in cookies_list:
        if cookie.get("name") == "auth":
            try:
                # Cookie value may be URL-encoded JSON
                value = unquote(cookie.get("value", ""))
                auth_data = json.loads(value)
                token = auth_data.get("access_token")
                if token:
                    log.debug("Extracted auth token from cookie")
                    return token
            except (json.JSONDecodeError, TypeError) as e:
                log.warning(f"Failed to parse auth cookie: {e}")
    return None


def extract_auth_expiry(cookies_list: List[dict]) -> float:
    """Extract token expiry timestamp from auth cookie."""
    for cookie in cookies_list:
        if cookie.get("name") == "auth":
            try:
                value = unquote(cookie.get("value", ""))
                auth_data = json.loads(value)
                expires_in = auth_data.get("expires_in", 0)
                if expires_in:
                    return time.time() + expires_in
            except (json.JSONDecodeError, TypeError):
                pass
    return 0


def validate_required_cookies(cookies_list: List[dict]) -> List[str]:
    """
    Check if all required bot protection cookies are present.

    Returns list of missing cookie names.
    """
    present = {c.get("name") for c in cookies_list}
    missing = []

    for required in REQUIRED_COOKIES:
        # Handle wildcard patterns like "incap_ses_*"
        if required.endswith("*"):
            prefix = required[:-1]
            if not any(name.startswith(prefix) for name in present):
                missing.append(required)
        elif required not in present:
            missing.append(required)

    return missing


def get_cookie_value(cookies_list: List[dict], name: str) -> Optional[str]:
    """Get a specific cookie value by name."""
    for cookie in cookies_list:
        if cookie.get("name") == name:
            return cookie.get("value")
    return None


@dataclass
class Session:
    """A single session with cookies, JWT auth, and bot protection tracking."""

    name: str
    cookies: str
    csrf_token: Optional[str] = None
    last_validated: float = 0
    is_valid: bool = True

    # JWT authentication
    auth_token: Optional[str] = None
    auth_expires_at: float = 0

    # Bot protection cookies
    reese84_token: Optional[str] = None
    datadome_token: Optional[str] = None

    # Raw cookie list for re-extraction
    _raw_cookies: List[dict] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path, name: str = "default") -> "Session":
        """Load session from cookies file with JWT extraction."""
        if not path.exists():
            raise FileNotFoundError(f"No cookies at {path}")

        raw_cookies = json.loads(path.read_text())
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in raw_cookies)

        # Validate required cookies
        missing = validate_required_cookies(raw_cookies)
        if missing:
            log.warning(f"Missing bot protection cookies: {', '.join(missing)}")

        # Extract JWT auth token
        auth_token = extract_auth_token(raw_cookies)
        auth_expires_at = extract_auth_expiry(raw_cookies)

        if auth_token:
            log.info(f"Session '{name}' has valid auth token")
        else:
            log.warning(f"Session '{name}' has no auth token - may need to re-login")

        # Extract bot protection tokens
        reese84 = get_cookie_value(raw_cookies, "reese84")
        datadome = get_cookie_value(raw_cookies, "datadome")

        return cls(
            name=name,
            cookies=cookie_str,
            last_validated=time.time(),
            auth_token=auth_token,
            auth_expires_at=auth_expires_at,
            reese84_token=reese84,
            datadome_token=datadome,
            _raw_cookies=raw_cookies,
        )

    def needs_refresh(self) -> bool:
        """Check if session needs refresh (expired or stale)."""
        # Check JWT expiry
        if self.auth_expires_at > 0 and time.time() > self.auth_expires_at:
            log.warning("Auth token expired")
            return True

        # Check last validation time
        return time.time() - self.last_validated > SESSION_EXPIRY

    def has_bot_protection(self) -> bool:
        """Check if bot protection cookies are present."""
        return bool(self.reese84_token and self.datadome_token)


@dataclass
class SessionManager:
    """Manages multiple sessions with validation and refresh."""

    sessions: Dict[str, Session] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def load(self, name: str = "default", path: Optional[Path] = None) -> Session:
        """Load a session from file."""
        path = path or DEFAULT_COOKIES_PATH
        session = Session.from_file(path, name)
        self.sessions[name] = session
        log.success(f"Loaded session '{name}' (auth: {'yes' if session.auth_token else 'no'})")
        return session

    def get(self, name: str = "default") -> Session:
        """Get a session by name."""
        if name not in self.sessions:
            raise KeyError(f"Session '{name}' not loaded")
        return self.sessions[name]

    async def validate(self, name: str = "default") -> bool:
        """Validate session by making a test request."""
        async with self._lock:
            session = self.get(name)

            try:
                headers = {"Cookie": session.cookies}
                if session.auth_token:
                    headers["Authorization"] = f"Bearer {session.auth_token}"

                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        BASE_URL,
                        headers=headers,
                        follow_redirects=True,
                    )

                    # Check if we're still logged in
                    session.is_valid = r.status_code == 200
                    session.last_validated = time.time()

                    if session.is_valid:
                        log.info(f"Session '{name}' validated")
                    else:
                        log.warning(f"Session '{name}' invalid ({r.status_code})")

                    return session.is_valid

            except httpx.RequestError as e:
                log.error(f"Validation failed: {e}")
                return False

    async def warm(self, name: str = "default") -> bool:
        """
        Warm up session by making initial request.
        Extracts CSRF tokens if present.
        """
        session = self.get(name)

        try:
            headers = {"Cookie": session.cookies}
            if session.auth_token:
                headers["Authorization"] = f"Bearer {session.auth_token}"

            async with httpx.AsyncClient() as client:
                r = await client.get(
                    BASE_URL,
                    headers=headers,
                    follow_redirects=True,
                )

                # Try to extract CSRF token from response
                text = r.text
                if 'csrf' in text.lower():
                    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', text)
                    if match:
                        session.csrf_token = match.group(1)
                        log.info(f"Extracted CSRF token for '{name}'")

                # Check response headers for CSRF
                if 'x-csrf-token' in r.headers:
                    session.csrf_token = r.headers['x-csrf-token']
                    log.info(f"Extracted CSRF token from header for '{name}'")

                # Also check cookies for CSRF
                for cookie in r.cookies.jar:
                    if 'csrf' in cookie.name.lower():
                        session.csrf_token = cookie.value
                        break

                session.last_validated = time.time()
                session.is_valid = True
                log.success(f"Session '{name}' warmed up")
                return True

        except httpx.RequestError as e:
            log.error(f"Warm-up failed: {e}")
            return False

    async def ensure_valid(self, name: str = "default") -> bool:
        """Ensure session is valid, refresh if needed."""
        session = self.get(name)

        if session.needs_refresh():
            return await self.validate(name)

        return session.is_valid


# Legacy functions for backwards compatibility
def load_cookies(path: Optional[Path] = None) -> str:
    """Load cookies from file as header string."""
    path = path or DEFAULT_COOKIES_PATH
    if not path.exists():
        raise FileNotFoundError("No cookies. Run 'login' command first.")

    cookies = json.loads(path.read_text())
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def load_session(path: Optional[Path] = None) -> Session:
    """Load full session with JWT extraction."""
    path = path or DEFAULT_COOKIES_PATH
    return Session.from_file(path)


def save_cookies(cookies: List[dict], path: Optional[Path] = None) -> None:
    """Save cookies to file."""
    path = path or DEFAULT_COOKIES_PATH
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(cookies, indent=2))
    log.success(f"Saved {len(cookies)} cookies to {path}")


async def capture_session(name: str = "default") -> None:
    """Open browser for manual login and capture cookies."""
    from playwright.async_api import async_playwright

    log.info("Launching browser for login...")
    log.info("IMPORTANT: Bot protection cookies (reese84, datadome) will be captured automatically")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE_URL)
        log.info("Log in manually, then press Enter in terminal...")

        # Wait for user input (blocking)
        await asyncio.get_event_loop().run_in_executor(None, input)

        cookies = await context.cookies()

        # Validate we got the critical cookies
        missing = validate_required_cookies(cookies)
        if missing:
            log.warning(f"Missing cookies after login: {', '.join(missing)}")
            log.warning("Some features may not work without these cookies")
        else:
            log.success("All required bot protection cookies captured!")

        # Check for auth token
        auth_token = extract_auth_token(cookies)
        if auth_token:
            log.success("Auth token captured successfully")
        else:
            log.warning("No auth token found - you may not be logged in")

        # Save with profile name
        path = COOKIES_DIR / f"cookies_{name}.json"
        save_cookies(cookies, path)

        # Also save as default
        if name != "default":
            save_cookies(cookies, DEFAULT_COOKIES_PATH)

        await browser.close()
        log.success("Session captured successfully")
