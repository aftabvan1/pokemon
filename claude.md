# Pokemon Center Bot

A Python-based auto-purchase bot for pokemoncenter.com. Monitors product pages for restocks, adds to cart instantly, and completes checkout automatically with manual CAPTCHA solving via browser popup when needed.

This is a learning project focused on web automation, HTTP interception, session management, and bot architecture.

---

## Tech Stack

| Category | Tool | Purpose |
|----------|------|---------|
| Language | Python 3.11+ | Async support, type hints |
| Automation | Playwright (async) | Session capture, CAPTCHA handling |
| HTTP | httpx (async) | Fast direct API calls |
| CLI | typer | Command-line interface |
| Terminal UI | rich | Colors, tables, progress bars, live display |
| Logging | loguru | Structured, colored logging |
| Notifications | Discord webhook | Alerts on key events |
| Config | python-dotenv | Environment variable management |
| Proxy | httpx + rotating pool | IP rotation, ban avoidance |
| Async | asyncio | Concurrent task execution |

---

## Project Structure

```
/pokemon
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point, CLI commands (typer)
│   ├── tasks.py          # Task & Profile dataclasses, CSV loading
│   ├── runner.py         # Multi-task concurrent runner with live display
│   ├── monitor.py        # Polls product endpoint for stock changes
│   ├── cart.py           # Handles add-to-cart API call
│   ├── checkout.py       # Checkout flow (shipping, payment, submit)
│   ├── captcha.py        # CAPTCHA detection, browser popup, manual solve
│   ├── session.py        # Cookie/token management, session state
│   ├── proxy.py          # Proxy pool with health tracking
│   ├── endpoints.py      # All mapped API endpoints as constants
│   ├── notifier.py       # Discord webhook notifications
│   ├── logger.py         # Centralized logging configuration
│   └── config.py         # Loads env vars and settings
├── data/
│   ├── tasks.csv         # Task definitions (product, size, profile)
│   ├── profiles.csv      # Billing/shipping profiles
│   ├── proxies.txt       # Proxy list (one per line)
│   └── cookies.json      # Saved session cookies
├── logs/                 # Auto-generated log files
├── .env                  # Credentials (never commit)
├── .env.example          # Template for .env
├── requirements.txt
└── README.md
```

---

## Installation

```bash
# Clone and enter directory
cd pokemon

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy env template and fill in your values
cp .env.example .env
```

### requirements.txt

```
httpx[http2]>=0.27.0
playwright>=1.40.0
python-dotenv>=1.0.0
typer>=0.9.0
rich>=13.7.0
loguru>=0.7.2
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
```

---

## Usage

```bash
# Run with default settings (uses TARGET_PRODUCTS from .env)
python -m src.main run

# Monitor specific products
python -m src.main run --products "product-123,product-456"

# Dry run (monitor only, no purchase)
python -m src.main run --dry-run

# Debug mode (verbose logging)
python -m src.main run --debug

# Capture session cookies via browser login
python -m src.main login

# Test Discord webhook
python -m src.main test-notify
```

---

## Terminal Experience

The terminal output should be scannable, informative, and visually distinct. Use `rich` and `loguru` for this.

### Log Format

```
TIMESTAMP    LEVEL    COMPONENT    MESSAGE
─────────────────────────────────────────────────────────
12:34:56.123 INFO     MONITOR      Watching product-123
12:34:56.456 INFO     MONITOR      Poll #1,247 — out of stock
12:34:57.001 SUCCESS  MONITOR      STOCK DETECTED!
12:34:57.012 INFO     CART         Adding to cart...
12:34:57.234 SUCCESS  CART         Added successfully
12:34:57.250 INFO     CHECKOUT     Starting checkout flow
12:34:58.100 WARNING  CAPTCHA      Challenge detected — check browser
12:35:15.000 SUCCESS  CHECKOUT     Order placed! Confirmation #12345
```

### Color Coding

| Level | Color | Use Case |
|-------|-------|----------|
| DEBUG | dim white | Verbose internals |
| INFO | white | Normal operations |
| SUCCESS | green | Stock found, cart added, order placed |
| WARNING | yellow | CAPTCHA needed, session expiring |
| ERROR | red | Request failed, checkout error |

### Logger Setup

```python
# src/logger.py
import sys
from loguru import logger

def setup_logger(debug: bool = False):
    logger.remove()  # Remove default handler

    level = "DEBUG" if debug else "INFO"

    logger.add(
        sys.stdout,
        format="<dim>{time:HH:mm:ss.SSS}</dim> <level>{level: <8}</level> <cyan>{extra[component]: <10}</cyan> {message}",
        level=level,
        colorize=True,
    )

    # Also log to file
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
    )

    return logger

# Usage in other modules
from loguru import logger

logger.bind(component="MONITOR").info("Watching product-123")
logger.bind(component="CART").success("Added to cart!")
logger.bind(component="CAPTCHA").warning("Challenge detected")
```

### Live Status Display

Use `rich.live` for real-time updates without flooding the terminal:

```python
from rich.live import Live
from rich.table import Table
from rich.console import Console

console = Console()

def create_status_table(tasks: list[dict]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Product", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Polls", justify="right")
    table.add_column("Last Check", style="dim")

    for task in tasks:
        status_style = "green" if task["status"] == "IN_STOCK" else "dim"
        table.add_row(
            task["product_id"],
            f"[{status_style}]{task['status']}[/]",
            str(task["poll_count"]),
            task["last_check"],
        )

    return table

async def monitor_with_display(tasks: list[dict]):
    with Live(create_status_table(tasks), refresh_per_second=4) as live:
        while True:
            # Update task statuses...
            live.update(create_status_table(tasks))
            await asyncio.sleep(0.25)
```

### Progress Indicators

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
) as progress:
    task = progress.add_task("Logging in...", total=None)
    await perform_login()
    progress.update(task, description="[green]Logged in!")
```

---

## CLI Interface

```python
# src/main.py
import typer
from typing import Optional

app = typer.Typer(
    name="pokemon-bot",
    help="Pokemon Center auto-purchase bot",
    add_completion=False,
)

@app.command()
def run(
    products: Optional[str] = typer.Option(
        None, "--products", "-p",
        help="Comma-separated product IDs to monitor"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Monitor only, don't purchase"
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d",
        help="Enable debug logging"
    ),
):
    """Start monitoring and auto-purchase."""
    from .logger import setup_logger
    from .config import Config

    setup_logger(debug=debug)
    config = Config()

    product_list = products.split(",") if products else config.target_products

    # Start the bot...

@app.command()
def login():
    """Open browser to capture session cookies."""
    pass

@app.command()
def test_notify():
    """Send a test Discord notification."""
    pass

if __name__ == "__main__":
    app()
```

---

## Graceful Shutdown

Handle Ctrl+C cleanly with status summary:

```python
import signal
import asyncio
from loguru import logger

class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        self.tasks_completed = 0
        self.tasks_failed = 0

    def register_handlers(self):
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        if self.shutdown_requested:
            logger.warning("Force quitting...")
            raise SystemExit(1)

        logger.info("Shutdown requested, finishing current operations...")
        self.shutdown_requested = True

    def print_summary(self):
        from rich.panel import Panel
        from rich.console import Console

        console = Console()
        summary = f"""
[green]Completed:[/] {self.tasks_completed}
[red]Failed:[/] {self.tasks_failed}
        """
        console.print(Panel(summary, title="Session Summary", border_style="blue"))

# Usage
shutdown = GracefulShutdown()
shutdown.register_handlers()

async def main_loop():
    while not shutdown.shutdown_requested:
        await do_work()

    shutdown.print_summary()
```

---

## Architecture

### Core Flow

```
1. MONITOR     → Poll product API every 200-500ms
                 Watch for "IN_STOCK" status

2. ADD TO CART → POST add-to-cart immediately on detection
                 Use pre-loaded session cookies

3. CHECKOUT    → POST checkout endpoints sequentially:
                 • Set shipping address
                 • Set payment method
                 • Submit order

4. CAPTCHA     → On challenge detection:
                 • Pause task
                 • Open Playwright browser at CAPTCHA URL
                 • Discord notification
                 • Wait for manual solve
                 • Extract token, resume flow

5. NOTIFY      → Discord webhook on success/failure
```

### Two Modes

**Browser Mode (Playwright)**
- Used for: login, session capture, CAPTCHA solving
- Controls real Chromium browser
- Log in once, capture cookies, reuse them

**HTTP Mode (httpx)**
- Used for: monitoring, cart, checkout
- Direct API calls with saved cookies
- 10-100x faster than browser mode

Always prefer HTTP mode. Fall back to browser only when needed.

---

## Endpoint Mapping (Critical First Step)

Before writing bot code, intercept and document all API calls manually:

1. Open Chrome → F12 → Network tab
2. Filter by `Fetch/XHR`
3. Add item to cart manually → watch requests
4. Click through checkout → watch every request
5. For each request, note:
   - Method (GET/POST)
   - Full URL
   - Headers (`Cookie`, `X-CSRF-Token`, `Authorization`)
   - Request body (JSON payload)
   - Response structure

### endpoints.py

```python
# src/endpoints.py

BASE_URL = "https://www.pokemoncenter.com"

# Stock checking
AVAILABILITY = "/api/product/{product_id}/availability"

# Cart operations
CART_ADD = "/api/cart/add"
CART_VIEW = "/api/cart"

# Checkout flow
CHECKOUT_SHIPPING = "/api/checkout/shipping"
CHECKOUT_PAYMENT = "/api/checkout/payment"
CHECKOUT_SUBMIT = "/api/checkout/submit"

# Note: These are placeholder paths. You must intercept
# the real endpoints from the site using Chrome DevTools.
```

---

## Session Management

### Login Flow

```python
# src/session.py
import json
from pathlib import Path
from playwright.async_api import async_playwright
from loguru import logger

COOKIES_PATH = Path("profiles/cookies.json")

async def capture_session():
    """Open browser for manual login, save cookies."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.pokemoncenter.com/login")

        logger.bind(component="SESSION").info(
            "Please log in manually. Press Enter when done..."
        )
        input()

        cookies = await context.cookies()
        COOKIES_PATH.write_text(json.dumps(cookies, indent=2))

        logger.bind(component="SESSION").success(
            f"Saved {len(cookies)} cookies to {COOKIES_PATH}"
        )

        await browser.close()

def load_cookies() -> dict[str, str]:
    """Load cookies as header string."""
    if not COOKIES_PATH.exists():
        raise FileNotFoundError("No saved cookies. Run 'login' command first.")

    cookies = json.loads(COOKIES_PATH.read_text())
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)
```

### Headers

```python
# Keep User-Agent current — check https://www.whatismybrowser.com/guides/the-latest-user-agent/chrome
def get_headers(cookies: str, csrf_token: str = None) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.pokemoncenter.com/",
        "Origin": "https://www.pokemoncenter.com",
        "Cookie": cookies,
    }

    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    return headers
```

### Session Refresh

```python
import time

class SessionManager:
    def __init__(self):
        self.cookies = None
        self.last_refresh = 0
        self.refresh_interval = 3600  # 1 hour

    async def ensure_valid(self):
        if time.time() - self.last_refresh > self.refresh_interval:
            await self.refresh()

    async def refresh(self):
        # Re-login or refresh token
        self.last_refresh = time.time()

    async def handle_auth_error(self, response):
        if response.status_code in [401, 403]:
            await self.refresh()
            return True  # Retry the request
        return False
```

---

## Monitoring

```python
# src/monitor.py
import asyncio
import httpx
from loguru import logger

async def check_stock(client: httpx.AsyncClient, product_id: str) -> str:
    """Check product availability. Returns status string."""
    url = f"https://www.pokemoncenter.com/api/product/{product_id}/availability"

    response = await client.get(url)
    data = response.json()

    return data.get("status", "UNKNOWN")

async def monitor_product(
    client: httpx.AsyncClient,
    product_id: str,
    interval: float = 0.3,
    on_stock_callback = None,
):
    """Poll product until in stock."""
    log = logger.bind(component="MONITOR")
    poll_count = 0

    while True:
        poll_count += 1

        try:
            status = await check_stock(client, product_id)

            if status == "IN_STOCK":
                log.success(f"{product_id} — IN STOCK after {poll_count} polls!")
                if on_stock_callback:
                    await on_stock_callback(product_id)
                return

            if poll_count % 100 == 0:  # Log every 100 polls
                log.debug(f"{product_id} — poll #{poll_count}, status: {status}")

        except httpx.RequestError as e:
            log.warning(f"{product_id} — request error: {e}")

        await asyncio.sleep(interval)
```

---

## Proxy Pool

```python
# src/proxy.py
import random
from dataclasses import dataclass, field
from loguru import logger

@dataclass
class Proxy:
    url: str
    failures: int = 0
    is_healthy: bool = True

@dataclass
class ProxyPool:
    proxies: list[Proxy] = field(default_factory=list)
    max_failures: int = 3

    def add(self, url: str):
        self.proxies.append(Proxy(url=url))

    def get(self) -> str | None:
        """Get a healthy proxy URL."""
        healthy = [p for p in self.proxies if p.is_healthy]

        if not healthy:
            logger.bind(component="PROXY").warning("No healthy proxies available!")
            return None

        return random.choice(healthy).url

    def mark_failed(self, url: str):
        """Mark a proxy as failed. Disable if too many failures."""
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.failures += 1
                if proxy.failures >= self.max_failures:
                    proxy.is_healthy = False
                    logger.bind(component="PROXY").warning(
                        f"Disabled proxy after {proxy.failures} failures: {url[:30]}..."
                    )
                break

    def mark_success(self, url: str):
        """Reset failure count on success."""
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.failures = 0
                break

    def reset_all(self):
        """Re-enable all proxies."""
        for proxy in self.proxies:
            proxy.failures = 0
            proxy.is_healthy = True

# Usage
pool = ProxyPool()
pool.add("http://user:pass@proxy1.example.com:8080")
pool.add("http://user:pass@proxy2.example.com:8080")

async with httpx.AsyncClient(proxy=pool.get()) as client:
    response = await client.get(url)
```

---

## CAPTCHA Handling

```python
# src/captcha.py
import asyncio
from playwright.async_api import async_playwright
from loguru import logger
from .notifier import notify

async def detect_captcha(response) -> bool:
    """Check if response contains a CAPTCHA challenge."""
    if response.status_code == 429:
        return True

    try:
        data = response.json()
        if data.get("captcha") or data.get("challenge"):
            return True
    except:
        pass

    # Check for Cloudflare challenge
    if "cf-ray" in response.headers:
        text = response.text
        if "challenge" in text.lower() or "cf_clearance" in text:
            return True

    return False

async def solve_captcha_manually(url: str) -> str | None:
    """Open browser for manual CAPTCHA solve, return token."""
    log = logger.bind(component="CAPTCHA")
    log.warning(f"CAPTCHA detected! Opening browser...")

    await notify("CAPTCHA needed — check your browser", color=0xFFAA00)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url)

        log.info("Waiting for CAPTCHA solve...")

        # Wait for navigation away from challenge page
        try:
            await page.wait_for_url(
                lambda u: "challenge" not in u and "captcha" not in u.lower(),
                timeout=120000  # 2 minute timeout
            )
        except:
            log.error("CAPTCHA solve timed out")
            await browser.close()
            return None

        # Extract any tokens from cookies or page
        cookies = await context.cookies()
        token = next(
            (c["value"] for c in cookies if "cf_clearance" in c["name"]),
            None
        )

        log.success("CAPTCHA solved!")
        await browser.close()

        return token
```

---

## Discord Notifications

```python
# src/notifier.py
import os
import httpx
from loguru import logger

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

COLORS = {
    "success": 0x00FF00,  # Green
    "warning": 0xFFAA00,  # Orange
    "error": 0xFF0000,    # Red
    "info": 0x0099FF,     # Blue
}

async def notify(
    message: str,
    title: str = "Pokemon Bot",
    color: int = None,
    level: str = "info",
):
    """Send Discord webhook notification."""
    if not WEBHOOK_URL:
        logger.bind(component="NOTIFY").warning("No Discord webhook configured")
        return

    if color is None:
        color = COLORS.get(level, COLORS["info"])

    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color,
        }]
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_URL, json=payload)
    except httpx.RequestError as e:
        logger.bind(component="NOTIFY").error(f"Failed to send notification: {e}")

# Convenience functions
async def notify_stock(product_id: str):
    await notify(f"**STOCK DETECTED**\n`{product_id}`", level="success")

async def notify_success(order_id: str):
    await notify(f"**ORDER PLACED**\nConfirmation: `{order_id}`", level="success")

async def notify_error(error: str):
    await notify(f"**ERROR**\n{error}", level="error")
```

---

## Error Handling

```python
import asyncio
import httpx
from loguru import logger

async def safe_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retries: int = 3,
    **kwargs,
) -> httpx.Response | None:
    """Make request with retry logic and error handling."""
    log = logger.bind(component="HTTP")

    for attempt in range(retries):
        try:
            response = await client.request(method, url, **kwargs)

            # Rate limited
            if response.status_code == 429:
                wait = 2 ** attempt
                log.warning(f"Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue

            # Auth error
            if response.status_code in [401, 403]:
                log.warning("Auth error, refreshing session...")
                # await session_manager.refresh()
                continue

            return response

        except httpx.RequestError as e:
            log.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(1)
            else:
                return None

    log.error(f"All {retries} attempts failed for {url}")
    return None
```

---

## Task Management (CSV Import)

Inspired by [Ganesh Bot](https://ganeshbot.com/)'s task system — CSV import for bulk task creation and profile management.

### Task States

```
IDLE → MONITORING → CARTED → CHECKOUT → SUCCESS
                 ↓           ↓
              WAITING     FAILED
            (CAPTCHA)
```

### CSV Task File Format

```csv
# tasks.csv
product_id,size,profile,proxy_group,priority
pokemon-pikachu-plush,ONE_SIZE,profile_1,residential,high
pokemon-charizard-figure,ONE_SIZE,profile_2,datacenter,normal
pokemon-eevee-bundle,ONE_SIZE,profile_1,residential,high
```

### CSV Profile File Format

```csv
# profiles.csv
profile_name,email,first_name,last_name,address1,address2,city,state,zip,country,phone,card_number,card_exp,card_cvv
profile_1,john@email.com,John,Doe,123 Main St,,New York,NY,10001,US,5551234567,4111111111111111,12/26,123
profile_2,jane@email.com,Jane,Doe,456 Oak Ave,Apt 2,Los Angeles,CA,90001,US,5559876543,4222222222222222,06/27,456
```

### Task & Profile Manager

```python
# src/tasks.py
import csv
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from loguru import logger

class TaskState(Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    CARTED = "carted"
    CHECKOUT = "checkout"
    WAITING_CAPTCHA = "waiting_captcha"
    SUCCESS = "success"
    FAILED = "failed"

class Priority(Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

@dataclass
class Profile:
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
    id: str
    product_id: str
    size: str
    profile: Profile
    proxy_group: str
    priority: Priority = Priority.NORMAL
    state: TaskState = TaskState.IDLE
    poll_count: int = 0
    error: Optional[str] = None
    order_id: Optional[str] = None

class TaskManager:
    def __init__(self):
        self.tasks: list[Task] = []
        self.profiles: dict[str, Profile] = {}
        self.log = logger.bind(component="TASKS")

    def load_profiles(self, path: Path = Path("profiles.csv")):
        """Load profiles from CSV file."""
        if not path.exists():
            self.log.warning(f"No profiles file found at {path}")
            return

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
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

        self.log.success(f"Loaded {len(self.profiles)} profiles")

    def load_tasks(self, path: Path = Path("tasks.csv")):
        """Load tasks from CSV file."""
        if not path.exists():
            self.log.warning(f"No tasks file found at {path}")
            return

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                profile_name = row["profile"]
                if profile_name not in self.profiles:
                    self.log.error(f"Profile '{profile_name}' not found, skipping task")
                    continue

                task = Task(
                    id=f"task_{i:03d}",
                    product_id=row["product_id"],
                    size=row["size"],
                    profile=self.profiles[profile_name],
                    proxy_group=row.get("proxy_group", "default"),
                    priority=Priority(row.get("priority", "normal")),
                )
                self.tasks.append(task)

        self.log.success(f"Loaded {len(self.tasks)} tasks")

    def get_by_state(self, state: TaskState) -> list[Task]:
        """Get all tasks in a given state."""
        return [t for t in self.tasks if t.state == state]

    def get_summary(self) -> dict[str, int]:
        """Get count of tasks by state."""
        summary = {}
        for state in TaskState:
            summary[state.value] = len(self.get_by_state(state))
        return summary
```

### Multi-Task Runner

```python
# src/runner.py
import asyncio
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from loguru import logger

from .tasks import TaskManager, Task, TaskState
from .monitor import check_stock
from .cart import add_to_cart
from .checkout import run_checkout
from .captcha import detect_captcha, solve_captcha_manually
from .proxy import ProxyPool

console = Console()

def create_task_table(tasks: list[Task]) -> Table:
    """Create a rich table showing all task statuses."""
    table = Table(
        title="Tasks",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )

    table.add_column("ID", style="dim", width=10)
    table.add_column("Product", style="white", width=30)
    table.add_column("Size", justify="center", width=10)
    table.add_column("Profile", style="cyan", width=12)
    table.add_column("State", justify="center", width=15)
    table.add_column("Polls", justify="right", width=8)
    table.add_column("Info", style="dim", width=20)

    state_styles = {
        TaskState.IDLE: "dim",
        TaskState.MONITORING: "blue",
        TaskState.CARTED: "yellow",
        TaskState.CHECKOUT: "magenta",
        TaskState.WAITING_CAPTCHA: "yellow bold",
        TaskState.SUCCESS: "green bold",
        TaskState.FAILED: "red",
    }

    for task in tasks:
        style = state_styles.get(task.state, "white")
        info = task.order_id or task.error or ""

        table.add_row(
            task.id,
            task.product_id[:28] + ".." if len(task.product_id) > 30 else task.product_id,
            task.size,
            task.profile.name,
            f"[{style}]{task.state.value.upper()}[/]",
            str(task.poll_count),
            info[:18] + ".." if len(info) > 20 else info,
        )

    return table

def create_summary_panel(manager: TaskManager) -> Panel:
    """Create a summary panel with task counts."""
    summary = manager.get_summary()

    text = (
        f"[blue]Monitoring:[/] {summary['monitoring']}  "
        f"[yellow]Carted:[/] {summary['carted']}  "
        f"[magenta]Checkout:[/] {summary['checkout']}  "
        f"[green]Success:[/] {summary['success']}  "
        f"[red]Failed:[/] {summary['failed']}"
    )

    return Panel(text, title="Summary", border_style="dim")

async def run_single_task(task: Task, client, proxy_pool: ProxyPool):
    """Run a single task through the full flow."""
    log = logger.bind(component=task.id)

    # Monitor for stock
    task.state = TaskState.MONITORING

    while task.state == TaskState.MONITORING:
        task.poll_count += 1

        try:
            status = await check_stock(client, task.product_id)

            if status == "IN_STOCK":
                log.success(f"Stock found after {task.poll_count} polls!")
                task.state = TaskState.CARTED
                break

        except Exception as e:
            log.warning(f"Monitor error: {e}")

        await asyncio.sleep(0.3)

    # Add to cart
    if task.state == TaskState.CARTED:
        try:
            response = await add_to_cart(client, task.product_id, task.size)

            if await detect_captcha(response):
                task.state = TaskState.WAITING_CAPTCHA
                token = await solve_captcha_manually(response.url)
                if not token:
                    task.state = TaskState.FAILED
                    task.error = "CAPTCHA timeout"
                    return

            task.state = TaskState.CHECKOUT

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            return

    # Checkout
    if task.state == TaskState.CHECKOUT:
        try:
            order_id = await run_checkout(client, task.profile)
            task.state = TaskState.SUCCESS
            task.order_id = order_id
            log.success(f"Order placed: {order_id}")

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)

async def run_all_tasks(manager: TaskManager, proxy_pool: ProxyPool):
    """Run all tasks concurrently with live display."""
    import httpx

    async with httpx.AsyncClient() as client:
        # Sort by priority
        sorted_tasks = sorted(
            manager.tasks,
            key=lambda t: {"high": 0, "normal": 1, "low": 2}[t.priority.value]
        )

        # Create task coroutines
        coroutines = [
            run_single_task(task, client, proxy_pool)
            for task in sorted_tasks
        ]

        # Run with live display
        with Live(console=console, refresh_per_second=4) as live:
            async def update_display():
                while any(t.state not in [TaskState.SUCCESS, TaskState.FAILED] for t in manager.tasks):
                    table = create_task_table(manager.tasks)
                    summary = create_summary_panel(manager)
                    from rich.console import Group
                    live.update(Group(table, summary))
                    await asyncio.sleep(0.25)

            # Run tasks and display updater concurrently
            await asyncio.gather(
                *coroutines,
                update_display(),
            )

    # Final summary
    console.print(create_task_table(manager.tasks))
    console.print(create_summary_panel(manager))
```

### CLI Commands for Tasks

```python
# Add to src/main.py

@app.command()
def run(
    tasks_file: str = typer.Option("tasks.csv", "--tasks", "-t", help="Path to tasks CSV"),
    profiles_file: str = typer.Option("profiles.csv", "--profiles", "-P", help="Path to profiles CSV"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Monitor only"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug logging"),
):
    """Run bot with tasks from CSV files."""
    from .logger import setup_logger
    from .tasks import TaskManager
    from .proxy import ProxyPool
    from .runner import run_all_tasks

    setup_logger(debug=debug)

    manager = TaskManager()
    manager.load_profiles(Path(profiles_file))
    manager.load_tasks(Path(tasks_file))

    if not manager.tasks:
        console.print("[red]No tasks loaded. Check your CSV files.[/]")
        raise typer.Exit(1)

    proxy_pool = ProxyPool()
    # Load proxies from config...

    asyncio.run(run_all_tasks(manager, proxy_pool))

@app.command()
def validate(
    tasks_file: str = typer.Option("tasks.csv", "--tasks", "-t"),
    profiles_file: str = typer.Option("profiles.csv", "--profiles", "-P"),
):
    """Validate CSV files without running."""
    from .tasks import TaskManager

    manager = TaskManager()
    manager.load_profiles(Path(profiles_file))
    manager.load_tasks(Path(tasks_file))

    console.print(f"\n[green]Profiles:[/] {len(manager.profiles)}")
    console.print(f"[green]Tasks:[/] {len(manager.tasks)}")

    for task in manager.tasks:
        console.print(f"  • {task.product_id} / {task.size} → {task.profile.name}")

@app.command()
def export_template():
    """Export empty CSV templates."""
    tasks_template = "product_id,size,profile,proxy_group,priority\n"
    profiles_template = "profile_name,email,first_name,last_name,address1,address2,city,state,zip,country,phone,card_number,card_exp,card_cvv\n"

    Path("tasks.csv").write_text(tasks_template)
    Path("profiles.csv").write_text(profiles_template)

    console.print("[green]Created tasks.csv and profiles.csv templates[/]")
```

---

## .env Structure

```env
# Account credentials
PC_EMAIL=your@email.com
PC_PASSWORD=yourpassword

# Discord notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy

# Proxies (comma separated, optional)
PROXY_LIST=http://user:pass@host:port,http://user:pass@host2:port

# Timing
MONITOR_INTERVAL=0.3
CHECKOUT_TIMEOUT=30

# Target products (comma separated)
TARGET_PRODUCTS=product-id-1,product-id-2
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_monitor.py -v
```

### Mocking HTTP Calls

```python
# tests/test_monitor.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_check_stock_in_stock():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "IN_STOCK"}

    with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
        async with httpx.AsyncClient() as client:
            from src.monitor import check_stock
            status = await check_stock(client, "test-product")
            assert status == "IN_STOCK"

@pytest.mark.asyncio
async def test_check_stock_out_of_stock():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "OUT_OF_STOCK"}

    with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
        async with httpx.AsyncClient() as client:
            from src.monitor import check_stock
            status = await check_stock(client, "test-product")
            assert status == "OUT_OF_STOCK"
```

---

## Development Order

1. **Map endpoints** — Intercept all API calls in Chrome DevTools first
2. **Project scaffold** — Create all files, install deps
3. **Terminal setup** — Logger (`loguru`), CLI (`typer`), colors (`rich`)
4. **Task system** — CSV import for tasks & profiles
5. **Session management** — Login, cookie save/load
6. **Stock monitor** — Basic polling with state updates
7. **Multi-task runner** — Concurrent tasks with live display table
8. **Add to cart** — Fire cart request with proper headers
9. **Checkout flow** — Chain checkout API calls
10. **CAPTCHA handler** — Browser popup + manual solve
11. **Notifications** — Discord alerts
12. **Proxy rotation** — Pool with health tracking per task
13. **Polish** — Graceful shutdown, retry logic, tests

---

## Key Principles

- **HTTP mode > browser mode** — Playwright only for login/CAPTCHA
- **Headers must look real** — Wrong headers = instant block
- **Map before you code** — Understanding endpoints is 80% of the work
- **Sessions are fragile** — Build refresh logic from the start
- **Log everything** — Timestamps, responses, errors for debugging
- **Test on common items first** — Don't debug on limited drops
- **Terminal UX matters** — Colored, scannable output saves time
- **CSV for bulk ops** — Tasks & profiles via CSV, not hardcoded
- **One proxy per task** — Avoid reusing IPs across tasks
- **Focus beats breadth** — Support fewer sites well (like Ganesh)

---

## Sources & Inspiration

- [Ganesh Bot](https://ganeshbot.com/) — CLI-first design, task groups, 650k+ checkouts
- [Ganesh Bot Review](https://botsthatwork.com/review/ganesh/) — Success rate analysis
- [StellarAIO](https://learnretailarbitrage.com/stellaraio-review/) — CSV profile management
- [NSB Bot Guide](https://proxyreviewhub.com/nsb-bot/) — Task management best practices
