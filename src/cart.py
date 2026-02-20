"""Cart operations with verification."""
from __future__ import annotations

from typing import Optional

from . import logger
from . import endpoints
from .http_client import HTTPClient
from .captcha import detect as detect_captcha

log = logger.get("CART")


class CartError(Exception):
    """Cart operation failed."""
    pass


async def add_to_cart(
    client: HTTPClient,
    product_id: str,
    size: str,
    quantity: int = 1,
) -> dict:
    """
    Add product to cart.

    Returns:
        Cart data from response

    Raises:
        CartError: If add fails
    """
    url = endpoints.url(endpoints.CART_ADD)
    payload = endpoints.cart_add_payload(product_id, size, quantity)

    log.info(f"Adding {product_id} ({size}) x{quantity}")

    response = await client.post(url, json=payload)

    # Check for CAPTCHA
    if detect_captcha(response):
        raise CartError("CAPTCHA required")

    if not response.is_success:
        raise CartError(f"Add failed: {response.status_code}")

    data = response.json()

    # Verify no error in response
    if data.get("error"):
        raise CartError(data.get("message", "Unknown error"))

    log.success(f"Added {product_id} to cart")
    return data


async def view_cart(client: HTTPClient) -> dict:
    """Get current cart contents."""
    url = endpoints.url(endpoints.CART_VIEW)
    response = await client.get(url)

    if not response.is_success:
        raise CartError(f"View cart failed: {response.status_code}")

    return response.json()


async def verify_item_in_cart(
    client: HTTPClient,
    product_id: str,
) -> bool:
    """Check if a specific item is in the cart."""
    try:
        cart = await view_cart(client)

        # NOTE: Adjust based on actual cart structure
        items = cart.get("items", [])
        for item in items:
            if item.get("productId") == product_id:
                return True

        return False

    except Exception as e:
        log.warning(f"Cart verification failed: {e}")
        return False


async def clear_cart(client: HTTPClient) -> bool:
    """Clear all items from cart."""
    url = endpoints.url(endpoints.CART_CLEAR)

    try:
        response = await client.post(url)
        if response.is_success:
            log.info("Cart cleared")
            return True
    except Exception as e:
        log.warning(f"Clear cart failed: {e}")

    return False


async def add_with_verification(
    client: HTTPClient,
    product_id: str,
    size: str,
    quantity: int = 1,
    max_retries: int = 2,
) -> bool:
    """
    Add to cart and verify it's actually there.

    Returns:
        True if item is confirmed in cart
    """
    for attempt in range(max_retries):
        try:
            await add_to_cart(client, product_id, size, quantity)

            # Verify
            if await verify_item_in_cart(client, product_id):
                return True

            log.warning(f"Item not in cart after add (attempt {attempt + 1})")

        except CartError as e:
            log.error(f"Add failed: {e}")
            if "CAPTCHA" in str(e):
                raise

        except Exception as e:
            log.error(f"Unexpected error: {e}")

    return False
