"""Centralized logging configuration."""

import sys
from pathlib import Path
from loguru import logger


def setup(debug: bool = False) -> None:
    """Configure loguru for the bot."""
    logger.remove()

    level = "DEBUG" if debug else "INFO"
    fmt = (
        "<dim>{time:HH:mm:ss.SSS}</dim> "
        "<level>{level: <8}</level> "
        "<cyan>{extra[component]: <12}</cyan> "
        "{message}"
    )

    # Console output
    logger.add(sys.stdout, format=fmt, level=level, colorize=True)

    # File output
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "bot_{time:YYYY-MM-DD}.log",
        format=fmt,
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
    )


def get(component: str):
    """Get a logger bound to a component name."""
    return logger.bind(component=component)
