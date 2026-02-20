#!/usr/bin/env python3
"""
Pokemon Center Stock Monitor

Monitors product pages for stock availability by parsing JSON-LD structured data.
Plays alert sound and logs when stock is detected.
"""

import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

# =============================================================================
# CONFIGURATION - Edit these values
# =============================================================================

# URLs to monitor (add/remove as needed)
URLS_TO_MONITOR = [
    "https://www.pokemoncenter.com/en-ca/product/70-11179-101/",
    # Add more URLs here:
    # "https://www.pokemoncenter.com/en-ca/product/ANOTHER-PRODUCT-ID/",
]

# Polling interval in seconds (will add ±5 second jitter)
POLL_INTERVAL = 30

# Log file path
LOG_FILE = Path("stock_log.txt")

# User agents to rotate through
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
]

# =============================================================================
# GLOBALS
# =============================================================================

ua_index = 0
stock_status: dict[str, bool] = {}  # Track previous status for change detection


def get_next_user_agent() -> str:
    """Rotate through user agents."""
    global ua_index
    ua = USER_AGENTS[ua_index % len(USER_AGENTS)]
    ua_index += 1
    return ua


def get_headers() -> dict:
    """Build request headers with rotated user agent."""
    return {
        "User-Agent": get_next_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_to_file(message: str) -> None:
    """Append message to log file."""
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp()}] {message}\n")


def print_status(url: str, status: str, in_stock: bool = False) -> None:
    """Print timestamped status update."""
    product_id = url.rstrip("/").split("/")[-1]

    if in_stock:
        # Loud alert for stock
        print(f"\n{'='*60}")
        print(f"[{timestamp()}] *** STOCK DETECTED ***")
        print(f"Product: {product_id}")
        print(f"URL: {url}")
        print(f"{'='*60}\n")
    else:
        print(f"[{timestamp()}] {product_id}: {status}")


def play_alert_sound() -> None:
    """Play system alert sound on Mac."""
    # Play multiple times for attention
    for _ in range(3):
        os.system("afplay /System/Library/Sounds/Ping.aiff &")
        os.system("sleep 0.3")


def extract_json_ld(html: str) -> list[dict]:
    """Extract all JSON-LD scripts from HTML."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    results = []
    for match in matches:
        try:
            data = json.loads(match.strip())
            # Handle both single objects and arrays
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except json.JSONDecodeError:
            continue

    return results


def check_availability(json_ld_items: list[dict]) -> tuple[bool, str]:
    """
    Check if product is in stock from JSON-LD data.

    Returns:
        (in_stock: bool, status_text: str)
    """
    for item in json_ld_items:
        # Check if it's a Product type
        item_type = item.get("@type", "")
        if item_type != "Product" and "Product" not in str(item_type):
            continue

        # Check offers
        offers = item.get("offers", {})

        # Handle single offer or array of offers
        if isinstance(offers, list):
            offer_list = offers
        else:
            offer_list = [offers]

        for offer in offer_list:
            availability = offer.get("availability", "")

            # Normalize the availability URL
            availability_lower = availability.lower()

            if "instock" in availability_lower:
                return True, "IN STOCK"
            elif "outofstock" in availability_lower:
                return False, "Out of Stock"
            elif "preorder" in availability_lower:
                return False, "Pre-order"
            elif "soldout" in availability_lower:
                return False, "Sold Out"
            elif "limitedavailability" in availability_lower:
                return True, "LIMITED AVAILABILITY"

    return False, "Unknown"


async def check_product(client: httpx.AsyncClient, url: str, retries: int = 3) -> None:
    """
    Check a single product URL for stock.

    Uses exponential backoff on errors.
    """
    global stock_status

    product_id = url.rstrip("/").split("/")[-1]

    for attempt in range(retries):
        try:
            response = await client.get(url, headers=get_headers(), follow_redirects=True)

            if response.status_code == 403:
                print_status(url, "BLOCKED (403) - may need fresh cookies")
                log_to_file(f"{product_id}: Blocked (403)")
                return

            if response.status_code == 429:
                wait_time = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                print_status(url, f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            if response.status_code != 200:
                print_status(url, f"HTTP {response.status_code}")
                return

            # Parse JSON-LD from response
            json_ld_items = extract_json_ld(response.text)

            if not json_ld_items:
                print_status(url, "No JSON-LD found")
                return

            # Check availability
            in_stock, status_text = check_availability(json_ld_items)

            # Check if status changed
            previous_status = stock_status.get(url)
            current_status = in_stock

            if in_stock:
                # STOCK DETECTED!
                print_status(url, status_text, in_stock=True)
                log_to_file(f"{product_id}: *** IN STOCK *** - {url}")
                play_alert_sound()

                # Only alert once per stock event
                if previous_status != current_status:
                    stock_status[url] = current_status
            else:
                print_status(url, status_text)

                # Log status changes
                if previous_status is None or previous_status != current_status:
                    log_to_file(f"{product_id}: {status_text}")
                    stock_status[url] = current_status

            return

        except httpx.TimeoutException:
            wait_time = 2 ** attempt
            print_status(url, f"Timeout (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                await asyncio.sleep(wait_time)

        except httpx.RequestError as e:
            wait_time = 2 ** attempt
            print_status(url, f"Error: {e} (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                await asyncio.sleep(wait_time)

    log_to_file(f"{product_id}: Failed after {retries} attempts")


async def monitor_loop(urls: list[str]) -> None:
    """Main monitoring loop."""
    print(f"\n{'='*60}")
    print(f"Pokemon Center Stock Monitor")
    print(f"{'='*60}")
    print(f"Monitoring {len(urls)} product(s)")
    print(f"Poll interval: {POLL_INTERVAL}s (±5s jitter)")
    print(f"Log file: {LOG_FILE.absolute()}")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*60}\n")

    log_to_file(f"Monitor started for {len(urls)} URLs")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        http2=True,
    ) as client:
        poll_count = 0

        while True:
            poll_count += 1
            print(f"\n--- Poll #{poll_count} at {timestamp()} ---")

            # Check all URLs concurrently
            tasks = [check_product(client, url) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate next interval with jitter
            jitter = random.uniform(-5, 5)
            wait_time = max(5, POLL_INTERVAL + jitter)  # Minimum 5 seconds

            print(f"\nNext check in {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)


def main():
    """Entry point."""
    if not URLS_TO_MONITOR:
        print("Error: No URLs configured. Edit URLS_TO_MONITOR at the top of the file.")
        sys.exit(1)

    try:
        asyncio.run(monitor_loop(URLS_TO_MONITOR))
    except KeyboardInterrupt:
        print(f"\n\n[{timestamp()}] Monitor stopped by user")
        log_to_file("Monitor stopped by user")


if __name__ == "__main__":
    main()
