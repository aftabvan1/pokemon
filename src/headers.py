"""Browser-accurate HTTP headers for anti-detection."""
from __future__ import annotations

from typing import Optional

# Chrome 122 on Windows 10 - keep this updated
CHROME_VERSION = "122.0.0.0"
USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_VERSION} Safari/537.36"
)

# Client hints (Sec-Ch-* headers)
CLIENT_HINTS = {
    "Sec-Ch-Ua": f'"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def get_headers(
    cookies: str = "",
    csrf_token: Optional[str] = None,
    request_type: str = "api",
    referer: str = "https://www.pokemoncenter.com/",
) -> dict:
    """
    Get browser-accurate headers for requests.

    Args:
        cookies: Cookie header string
        csrf_token: CSRF token if required
        request_type: 'api' for JSON, 'page' for HTML, 'checkout' for critical
        referer: Referer URL
    """
    # Base headers present in all requests
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Origin": "https://www.pokemoncenter.com",  # Update for target site
        "Referer": referer,
    }

    # Add client hints
    headers.update(CLIENT_HINTS)

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

    # Add CSRF token
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
        # Some sites use different header names
        headers["X-XSRF-TOKEN"] = csrf_token

    return headers


def get_monitor_headers(cookies: str = "") -> dict:
    """Lightweight headers for high-frequency monitoring."""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": cookies,
        **CLIENT_HINTS,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
