"""Terminal display utilities using rich - Porter branding ⚡."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from .tasks import Task, TaskManager, State

# ═══════════════════════════════════════════════════════════════════════════════
# BRAND COLORS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_PRIMARY = "#FFD700"      # Gold/Yellow (Pikachu!)
BRAND_SECONDARY = "#3B4CCA"    # Blue
BRAND_ACCENT = "#FF0000"       # Red
BRAND_SUCCESS = "#00D26A"      # Green
BRAND_ERROR = "#FF3B3B"        # Red
BRAND_WARNING = "#FFA500"      # Orange
BRAND_DIM = "#666666"          # Gray

# Lightning themed constants
LIGHTNING = "⚡"
LIGHTNING_BOLT = f"[{BRAND_PRIMARY}]{LIGHTNING}[/]"

console = Console()

# Speed-focused taglines
SPEED_TAGLINES = [
    "Lightning-fast auto-purchase bot",
    "Faster than Pikachu's Thunder Shock",
    "Quick as a Thunderbolt",
    "Speed that shocks the competition",
    "Catch 'em all, at lightning speed",
]

# ═══════════════════════════════════════════════════════════════════════════════
# ASCII ART LOGOS
# ═══════════════════════════════════════════════════════════════════════════════

LOGO = f"""
[bold {BRAND_PRIMARY}]╔═══════════════════════════════════════════════════════════╗
║[/][bold white]  ██████╗  ██████╗ ██████╗ ████████╗███████╗██████╗        [/][bold {BRAND_PRIMARY}]║
║[/][bold white]  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗       [/][bold {BRAND_PRIMARY}]║
║[/][bold white]  ██████╔╝██║   ██║██████╔╝   ██║   █████╗  ██████╔╝       [/][bold {BRAND_PRIMARY}]║
║[/][bold white]  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══╝  ██╔══██╗       [/][bold {BRAND_PRIMARY}]║
║[/][bold white]  ██║     ╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║       [/][bold {BRAND_PRIMARY}]║
║[/][bold white]  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝       [/][bold {BRAND_PRIMARY}]║
╚═══════════════════════════════════════════════════════════╝[/]
"""

LOGO_SMALL = f"[bold {BRAND_PRIMARY}]{LIGHTNING}[/] [bold white]PORTER[/] [dim]v0.1.0[/]"

LOGO_MINI = f"[bold {BRAND_PRIMARY}]{LIGHTNING}[/] [bold white]PORTER[/] [dim]v0.1.0[/] [dim]│[/] [italic dim]Lightning fast[/]"

TAGLINE = "[dim italic]Lightning-fast auto-purchase bot[/]"

# ═══════════════════════════════════════════════════════════════════════════════
# STATE STYLING
# ═══════════════════════════════════════════════════════════════════════════════

STATE_STYLES = {
    State.IDLE: "dim",
    State.MONITORING: f"{BRAND_PRIMARY} bold",
    State.CARTED: f"{BRAND_PRIMARY} bold",
    State.CHECKOUT: "#FF69B4 bold",
    State.CAPTCHA: f"{BRAND_WARNING} bold blink",
    State.SUCCESS: f"{BRAND_SUCCESS} bold",
    State.FAILED: BRAND_ERROR,
}

STATE_ICONS = {
    State.IDLE: "○",
    State.MONITORING: LIGHTNING,  # Lightning for active monitoring!
    State.CARTED: "◈",
    State.CHECKOUT: "◆",
    State.CAPTCHA: "⚠",
    State.SUCCESS: "✓",
    State.FAILED: "✗",
}


# ═══════════════════════════════════════════════════════════════════════════════
# BANNER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner(version: str = "0.1.0") -> None:
    """Print the Porter startup banner."""
    console.print(LOGO)
    tagline = random.choice(SPEED_TAGLINES)
    console.print(Align.center(f"[dim italic]{tagline}[/]"))
    console.print()


def print_banner_small() -> None:
    """Print a compact banner."""
    console.print()
    console.print(Panel(
        LOGO_MINI,
        border_style=BRAND_PRIMARY,
        padding=(0, 2),
    ))
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK STATUS (Instant, no network calls)
# ═══════════════════════════════════════════════════════════════════════════════

def get_quick_status() -> dict:
    """Get instant status from files only - no network calls for speed."""
    data_dir = Path("data")

    status = {
        "cookies": False,
        "cookies_count": 0,
        "tasks": 0,
        "profiles": 0,
        "proxies": 0,
        "discord": False,
        "env_exists": Path(".env").exists(),
    }

    # Check cookies
    cookies_path = data_dir / "cookies.json"
    if cookies_path.exists():
        try:
            cookies = json.loads(cookies_path.read_text())
            status["cookies"] = True
            status["cookies_count"] = len(cookies)
        except:
            pass

    # Check tasks CSV
    tasks_path = data_dir / "tasks.csv"
    if tasks_path.exists():
        try:
            lines = tasks_path.read_text().strip().split('\n')
            status["tasks"] = max(0, len(lines) - 1)  # Minus header
        except:
            pass

    # Check profiles CSV
    profiles_path = data_dir / "profiles.csv"
    if profiles_path.exists():
        try:
            lines = profiles_path.read_text().strip().split('\n')
            status["profiles"] = max(0, len(lines) - 1)
        except:
            pass

    # Check proxies
    proxies_path = data_dir / "proxies.txt"
    if proxies_path.exists():
        try:
            lines = [l for l in proxies_path.read_text().splitlines()
                     if l.strip() and not l.startswith('#')]
            status["proxies"] = len(lines)
        except:
            pass

    # Check Discord webhook in .env
    if Path(".env").exists():
        try:
            content = Path(".env").read_text()
            if "DISCORD_WEBHOOK_URL=" in content:
                # Check it's not empty
                for line in content.splitlines():
                    if line.startswith("DISCORD_WEBHOOK_URL="):
                        value = line.split("=", 1)[1].strip().strip('"').strip("'")
                        status["discord"] = bool(value)
                        break
        except:
            pass

    return status


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def create_status_dashboard(status: dict) -> Panel:
    """Create the status dashboard panel."""
    items = []

    # Session status
    if status["cookies"]:
        items.append(f"  [{BRAND_SUCCESS}]●[/] Session    [dim]({status['cookies_count']} cookies)[/]")
    else:
        items.append(f"  [{BRAND_ERROR}]○[/] Session    [dim]Not logged in[/]")

    # Tasks
    if status["tasks"] > 0:
        items.append(f"  [{BRAND_SUCCESS}]●[/] Tasks      [white]{status['tasks']}[/] [dim]ready[/]")
    else:
        items.append(f"  [{BRAND_ERROR}]○[/] Tasks      [dim]None configured[/]")

    # Profiles
    if status["profiles"] > 0:
        items.append(f"  [{BRAND_SUCCESS}]●[/] Profiles   [white]{status['profiles']}[/] [dim]loaded[/]")
    else:
        items.append(f"  [{BRAND_ERROR}]○[/] Profiles   [dim]None configured[/]")

    # Proxies (optional)
    if status["proxies"] > 0:
        items.append(f"  [{BRAND_SUCCESS}]●[/] Proxies    [white]{status['proxies']}[/] [dim]available[/]")
    else:
        items.append(f"  [dim]○[/] Proxies    [dim]Direct connection[/]")

    # Discord (optional)
    if status["discord"]:
        items.append(f"  [{BRAND_SUCCESS}]●[/] Discord    [dim]Configured[/]")
    else:
        items.append(f"  [dim]○[/] Discord    [dim]Not configured[/]")

    text = "\n".join(items)

    return Panel(
        text,
        title=f"{LIGHTNING_BOLT} [bold white]Status[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    )


def create_menu_panel() -> Panel:
    """Create the quick actions menu panel."""
    menu_items = f"""
  [{BRAND_PRIMARY}]1[/]  [bold white]run[/]         Start monitoring & auto-purchase
  [{BRAND_PRIMARY}]2[/]  [bold white]add-task[/]    Add product to monitor [dim](paste URL)[/]
  [{BRAND_PRIMARY}]3[/]  [bold white]list-tasks[/]  View all tasks
  [{BRAND_PRIMARY}]4[/]  [bold white]login[/]       Capture session cookies
  [{BRAND_PRIMARY}]5[/]  [bold white]status[/]      Full status dashboard
  [{BRAND_PRIMARY}]6[/]  [bold white]guide[/]       Quick start tutorial

  [dim]────────────────────────────────────[/]

  [{BRAND_PRIMARY}]s[/]  [bold white]setup[/]       Run setup wizard
  [{BRAND_PRIMARY}]?[/]  [bold white]help[/]        Show all commands
"""

    return Panel(
        menu_items,
        title=f"{LIGHTNING_BOLT} [bold white]Quick Actions[/]",
        border_style=BRAND_PRIMARY,
        padding=(0, 1),
    )


def show_interactive_menu() -> None:
    """Display the interactive menu with status dashboard."""
    console.print()
    console.print(LOGO_MINI)
    console.print()

    # Quick status (instant, file-based)
    status = get_quick_status()

    # Status dashboard
    console.print(create_status_dashboard(status))
    console.print()

    # Menu
    console.print(create_menu_panel())
    console.print()

    # Hint
    console.print(f"  [dim]Type[/] [bold white]porter <command>[/] [dim]to run a command[/]")
    console.print()


def show_full_status() -> None:
    """Display comprehensive status dashboard."""
    console.print()
    console.print(LOGO_SMALL)
    console.print()

    status = get_quick_status()

    # Configuration table
    config_table = Table(
        show_header=False,
        box=box.SIMPLE,
        padding=(0, 1),
        expand=True,
    )
    config_table.add_column("Item", style="dim", width=12)
    config_table.add_column("Value", style="white")
    config_table.add_column("Status", justify="center", width=3)

    # Session
    if status["cookies"]:
        config_table.add_row("Session", f"{status['cookies_count']} cookies", f"[{BRAND_SUCCESS}]●[/]")
    else:
        config_table.add_row("Session", "Not configured", f"[{BRAND_ERROR}]○[/]")

    # Tasks
    config_table.add_row(
        "Tasks",
        f"{status['tasks']} configured" if status['tasks'] else "None",
        f"[{BRAND_SUCCESS}]●[/]" if status['tasks'] else f"[{BRAND_ERROR}]○[/]"
    )

    # Profiles
    config_table.add_row(
        "Profiles",
        f"{status['profiles']} loaded" if status['profiles'] else "None",
        f"[{BRAND_SUCCESS}]●[/]" if status['profiles'] else f"[{BRAND_ERROR}]○[/]"
    )

    # Proxies
    config_table.add_row(
        "Proxies",
        f"{status['proxies']} available" if status['proxies'] else "Direct",
        f"[{BRAND_SUCCESS}]●[/]" if status['proxies'] else "[dim]○[/]"
    )

    # Discord
    config_table.add_row(
        "Discord",
        "Configured" if status['discord'] else "Not set",
        f"[{BRAND_SUCCESS}]●[/]" if status['discord'] else "[dim]○[/]"
    )

    # .env
    config_table.add_row(
        ".env",
        "Found" if status['env_exists'] else "Missing",
        f"[{BRAND_SUCCESS}]●[/]" if status['env_exists'] else f"[{BRAND_ERROR}]○[/]"
    )

    console.print(Panel(
        config_table,
        title=f"{LIGHTNING_BOLT} [bold white]Configuration[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 1),
    ))

    # Readiness check
    ready_items = [
        status["cookies"],
        status["tasks"] > 0,
        status["profiles"] > 0,
    ]
    ready_count = sum(ready_items)
    total_required = len(ready_items)

    if ready_count == total_required:
        readiness = f"[bold {BRAND_SUCCESS}]{LIGHTNING} READY TO RUN {LIGHTNING}[/]"
        readiness_style = BRAND_SUCCESS
        suggestion = "Run [bold]porter run[/] to start monitoring"
    elif ready_count >= 2:
        readiness = f"[bold {BRAND_WARNING}]ALMOST READY[/]"
        readiness_style = BRAND_WARNING
        suggestion = "Run [bold]porter setup[/] to complete configuration"
    else:
        readiness = f"[bold {BRAND_ERROR}]SETUP REQUIRED[/]"
        readiness_style = BRAND_ERROR
        suggestion = "Run [bold]porter setup[/] to get started"

    console.print()
    console.print(Panel(
        f"{readiness}\n\n[dim]{suggestion}[/]",
        border_style=readiness_style,
        padding=(0, 2),
    ))
    console.print()


def show_quick_guide() -> None:
    """Display the quick start tutorial."""
    console.print()
    console.print(Panel(
        f"[bold {BRAND_PRIMARY}]{LIGHTNING} PORTER QUICK START GUIDE {LIGHTNING}[/]",
        border_style=BRAND_PRIMARY,
        padding=(0, 4),
    ))
    console.print()

    steps = [
        ("1", "Setup",
         f"Run [bold cyan]porter setup[/] to configure everything\n"
         "Or manually create .env, data/profiles.csv, data/tasks.csv"),

        ("2", "Login",
         f"Run [bold cyan]porter login[/] to capture session cookies\n"
         "Log in manually in the browser that opens"),

        ("3", "Add Tasks",
         f"Edit [bold cyan]data/tasks.csv[/] with products to monitor:\n"
         "[dim]product_id,size,profile,proxy_group,priority\n"
         "pikachu-plush,ONE_SIZE,default,residential,high[/]"),

        ("4", "Validate",
         f"Run [bold cyan]porter validate[/] to check your configuration\n"
         f"Run [bold cyan]porter health[/] to test connectivity"),

        ("5", "Run",
         f"Run [bold cyan]porter run[/] to start monitoring\n"
         f"Use [bold cyan]porter run --dry-run[/] to test without purchasing"),
    ]

    for num, title, content in steps:
        console.print(Panel(
            content,
            title=f"[bold {BRAND_PRIMARY}]Step {num}:[/] [bold white]{title}[/]",
            border_style=BRAND_SECONDARY,
            padding=(0, 2),
        ))
        console.print()

    # Pro tips
    tips = f"""
[bold {BRAND_PRIMARY}]{LIGHTNING} Pro Tips:[/]

  [{BRAND_PRIMARY}]{LIGHTNING}[/] Use [bold]residential proxies[/] for checkout tasks
  [{BRAND_PRIMARY}]{LIGHTNING}[/] Set [bold]high priority[/] for limited drops
  [{BRAND_PRIMARY}]{LIGHTNING}[/] Monitor multiple products with separate tasks
  [{BRAND_PRIMARY}]{LIGHTNING}[/] Keep browser ready for CAPTCHA challenges
  [{BRAND_PRIMARY}]{LIGHTNING}[/] Test with common items before limited releases
"""

    console.print(Panel(
        tips,
        title=f"[bold white]Speed Tips[/]",
        border_style=BRAND_PRIMARY,
        padding=(0, 2),
    ))

    console.print()
    console.print(f"  [dim]Run [bold]porter --help[/] for all commands[/]")
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# TASK TABLE & SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

def task_table(tasks: list[Task], compact: bool = False) -> Table:
    """Create a branded table showing task statuses."""
    table = Table(
        show_header=True,
        header_style=f"bold {BRAND_PRIMARY}",
        border_style=BRAND_SECONDARY,
        box=box.ROUNDED,
        title=f"{LIGHTNING_BOLT} [bold white]Tasks[/]",
        title_justify="left",
        padding=(0, 1),
    )

    table.add_column("", justify="center", width=3)  # Status icon
    table.add_column("Product", style="white", min_width=24)
    table.add_column("Size", justify="center", width=8, style="cyan")
    table.add_column("Profile", style="dim", width=10)
    table.add_column("State", justify="center", width=14)
    table.add_column("Polls", justify="right", width=6, style="dim")
    table.add_column("Info", style="dim", min_width=12)

    for t in tasks:
        style = STATE_STYLES.get(t.state, "white")
        icon = STATE_ICONS.get(t.state, "○")
        product = t.product_id[:22] + ".." if len(t.product_id) > 24 else t.product_id
        info = (t.order_id or t.error or "")[:20]

        icon_styled = f"[{style}]{icon}[/]"
        state_styled = f"[{style}]{t.state.value.upper()}[/]"

        if t.state == State.SUCCESS and t.order_id:
            info = f"[{BRAND_SUCCESS}]{t.order_id[:18]}[/]"
        elif t.error:
            info = f"[{BRAND_ERROR}]{t.error[:18]}[/]"

        table.add_row(
            icon_styled,
            product,
            t.size or "-",
            t.profile.name[:10],
            state_styled,
            str(t.polls),
            info,
        )

    return table


def summary_panel(manager: TaskManager) -> Panel:
    """Create a branded summary panel with task counts."""
    s = manager.summary()

    parts = []

    if s['monitoring'] > 0:
        parts.append(f"[{BRAND_SECONDARY}]{LIGHTNING} {s['monitoring']} monitoring[/]")
    if s['carted'] > 0:
        parts.append(f"[{BRAND_PRIMARY}]◈ {s['carted']} carted[/]")
    if s['checkout'] > 0:
        parts.append(f"[#FF69B4]◆ {s['checkout']} checkout[/]")
    if s['success'] > 0:
        parts.append(f"[{BRAND_SUCCESS}]✓ {s['success']} success[/]")
    if s['failed'] > 0:
        parts.append(f"[{BRAND_ERROR}]✗ {s['failed']} failed[/]")

    if not parts:
        parts.append("[dim]○ Ready to start[/]")

    text = "  ".join(parts)

    return Panel(
        Align.center(text),
        border_style=BRAND_SECONDARY,
        padding=(0, 1),
    )


def status_bar(manager: TaskManager) -> Panel:
    """Create a compact status bar for live display."""
    s = manager.summary()
    total = len(manager.tasks)
    active = s['monitoring'] + s['carted'] + s['checkout']

    if s['success'] + s['failed'] == total:
        status = f"[{BRAND_SUCCESS}]● Complete[/]"
    elif active > 0:
        status = f"[{BRAND_PRIMARY}]{LIGHTNING} Running[/]"
    else:
        status = "[dim]○ Idle[/]"

    text = f"{status}  [dim]│[/]  " + "  ".join([
        f"[{BRAND_SECONDARY}]{s['monitoring']}[/] [dim]mon[/]",
        f"[{BRAND_PRIMARY}]{s['carted']}[/] [dim]cart[/]",
        f"[#FF69B4]{s['checkout']}[/] [dim]chk[/]",
        f"[{BRAND_SUCCESS}]{s['success']}[/] [dim]ok[/]",
        f"[{BRAND_ERROR}]{s['failed']}[/] [dim]fail[/]",
    ])

    return Panel(text, border_style="dim", padding=(0, 1))


def full_display(manager: TaskManager) -> Group:
    """Create full branded display with table and summary."""
    return Group(
        task_table(manager.tasks),
        "",
        summary_panel(manager),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE BOXES
# ═══════════════════════════════════════════════════════════════════════════════

def success_box(message: str, title: str = "Success") -> Panel:
    """Create a success message box."""
    return Panel(
        f"[{BRAND_SUCCESS}]✓[/] {message}",
        title=f"[bold {BRAND_SUCCESS}]{title}[/]",
        border_style=BRAND_SUCCESS,
        padding=(0, 2),
    )


def error_box(message: str, title: str = "Error") -> Panel:
    """Create an error message box."""
    return Panel(
        f"[{BRAND_ERROR}]✗[/] {message}",
        title=f"[bold {BRAND_ERROR}]{title}[/]",
        border_style=BRAND_ERROR,
        padding=(0, 2),
    )


def warning_box(message: str, title: str = "Warning") -> Panel:
    """Create a warning message box."""
    return Panel(
        f"[{BRAND_WARNING}]⚠[/] {message}",
        title=f"[bold {BRAND_WARNING}]{title}[/]",
        border_style=BRAND_WARNING,
        padding=(0, 2),
    )


def info_box(message: str, title: str = "Info") -> Panel:
    """Create an info message box."""
    return Panel(
        f"[{BRAND_SECONDARY}]ℹ[/] {message}",
        title=f"[bold {BRAND_SECONDARY}]{title}[/]",
        border_style=BRAND_SECONDARY,
        padding=(0, 2),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def speed_message(text: str) -> str:
    """Wrap message with lightning bolt prefix."""
    return f"{LIGHTNING_BOLT} {text}"


def instant_feedback(message: str) -> None:
    """Print instant feedback message."""
    console.print(f"  {LIGHTNING_BOLT} {message}")
