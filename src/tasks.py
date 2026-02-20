"""Task and profile management with CSV loading."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from . import logger

log = logger.get("TASKS")


class State(Enum):
    """Task execution states."""

    IDLE = "idle"
    MONITORING = "monitoring"
    CARTED = "carted"
    CHECKOUT = "checkout"
    CAPTCHA = "captcha"
    SUCCESS = "success"
    FAILED = "failed"


class Priority(Enum):
    """Task priority levels."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class Profile:
    """Billing/shipping profile."""

    name: str
    email: str
    first_name: str
    last_name: str
    address1: str
    address2: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: str
    card_number: str
    card_exp: str
    card_cvv: str


@dataclass
class Task:
    """A single purchase task."""

    id: str
    product_id: str
    size: str
    profile: Profile
    proxy_group: str = "default"
    priority: Priority = Priority.NORMAL
    state: State = State.IDLE
    polls: int = 0
    error: Optional[str] = None
    order_id: Optional[str] = None


@dataclass
class TaskManager:
    """Manages tasks and profiles loaded from CSV."""

    profiles: dict[str, Profile] = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)

    def load_profiles(self, path: Path) -> int:
        """Load profiles from CSV. Returns count loaded."""
        if not path.exists():
            log.warning(f"Profiles file not found: {path}")
            return 0

        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                profile = Profile(
                    name=row["profile_name"],
                    email=row["email"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    address1=row["address1"],
                    address2=row.get("address2", ""),
                    city=row["city"],
                    state=row["state"],
                    zip_code=row["zip"],
                    country=row["country"],
                    phone=row["phone"],
                    card_number=row["card_number"],
                    card_exp=row["card_exp"],
                    card_cvv=row["card_cvv"],
                )
                self.profiles[profile.name] = profile

        log.success(f"Loaded {len(self.profiles)} profiles")
        return len(self.profiles)

    def load_tasks(self, path: Path) -> int:
        """Load tasks from CSV. Returns count loaded."""
        if not path.exists():
            log.warning(f"Tasks file not found: {path}")
            return 0

        with open(path, newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                profile_name = row["profile"]
                if profile_name not in self.profiles:
                    log.error(f"Profile '{profile_name}' not found, skipping")
                    continue

                task = Task(
                    id=f"T{i:03d}",
                    product_id=row["product_id"],
                    size=row["size"],
                    profile=self.profiles[profile_name],
                    proxy_group=row.get("proxy_group", "default"),
                    priority=Priority(row.get("priority", "normal")),
                )
                self.tasks.append(task)

        log.success(f"Loaded {len(self.tasks)} tasks")
        return len(self.tasks)

    def by_state(self, state: State) -> list[Task]:
        """Get tasks filtered by state."""
        return [t for t in self.tasks if t.state == state]

    def summary(self) -> dict[str, int]:
        """Get task counts by state."""
        return {s.value: len(self.by_state(s)) for s in State}

    def sorted_by_priority(self) -> list[Task]:
        """Get tasks sorted by priority (high first)."""
        order = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}
        return sorted(self.tasks, key=lambda t: order[t.priority])
