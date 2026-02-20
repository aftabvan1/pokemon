"""Request timing utilities for anti-detection."""
from __future__ import annotations

import asyncio
import random


def jitter(base_ms: float, variance_ms: float = 50) -> float:
    """
    Add random jitter to a base delay.

    Args:
        base_ms: Base delay in milliseconds
        variance_ms: Maximum variance (+/-)

    Returns:
        Delay in seconds (for asyncio.sleep)
    """
    delay_ms = base_ms + random.uniform(-variance_ms, variance_ms)
    return max(0.01, delay_ms / 1000)  # Minimum 10ms


async def wait_with_jitter(base_ms: float, variance_ms: float = 50) -> None:
    """Sleep with jitter applied."""
    await asyncio.sleep(jitter(base_ms, variance_ms))


async def human_delay(action: str = "default") -> None:
    """
    Add human-like delay between actions.

    Different actions have different typical delays.
    """
    delays = {
        "click": (100, 300),      # Quick click
        "type": (50, 150),        # Between keystrokes
        "read": (500, 1500),      # Reading content
        "navigate": (300, 800),   # Page navigation
        "checkout": (200, 500),   # Checkout steps
        "default": (100, 400),
    }

    min_ms, max_ms = delays.get(action, delays["default"])
    delay_ms = random.uniform(min_ms, max_ms)
    await asyncio.sleep(delay_ms / 1000)


async def monitor_interval(base_ms: float = 300) -> None:
    """
    Wait between monitor polls with jitter.

    Prevents synchronized polling patterns that trigger detection.
    """
    # 10% variance
    variance = base_ms * 0.1
    await wait_with_jitter(base_ms, variance)


class RateLimiter:
    """Simple rate limiter for requests."""

    def __init__(self, requests_per_second: float = 3.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until we can make another request."""
        async with self._lock:
            import time
            now = time.monotonic()
            elapsed = now - self.last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_request = time.monotonic()
