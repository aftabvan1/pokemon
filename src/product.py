"""Product page parsing to extract encoded variant IDs."""
from __future__ import annotations

import re
import json
from typing import Optional

from . import logger
from . import endpoints
from .http_client import HTTPClient

log = logger.get("PRODUCT")


async def fetch_product_page(client: HTTPClient, product_id: str) -> str:
    """
    Fetch product page HTML.

    Args:
        client: HTTP client with session
        product_id: Human-readable product ID (e.g., '70-11179-101')

    Returns:
        Page HTML content
    """
    url = endpoints.url(endpoints.PRODUCT_PAGE, product_id=product_id)
    log.debug(f"Fetching product page: {url}")

    response = await client.get(url, request_type="page")

    if not response.is_success:
        raise ValueError(f"Failed to fetch product page: {response.status_code}")

    return response.text


def extract_encoded_id(html: str) -> Optional[str]:
    """
    Extract the encoded product ID from page HTML.

    The encoded ID (e.g., 'qgqvhkjxgazs2ojwgm4dc=') is used for cart operations.
    It's likely embedded in:
    - A <script> tag with JSON data
    - A data attribute on the Add to Cart button
    - A JavaScript variable

    Returns:
        Encoded product ID or None if not found
    """
    # Pattern 1: Look for base64-like ID in script tags
    # These often end with = and contain lowercase letters/numbers
    patterns = [
        # Look for "productId" or "variantId" or "sku" followed by encoded value
        r'"(?:productId|variantId|skuId|sku|id)":\s*"([a-z0-9]{20,}=?)"',
        # Look for add-product URL pattern
        r'/cart/add-product/([a-z0-9]{15,}=?)',
        # Look for data attributes
        r'data-(?:product|variant|sku)-id="([a-z0-9]{15,}=?)"',
        # Generic base64-ish pattern that might be an ID
        r'"([a-z0-9]{20,30}=)"',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            # Return first match that looks like an encoded ID
            for match in matches:
                if len(match) >= 15 and match.endswith('='):
                    log.debug(f"Found encoded ID: {match[:20]}...")
                    return match

    log.warning("Could not find encoded product ID in page")
    return None


def extract_product_json(html: str) -> Optional[dict]:
    """
    Extract product JSON data from page HTML.

    Many sites embed product data as JSON in a <script> tag.
    """
    # Look for __NEXT_DATA__ (Next.js)
    next_data = re.search(
        r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL
    )
    if next_data:
        try:
            data = json.loads(next_data.group(1))
            log.debug("Found __NEXT_DATA__ JSON")
            return data
        except json.JSONDecodeError:
            pass

    # Look for any JSON with product data
    json_patterns = [
        r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
        r'window\.productData\s*=\s*({.*?});',
        r'"product"\s*:\s*({[^}]+})',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                log.debug(f"Found product JSON via pattern")
                return data
            except json.JSONDecodeError:
                continue

    return None


def find_encoded_ids_in_json(data, found: list, depth: int = 0) -> None:
    """Recursively search JSON data for encoded IDs."""
    if depth > 10:  # Prevent infinite recursion
        return

    if isinstance(data, dict):
        for key, value in data.items():
            # Check if this key-value looks like an encoded ID
            if isinstance(value, str) and len(value) >= 15 and len(value) <= 40:
                # Looks like a base64-ish ID
                if value.endswith('=') or (value.isalnum() and value.islower()):
                    found.append((key, value))
            # Recurse into nested structures
            find_encoded_ids_in_json(value, found, depth + 1)
    elif isinstance(data, list):
        for item in data:
            find_encoded_ids_in_json(item, found, depth + 1)


async def get_encoded_product_id(
    client: HTTPClient,
    product_id: str,
) -> Optional[str]:
    """
    Get the encoded product ID needed for cart operations.

    Args:
        client: HTTP client with session
        product_id: Human-readable product ID from URL

    Returns:
        Encoded product ID or None if not found
    """
    try:
        html = await fetch_product_page(client, product_id)

        # Method 1: Look for encoded ID patterns in raw HTML
        encoded_id = extract_encoded_id(html)
        if encoded_id:
            log.info(f"Resolved {product_id} → {encoded_id[:20]}...")
            return encoded_id

        # Method 2: Parse __NEXT_DATA__ and search recursively
        product_data = extract_product_json(html)
        if product_data:
            found_ids: list = []
            find_encoded_ids_in_json(product_data, found_ids)

            # Prefer IDs from certain key names
            priority_keys = ['variantId', 'productId', 'encodedId', 'id', 'sku']
            for priority_key in priority_keys:
                for key, value in found_ids:
                    if key.lower() == priority_key.lower():
                        log.info(f"Resolved {product_id} → {value[:20]}... (via {key})")
                        return value

            # Fall back to any ID that looks right
            for key, value in found_ids:
                if value.endswith('=') and len(value) >= 20:
                    log.info(f"Resolved {product_id} → {value[:20]}... (via {key})")
                    return value

        log.warning(f"Could not resolve encoded ID for {product_id}")
        return None

    except Exception as e:
        log.error(f"Error fetching product data: {e}")
        return None
