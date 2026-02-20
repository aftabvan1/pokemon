"""Product stock monitoring with jitter and rate limiting."""
from __future__ import annotations

from typing import Callable, Optional, Awaitable

from . import logger
from . import endpoints
from .http_client import HTTPClient
from .timing import monitor_interval

log = logger.get("MONITOR")


async def check_stock(client: HTTPClient, product_id: str) -> dict:
    """
    Check product availability.

    Returns:
        dict with at least {"in_stock": bool, "raw": <original response>}
    """
    url = endpoints.url(endpoints.STOCK_CHECK, product_id=product_id)

    response = await client.get(url)
    data = response.json()

    # Parse stock status based on configured keys
    status = data.get(endpoints.STOCK_STATUS_KEY, "")
    in_stock = status == endpoints.STOCK_IN_STOCK_VALUE

    return {
        "in_stock": in_stock,
        "status": status,
        "raw": data,
    }


async def monitor_product(
    client: HTTPClient,
    product_id: str,
    interval_ms: float = 300,
    on_stock: Optional[Callable[[str], Awaitable[None]]] = None,
    max_polls: int = 0,  # 0 = unlimited
) -> int:
    """
    Monitor a product until in stock.

    Args:
        client: HTTP client to use
        product_id: Product to monitor
        interval_ms: Base interval between polls (ms)
        on_stock: Callback when stock is found
        max_polls: Maximum number of polls (0 = unlimited)

    Returns:
        Number of polls made before finding stock (or max_polls)
    """
    polls = 0

    while max_polls == 0 or polls < max_polls:
        polls += 1

        try:
            result = await check_stock(client, product_id)

            if result["in_stock"]:
                log.success(f"{product_id} IN STOCK after {polls} polls")

                if on_stock:
                    await on_stock(product_id)

                return polls

            # Log every 100 polls
            if polls % 100 == 0:
                log.debug(f"{product_id} poll #{polls} - {result['status']}")

        except Exception as e:
            log.warning(f"{product_id} poll error: {e}")

        # Wait with jitter
        await monitor_interval(interval_ms)

    log.warning(f"{product_id} reached max polls ({max_polls})")
    return polls


async def monitor_multiple(
    client: HTTPClient,
    product_ids: list[str],
    interval_ms: float = 300,
) -> dict[str, bool]:
    """
    Check stock for multiple products in one pass.

    Returns:
        dict mapping product_id to in_stock status
    """
    import asyncio

    async def check_one(pid: str) -> tuple[str, bool]:
        try:
            result = await check_stock(client, pid)
            return (pid, result["in_stock"])
        except Exception:
            return (pid, False)

    results = await asyncio.gather(*[check_one(pid) for pid in product_ids])
    return dict(results)
