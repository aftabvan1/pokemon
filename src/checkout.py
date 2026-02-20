"""Checkout flow with full error handling and CSRF support."""
from __future__ import annotations

from typing import Optional

from . import logger
from . import endpoints
from .http_client import HTTPClient
from .tasks import Profile
from .captcha import detect as detect_captcha
from .timing import human_delay

log = logger.get("CHECKOUT")


class CheckoutError(Exception):
    """Checkout step failed."""

    def __init__(self, step: str, message: str):
        self.step = step
        self.message = message
        super().__init__(f"{step}: {message}")


async def init_checkout(client: HTTPClient) -> dict:
    """
    Initialize checkout session.

    Some sites require this before shipping/payment steps.
    """
    url = endpoints.url(endpoints.CHECKOUT_INIT)

    try:
        response = await client.post(url)

        if detect_captcha(response):
            raise CheckoutError("init", "CAPTCHA required")

        if not response.is_success:
            raise CheckoutError("init", f"Status {response.status_code}")

        return response.json()

    except CheckoutError:
        raise
    except Exception as e:
        raise CheckoutError("init", str(e))


async def set_shipping(client: HTTPClient, profile: Profile) -> dict:
    """Set shipping address."""
    url = endpoints.url(endpoints.CHECKOUT_SHIPPING)
    payload = endpoints.shipping_payload(profile)

    log.info("Setting shipping address...")

    try:
        response = await client.post(url, json=payload)

        if detect_captcha(response):
            raise CheckoutError("shipping", "CAPTCHA required")

        if not response.is_success:
            raise CheckoutError("shipping", f"Status {response.status_code}")

        data = response.json()

        # Check for validation errors
        if data.get("error") or data.get("errors"):
            errors = data.get("errors", [data.get("error")])
            raise CheckoutError("shipping", str(errors))

        log.success("Shipping address set")
        return data

    except CheckoutError:
        raise
    except Exception as e:
        raise CheckoutError("shipping", str(e))


async def set_payment(client: HTTPClient, profile: Profile) -> dict:
    """Set payment method."""
    url = endpoints.url(endpoints.CHECKOUT_PAYMENT)
    payload = endpoints.payment_payload(profile)

    log.info("Setting payment method...")

    try:
        response = await client.post(url, json=payload)

        if detect_captcha(response):
            raise CheckoutError("payment", "CAPTCHA required")

        if not response.is_success:
            raise CheckoutError("payment", f"Status {response.status_code}")

        data = response.json()

        # Check for validation errors
        if data.get("error") or data.get("errors"):
            errors = data.get("errors", [data.get("error")])
            raise CheckoutError("payment", str(errors))

        log.success("Payment method set")
        return data

    except CheckoutError:
        raise
    except Exception as e:
        raise CheckoutError("payment", str(e))


async def submit_order(client: HTTPClient) -> str:
    """
    Submit the order.

    Returns:
        Order ID / confirmation number
    """
    url = endpoints.url(endpoints.CHECKOUT_SUBMIT)

    log.info("Submitting order...")

    try:
        response = await client.post(url)

        if detect_captcha(response):
            raise CheckoutError("submit", "CAPTCHA required")

        if not response.is_success:
            raise CheckoutError("submit", f"Status {response.status_code}")

        data = response.json()

        # Check for errors
        if data.get("error"):
            raise CheckoutError("submit", data.get("message", "Order failed"))

        # Extract order ID - adjust based on actual response
        order_id = (
            data.get("orderId")
            or data.get("orderNumber")
            or data.get("confirmationNumber")
        )

        if not order_id:
            raise CheckoutError("submit", "No order ID in response")

        log.success(f"Order submitted: {order_id}")
        return order_id

    except CheckoutError:
        raise
    except Exception as e:
        raise CheckoutError("submit", str(e))


async def run_checkout(
    client: HTTPClient,
    profile: Profile,
    skip_init: bool = False,
) -> str:
    """
    Run full checkout flow.

    Args:
        client: HTTP client with session
        profile: Billing/shipping profile
        skip_init: Skip checkout initialization

    Returns:
        Order ID on success

    Raises:
        CheckoutError: On any failure
    """
    log.info("Starting checkout flow...")

    try:
        # Step 0: Initialize (optional)
        if not skip_init:
            await init_checkout(client)
            await human_delay("checkout")

        # Step 1: Shipping
        await set_shipping(client, profile)
        await human_delay("checkout")

        # Step 2: Payment
        await set_payment(client, profile)
        await human_delay("checkout")

        # Step 3: Submit
        order_id = await submit_order(client)

        log.success(f"Checkout complete! Order: {order_id}")
        return order_id

    except CheckoutError as e:
        log.error(f"Checkout failed at {e.step}: {e.message}")
        raise


async def checkout_with_retry(
    client: HTTPClient,
    profile: Profile,
    max_retries: int = 2,
) -> Optional[str]:
    """
    Run checkout with retry on transient failures.

    Returns:
        Order ID or None if all retries failed
    """
    last_error: Optional[CheckoutError] = None

    for attempt in range(max_retries):
        try:
            return await run_checkout(client, profile, skip_init=(attempt > 0))

        except CheckoutError as e:
            last_error = e

            # Don't retry on CAPTCHA - needs manual intervention
            if "CAPTCHA" in e.message:
                raise

            # Don't retry on validation errors
            if e.step in ["shipping", "payment"] and "invalid" in e.message.lower():
                raise

            log.warning(f"Checkout attempt {attempt + 1} failed, retrying...")
            await human_delay("navigate")

    if last_error:
        raise last_error

    return None
