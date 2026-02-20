"""CAPTCHA detection and manual solving."""
from __future__ import annotations

from typing import Optional
import httpx

from . import logger
from . import notifier

log = logger.get("CAPTCHA")


def detect(response: httpx.Response) -> bool:
    """Check if response contains a CAPTCHA challenge."""
    if response.status_code == 429:
        return True

    try:
        data = response.json()
        if data.get("captcha") or data.get("challenge"):
            return True
    except Exception:
        pass

    # Cloudflare check
    if "cf-ray" in response.headers:
        if "challenge" in response.text.lower():
            return True

    return False


async def solve_manually(url: str) -> str | None:
    """Open browser for manual solve. Returns token or None."""
    from playwright.async_api import async_playwright

    log.warning("CAPTCHA detected, opening browser...")
    await notifier.captcha_needed()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url)
        log.info("Solve CAPTCHA, waiting for redirect...")

        try:
            await page.wait_for_url(
                lambda u: "challenge" not in u and "captcha" not in u.lower(),
                timeout=120_000,
            )
        except Exception:
            log.error("CAPTCHA timeout")
            await browser.close()
            return None

        cookies = await context.cookies()
        token = next(
            (c["value"] for c in cookies if "cf_clearance" in c["name"]),
            None,
        )

        log.success("CAPTCHA solved")
        await browser.close()
        return token
