"""Session and cookie management with auto-refresh."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from . import logger
from .endpoints import BASE_URL

log = logger.get("SESSION")

COOKIES_DIR = Path("data")
DEFAULT_COOKIES_PATH = COOKIES_DIR / "cookies.json"
SESSION_EXPIRY = 3600  # 1 hour


@dataclass
class Session:
    """A single session with cookies and metadata."""

    name: str
    cookies: str
    csrf_token: Optional[str] = None
    last_validated: float = 0
    is_valid: bool = True

    @classmethod
    def from_file(cls, path: Path, name: str = "default") -> "Session":
        """Load session from cookies file."""
        if not path.exists():
            raise FileNotFoundError(f"No cookies at {path}")

        raw_cookies = json.loads(path.read_text())
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in raw_cookies)

        return cls(name=name, cookies=cookie_str, last_validated=time.time())

    def needs_refresh(self) -> bool:
        """Check if session needs refresh."""
        return time.time() - self.last_validated > SESSION_EXPIRY


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
        log.success(f"Loaded session '{name}'")
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
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        BASE_URL,
                        headers={"Cookie": session.cookies},
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
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    BASE_URL,
                    headers={"Cookie": session.cookies},
                    follow_redirects=True,
                )

                # Try to extract CSRF token from response
                # Common patterns: meta tag, cookie, header
                text = r.text
                if 'csrf' in text.lower():
                    # Look for meta tag pattern
                    import re
                    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', text)
                    if match:
                        session.csrf_token = match.group(1)
                        log.info(f"Extracted CSRF token for '{name}'")

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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE_URL)
        log.info("Log in manually, then press Enter in terminal...")

        # Wait for user input (blocking)
        await asyncio.get_event_loop().run_in_executor(None, input)

        cookies = await context.cookies()

        # Save with profile name
        path = COOKIES_DIR / f"cookies_{name}.json"
        save_cookies(cookies, path)

        # Also save as default
        if name != "default":
            save_cookies(cookies, DEFAULT_COOKIES_PATH)

        await browser.close()
        log.success("Session captured successfully")
