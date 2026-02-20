"""Pre-flight health checks before running tasks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from . import logger
from .endpoints import BASE_URL
from .session import SessionManager, load_cookies
from .proxy import ProxyPool

log = logger.get("HEALTH")


@dataclass
class HealthResult:
    """Result of a health check."""

    name: str
    passed: bool
    message: str


async def check_session(cookies: Optional[str] = None) -> HealthResult:
    """Check if session cookies are valid."""
    try:
        if cookies is None:
            cookies = load_cookies()

        async with httpx.AsyncClient() as client:
            r = await client.get(
                BASE_URL,
                headers={"Cookie": cookies},
                timeout=10.0,
                follow_redirects=True,
            )

            if r.status_code == 200:
                return HealthResult("Session", True, "Valid")
            else:
                return HealthResult("Session", False, f"Status {r.status_code}")

    except FileNotFoundError:
        return HealthResult("Session", False, "No cookies file")
    except httpx.RequestError as e:
        return HealthResult("Session", False, str(e))


async def check_proxy(proxy_url: str) -> HealthResult:
    """Check if proxy is working."""
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
            r = await client.get("https://httpbin.org/ip")

            if r.status_code == 200:
                ip = r.json().get("origin", "unknown")
                return HealthResult("Proxy", True, f"IP: {ip}")
            else:
                return HealthResult("Proxy", False, f"Status {r.status_code}")

    except httpx.RequestError as e:
        return HealthResult("Proxy", False, str(e))


async def check_endpoint(url: str, cookies: str = "") -> HealthResult:
    """Check if an endpoint is reachable."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                headers={"Cookie": cookies} if cookies else {},
                follow_redirects=True,
            )

            if r.status_code < 400:
                return HealthResult("Endpoint", True, f"{url} OK")
            else:
                return HealthResult("Endpoint", False, f"{url} returned {r.status_code}")

    except httpx.RequestError as e:
        return HealthResult("Endpoint", False, str(e))


async def check_discord(webhook_url: str) -> HealthResult:
    """Check if Discord webhook is valid (without sending)."""
    if not webhook_url:
        return HealthResult("Discord", False, "No webhook URL")

    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return HealthResult("Discord", False, "Invalid webhook URL format")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # GET on webhook returns webhook info
            r = await client.get(webhook_url)

            if r.status_code == 200:
                data = r.json()
                name = data.get("name", "Unknown")
                return HealthResult("Discord", True, f"Webhook: {name}")
            else:
                return HealthResult("Discord", False, f"Status {r.status_code}")

    except httpx.RequestError as e:
        return HealthResult("Discord", False, str(e))


async def run_all_checks(
    proxy_pool: Optional[ProxyPool] = None,
    discord_webhook: str = "",
) -> List[HealthResult]:
    """Run all health checks."""
    results: List[HealthResult] = []

    # Session check
    log.info("Checking session...")
    results.append(await check_session())

    # Proxy check (first proxy in pool)
    if proxy_pool and proxy_pool.groups:
        log.info("Checking proxy...")
        proxy_url = proxy_pool.get()
        if proxy_url:
            results.append(await check_proxy(proxy_url))
        else:
            results.append(HealthResult("Proxy", True, "No healthy proxies"))
    else:
        results.append(HealthResult("Proxy", True, "No proxies configured"))

    # Endpoint check
    log.info("Checking endpoint...")
    results.append(await check_endpoint(BASE_URL))

    # Discord check
    if discord_webhook:
        log.info("Checking Discord...")
        results.append(await check_discord(discord_webhook))

    return results


def print_results(results: List[HealthResult]) -> bool:
    """Print health check results. Returns True if all passed."""
    from .display import console

    all_passed = True

    console.print("\n[bold]Health Check Results[/]\n")

    for r in results:
        status = "[green]PASS[/]" if r.passed else "[red]FAIL[/]"
        console.print(f"  {status}  {r.name}: {r.message}")
        if not r.passed:
            all_passed = False

    console.print()
    return all_passed
