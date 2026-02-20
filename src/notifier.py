"""Discord webhook notifications."""

import httpx

from . import logger
from .config import Config

log = logger.get("NOTIFY")

COLORS = {
    "success": 0x00FF00,
    "warning": 0xFFAA00,
    "error": 0xFF0000,
    "info": 0x0099FF,
}


async def send(
    message: str,
    level: str = "info",
    title: str = "Porter",
) -> bool:
    """Send Discord webhook notification."""
    config = Config.load()

    if not config.discord_webhook:
        log.warning("No webhook configured")
        return False

    payload = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": COLORS.get(level, COLORS["info"]),
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(config.discord_webhook, json=payload)
            return r.is_success
    except httpx.RequestError as e:
        log.error(f"Webhook failed: {e}")
        return False


async def stock_found(product_id: str) -> bool:
    """Notify stock detected."""
    return await send(f"**STOCK**\n`{product_id}`", level="success")


async def order_placed(order_id: str) -> bool:
    """Notify order success."""
    return await send(f"**ORDER**\nConfirmation: `{order_id}`", level="success")


async def captcha_needed() -> bool:
    """Notify CAPTCHA required."""
    return await send("**CAPTCHA** — Check browser", level="warning")


async def error(msg: str) -> bool:
    """Notify error."""
    return await send(f"**ERROR**\n{msg}", level="error")
