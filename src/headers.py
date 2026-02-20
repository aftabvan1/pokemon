"""Browser-accurate HTTP headers for anti-detection (Mac/Chrome 144)."""
from __future__ import annotations

from typing import Optional

# Chrome 144 on macOS - matches Pokemon Center research
CHROME_VERSION = "144.0.0.0"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_VERSION} Safari/537.36"
)

# Client hints (Sec-Ch-* headers) - macOS/ARM
CLIENT_HINTS = {
    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Ch-Device-Memory": "8",
    "Sec-Ch-Ua-Arch": '"arm"',
    "Sec-Ch-Ua-Model": '""',
}


def get_headers(
    cookies: str = "",
    csrf_token: Optional[str] = None,
    auth_token: Optional[str] = None,
    request_type: str = "api",
    referer: str = "https://www.pokemoncenter.com/en-ca",
) -> dict:
    """
    Get browser-accurate headers for requests.

    Args:
        cookies: Cookie header string
        csrf_token: CSRF token if required
        auth_token: JWT Bearer token for Authorization header
        request_type: 'api' for JSON, 'page' for HTML, 'checkout' for critical
        referer: Referer URL
    """
    # Base headers present in all requests
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Origin": "https://www.pokemoncenter.com",
        "Referer": referer,
    }

    # Add client hints
    headers.update(CLIENT_HINTS)

    # Pokemon Center specific headers (discovered via DevTools)
    headers.update({
        "x-store-locale": "en-ca",
        "x-store-scope": "pokemon-ca",
        "accept-version": "1",
    })

    # Request-type specific headers
    if request_type == "api":
        headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
    elif request_type == "page":
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })
    elif request_type == "checkout":
        # Checkout requests need extra care
        headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })

    # Add cookies
    if cookies:
        headers["Cookie"] = cookies

    # Add Authorization header (JWT Bearer token)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # Add CSRF token
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
        headers["X-XSRF-TOKEN"] = csrf_token

    return headers


def get_monitor_headers(cookies: str = "", auth_token: Optional[str] = None) -> dict:
    """Lightweight headers for high-frequency monitoring."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        **CLIENT_HINTS,
        # Pokemon Center specific
        "x-store-locale": "en-ca",
        "x-store-scope": "pokemon-ca",
        "accept-version": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    if cookies:
        headers["Cookie"] = cookies

    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    return headers
