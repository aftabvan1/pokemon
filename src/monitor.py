"""Product stock monitoring with SFCC response parsing."""
from __future__ import annotations

from typing import Callable, Optional, Awaitable, List

from . import logger
from . import endpoints
from .http_client import HTTPClient
from .timing import monitor_interval

log = logger.get("MONITOR")


def parse_stock_status(data: dict) -> bool:
    """
    Parse SFCC stock response to determine availability.

    Tries multiple common SFCC response field patterns.
    UPDATE THIS after verifying actual response structure via DevTools.

    Common SFCC patterns:
    - data["availability"]["orderable"] == True
    - data["inventoryStatus"] == "IN_STOCK"
    - data["available"] == True
    - data["inStock"] == True
    - data["product"]["availability"]["orderable"] == True
    """
    # Pattern 1: availability.orderable (most common SFCC)
    if "availability" in data:
        avail = data["availability"]
        if isinstance(avail, dict):
            if avail.get("orderable") is True:
                return True
            if avail.get("available") is True:
                return True
            if avail.get("inStock") is True:
                return True
        elif avail is True:
            return True

    # Pattern 2: inventoryStatus string
    if data.get("inventoryStatus") == "IN_STOCK":
        return True

    # Pattern 3: Simple boolean fields
    if data.get("available") is True:
        return True
    if data.get("inStock") is True:
        return True
    if data.get("orderable") is True:
        return True

    # Pattern 4: Nested under product
    if "product" in data:
        product = data["product"]
        if isinstance(product, dict):
            return parse_stock_status(product)  # Recurse

    # Pattern 5: quantity > 0
    qty = data.get("quantity", data.get("inventoryQuantity", data.get("ats", 0)))
    if isinstance(qty, (int, float)) and qty > 0:
        return True

    return False


def get_stock_status_text(data: dict) -> str:
    """Get human-readable stock status from response."""
    # Try common status fields
    status = (
        data.get("inventoryStatus")
        or data.get("status")
        or data.get("availability", {}).get("status")
        or "UNKNOWN"
    )

    if isinstance(status, str):
        return status

    return "UNKNOWN"


async def check_stock(client: HTTPClient, product_id: str) -> dict:
    """
    Check product availability via SFCC API.

    Returns:
        dict with {"in_stock": bool, "status": str, "raw": dict}
    """
    url = endpoints.url(endpoints.STOCK_CHECK, product_id=product_id)

    response = await client.get(url)

    # Handle non-JSON responses
    try:
        data = response.json()
    except Exception as e:
        log.warning(f"Non-JSON response for {product_id}: {e}")
        return {
            "in_stock": False,
            "status": f"HTTP {response.status_code}",
            "raw": {"error": str(e), "status_code": response.status_code},
        }

    # Parse stock status using multiple patterns
    in_stock = parse_stock_status(data)
    status = get_stock_status_text(data)

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
    product_ids: List[str],
    interval_ms: float = 300,
) -> dict:
    """
    Check stock for multiple products in one pass.

    Returns:
        dict mapping product_id to in_stock status
    """
    import asyncio

    async def check_one(pid: str) -> tuple:
        try:
            result = await check_stock(client, pid)
            return (pid, result["in_stock"])
        except Exception:
            return (pid, False)

    results = await asyncio.gather(*[check_one(pid) for pid in product_ids])
    return dict(results)
