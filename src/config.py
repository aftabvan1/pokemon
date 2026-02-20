"""Configuration loader from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """Bot configuration from .env file."""

    email: str
    password: str
    discord_webhook: str
    proxy_list: List[str]
    monitor_interval: float
    checkout_timeout: int

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> Config:
        """Load config from .env file."""
        load_dotenv(env_path or ".env")

        proxy_str = os.getenv("PROXY_LIST", "")
        proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]

        return cls(
            email=os.getenv("PC_EMAIL", ""),
            password=os.getenv("PC_PASSWORD", ""),
            discord_webhook=os.getenv("DISCORD_WEBHOOK_URL", ""),
            proxy_list=proxies,
            monitor_interval=float(os.getenv("MONITOR_INTERVAL", "0.3")),
            checkout_timeout=int(os.getenv("CHECKOUT_TIMEOUT", "30")),
        )
