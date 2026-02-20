"""Proxy pool with health tracking, groups, and sticky sessions."""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from . import logger

log = logger.get("PROXY")


class ProxyType(Enum):
    """Types of proxies with different use cases."""

    RESIDENTIAL = "residential"  # Best for checkout
    DATACENTER = "datacenter"    # OK for monitoring
    ISP = "isp"                  # Good balance
    MOBILE = "mobile"            # Best anti-detection


@dataclass
class Proxy:
    """A single proxy with health tracking."""

    url: str
    proxy_type: ProxyType = ProxyType.DATACENTER
    failures: int = 0
    healthy: bool = True
    in_use: bool = False

    @property
    def masked_url(self) -> str:
        """URL with credentials masked."""
        if "@" in self.url:
            parts = self.url.split("@")
            return f"***@{parts[-1]}"
        return self.url[:30] + "..."


@dataclass
class ProxyGroup:
    """A group of proxies of the same type."""

    name: str
    proxy_type: ProxyType
    proxies: List[Proxy] = field(default_factory=list)

    def add(self, url: str) -> None:
        """Add a proxy to this group."""
        self.proxies.append(Proxy(url=url, proxy_type=self.proxy_type))

    def get_healthy(self) -> List[Proxy]:
        """Get all healthy, available proxies."""
        return [p for p in self.proxies if p.healthy and not p.in_use]

    def get_random(self) -> Optional[Proxy]:
        """Get a random healthy proxy."""
        healthy = self.get_healthy()
        return random.choice(healthy) if healthy else None


@dataclass
class ProxyPool:
    """Pool of proxies with groups and sticky session support."""

    groups: Dict[str, ProxyGroup] = field(default_factory=dict)
    default_group: str = "default"
    max_failures: int = 3
    _sticky: Dict[str, Proxy] = field(default_factory=dict)

    def create_group(
        self,
        name: str,
        proxy_type: ProxyType = ProxyType.DATACENTER,
    ) -> ProxyGroup:
        """Create a new proxy group."""
        group = ProxyGroup(name=name, proxy_type=proxy_type)
        self.groups[name] = group
        return group

    def load(self, path: Path, group_name: str = "default") -> int:
        """Load proxies from file into a group."""
        if not path.exists():
            return 0

        if group_name not in self.groups:
            self.create_group(group_name)

        group = self.groups[group_name]
        count = 0

        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                group.add(line)
                count += 1

        log.info(f"Loaded {count} proxies into group '{group_name}'")
        return count

    def get(self, group_name: Optional[str] = None) -> Optional[str]:
        """Get a random healthy proxy URL from a group."""
        name = group_name or self.default_group

        if name not in self.groups:
            return None

        proxy = self.groups[name].get_random()
        return proxy.url if proxy else None

    def get_sticky(self, task_id: str, group_name: Optional[str] = None) -> Optional[str]:
        """
        Get or create a sticky proxy for a task.

        Same task always gets same proxy (for checkout consistency).
        """
        # Return existing sticky proxy
        if task_id in self._sticky:
            proxy = self._sticky[task_id]
            if proxy.healthy:
                return proxy.url
            # Sticky proxy failed, release it
            del self._sticky[task_id]

        # Assign new sticky proxy
        name = group_name or self.default_group
        if name not in self.groups:
            return None

        proxy = self.groups[name].get_random()
        if proxy:
            proxy.in_use = True
            self._sticky[task_id] = proxy
            return proxy.url

        return None

    def release_sticky(self, task_id: str) -> None:
        """Release a sticky proxy when task completes."""
        if task_id in self._sticky:
            self._sticky[task_id].in_use = False
            del self._sticky[task_id]

    def mark_failed(self, url: str) -> None:
        """Mark a proxy as failed across all groups."""
        for group in self.groups.values():
            for proxy in group.proxies:
                if proxy.url == url:
                    proxy.failures += 1
                    if proxy.failures >= self.max_failures:
                        proxy.healthy = False
                        log.warning(f"Disabled proxy: {proxy.masked_url}")
                    return

    def mark_success(self, url: str) -> None:
        """Reset failure count for a proxy."""
        for group in self.groups.values():
            for proxy in group.proxies:
                if proxy.url == url:
                    proxy.failures = 0
                    return

    def reset_all(self) -> None:
        """Re-enable all proxies."""
        for group in self.groups.values():
            for proxy in group.proxies:
                proxy.failures = 0
                proxy.healthy = True
                proxy.in_use = False
        self._sticky.clear()
        log.info("All proxies reset")

    def stats(self) -> Dict[str, Dict[str, int]]:
        """Get proxy statistics by group."""
        stats = {}
        for name, group in self.groups.items():
            total = len(group.proxies)
            healthy = len([p for p in group.proxies if p.healthy])
            in_use = len([p for p in group.proxies if p.in_use])
            stats[name] = {
                "total": total,
                "healthy": healthy,
                "in_use": in_use,
                "available": healthy - in_use,
            }
        return stats


async def test_proxy(url: str, timeout: float = 10.0) -> bool:
    """Test if a proxy is working."""
    try:
        async with httpx.AsyncClient(proxy=url, timeout=timeout) as client:
            r = await client.get("https://httpbin.org/ip")
            return r.status_code == 200
    except Exception:
        return False


async def warmup_proxies(pool: ProxyPool, group_name: Optional[str] = None) -> int:
    """Test all proxies in a group and mark unhealthy ones."""
    groups_to_test = (
        [pool.groups[group_name]]
        if group_name and group_name in pool.groups
        else list(pool.groups.values())
    )

    tested = 0
    failed = 0

    for group in groups_to_test:
        log.info(f"Testing proxies in group '{group.name}'...")

        for proxy in group.proxies:
            if await test_proxy(proxy.url):
                proxy.healthy = True
                proxy.failures = 0
            else:
                proxy.healthy = False
                failed += 1
            tested += 1

    log.info(f"Tested {tested} proxies, {failed} failed")
    return tested - failed
