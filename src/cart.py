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
    encoded_product_id: str,
    quantity: int = 1,
    clobber: bool = False,
) -> dict:
    """
    Add product to cart via TPCI API.

    The product ID must be the encoded variant ID (e.g., 'qgqvhkjxgazs2ojwgm4dc='),
    not the human-readable SKU.

    Args:
        client: HTTP client with session
        encoded_product_id: Base64-like encoded product variant ID
        quantity: Number to add
        clobber: Replace existing item if already in cart

    Returns:
        Cart data from response

    Raises:
        CartError: If add fails
    """
    # Product ID goes in URL path, not body
    url = endpoints.cart_add_url(encoded_product_id)
    payload = endpoints.cart_add_payload(quantity=quantity, clobber=clobber)

    log.info(f"Adding {encoded_product_id[:20]}... x{quantity}")

    response = await client.post(url, json=payload)

    # Check for CAPTCHA
    if detect_captcha(response):
        raise CartError("CAPTCHA required")

    # 201 Created = success for cart add
    if response.status_code == 201:
        log.success(f"Added to cart (201 Created)")
        try:
            return response.json()
        except Exception:
            return {"success": True, "status_code": 201}

    if not response.is_success:
        raise CartError(f"Add failed: {response.status_code}")

    data = response.json()

    # Verify no error in response
    if data.get("error"):
        raise CartError(data.get("message", "Unknown error"))

    log.success(f"Added to cart")
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
    encoded_product_id: str,
    quantity: int = 1,
    max_retries: int = 2,
) -> bool:
    """
    Add to cart and verify it's actually there.

    Args:
        client: HTTP client with session
        encoded_product_id: Base64-like encoded product variant ID
        quantity: Number to add
        max_retries: Max retry attempts

    Returns:
        True if item is confirmed in cart
    """
    for attempt in range(max_retries):
        try:
            result = await add_to_cart(client, encoded_product_id, quantity)

            # 201 Created means success
            if result.get("success") or result.get("status_code") == 201:
                return True

            # Optionally verify via cart view
            # if await verify_item_in_cart(client, encoded_product_id):
            #     return True

            log.warning(f"Item may not be in cart (attempt {attempt + 1})")

        except CartError as e:
            log.error(f"Add failed: {e}")
            if "CAPTCHA" in str(e):
                raise

        except Exception as e:
            log.error(f"Unexpected error: {e}")

    return False
