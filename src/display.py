"""Terminal display utilities using rich - Porter branding."""
from __future__ import annotations

from typing import List
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from .tasks import Task, TaskManager, State

# Brand colors
BRAND_PRIMARY = "#FFD700"      # Gold/Yellow (Pokemon)
BRAND_SECONDARY = "#3B4CCA"    # Blue
BRAND_ACCENT = "#FF0000"       # Red
BRAND_SUCCESS = "#00D26A"      # Green
BRAND_ERROR = "#FF3B3B"        # Red
BRAND_DIM = "#666666"          # Gray

console = Console()

# ASCII Art Logo
LOGO = """
[bold #FFD700]╔═══════════════════════════════════════════════════════════╗
║[/][bold white]  ██████╗  ██████╗ ██████╗ ████████╗███████╗██████╗        [/][bold #FFD700]║
║[/][bold white]  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗       [/][bold #FFD700]║
║[/][bold white]  ██████╔╝██║   ██║██████╔╝   ██║   █████╗  ██████╔╝       [/][bold #FFD700]║
║[/][bold white]  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══╝  ██╔══██╗       [/][bold #FFD700]║
║[/][bold white]  ██║     ╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║       [/][bold #FFD700]║
║[/][bold white]  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝       [/][bold #FFD700]║
╚═══════════════════════════════════════════════════════════╝[/]
"""

LOGO_SMALL = """[bold #FFD700]◆[/] [bold white]PORTER[/] [dim]v0.1.0[/]"""

TAGLINE = "[dim italic]Lightning-fast auto-purchase bot[/]"

# State color mapping
STATE_STYLES = {
    State.IDLE: "dim",
    State.MONITORING: "#3B4CCA bold",
    State.CARTED: "#FFD700 bold",
    State.CHECKOUT: "#FF69B4 bold",
    State.CAPTCHA: "#FFA500 bold blink",
    State.SUCCESS: "#00D26A bold",
    State.FAILED: "#FF3B3B",
}

STATE_ICONS = {
    State.IDLE: "○",
    State.MONITORING: "◉",
    State.CARTED: "◈",
    State.CHECKOUT: "◆",
    State.CAPTCHA: "⚠",
    State.SUCCESS: "✓",
    State.FAILED: "✗",
}


def print_banner(version: str = "0.1.0") -> None:
    """Print the Porter startup banner."""
    console.print(LOGO)
    console.print(Align.center(TAGLINE))
    console.print()


def print_banner_small() -> None:
    """Print a compact banner."""
    console.print()
    console.print(Panel(
        LOGO_SMALL + "  " + TAGLINE,
        border_style="#FFD700",
        padding=(0, 2),
    ))
    console.print()


def task_table(tasks: list[Task], compact: bool = False) -> Table:
    """Create a branded table showing task statuses."""
    table = Table(
        show_header=True,
        header_style="bold #FFD700",
        border_style="#3B4CCA",
        box=box.ROUNDED,
        title="[bold #FFD700]◆[/] [bold white]Tasks[/]",
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

        # Color the icon based on state
        icon_styled = f"[{style}]{icon}[/]"
        state_styled = f"[{style}]{t.state.value.upper()}[/]"

        # Highlight successful orders
        if t.state == State.SUCCESS and t.order_id:
            info = f"[#00D26A]{t.order_id[:18]}[/]"
        elif t.error:
            info = f"[#FF3B3B]{t.error[:18]}[/]"

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
        parts.append(f"[#3B4CCA]◉ {s['monitoring']} monitoring[/]")
    if s['carted'] > 0:
        parts.append(f"[#FFD700]◈ {s['carted']} carted[/]")
    if s['checkout'] > 0:
        parts.append(f"[#FF69B4]◆ {s['checkout']} checkout[/]")
    if s['success'] > 0:
        parts.append(f"[#00D26A]✓ {s['success']} success[/]")
    if s['failed'] > 0:
        parts.append(f"[#FF3B3B]✗ {s['failed']} failed[/]")

    if not parts:
        parts.append("[dim]○ Ready to start[/]")

    text = "  ".join(parts)

    return Panel(
        Align.center(text),
        border_style="#3B4CCA",
        padding=(0, 1),
    )


def status_bar(manager: TaskManager) -> Panel:
    """Create a compact status bar for live display."""
    s = manager.summary()
    total = len(manager.tasks)
    active = s['monitoring'] + s['carted'] + s['checkout']

    # Progress indicator
    if s['success'] + s['failed'] == total:
        status = "[#00D26A]● Complete[/]"
    elif active > 0:
        status = "[#FFD700]● Running[/]"
    else:
        status = "[dim]○ Idle[/]"

    text = f"{status}  [dim]│[/]  " + "  ".join([
        f"[#3B4CCA]{s['monitoring']}[/] [dim]mon[/]",
        f"[#FFD700]{s['carted']}[/] [dim]cart[/]",
        f"[#FF69B4]{s['checkout']}[/] [dim]chk[/]",
        f"[#00D26A]{s['success']}[/] [dim]ok[/]",
        f"[#FF3B3B]{s['failed']}[/] [dim]fail[/]",
    ])

    return Panel(
        text,
        border_style="dim",
        padding=(0, 1),
    )


def full_display(manager: TaskManager) -> Group:
    """Create full branded display with table and summary."""
    return Group(
        task_table(manager.tasks),
        "",
        summary_panel(manager),
    )


def success_box(message: str, title: str = "Success") -> Panel:
    """Create a success message box."""
    return Panel(
        f"[#00D26A]✓[/] {message}",
        title=f"[bold #00D26A]{title}[/]",
        border_style="#00D26A",
        padding=(0, 2),
    )


def error_box(message: str, title: str = "Error") -> Panel:
    """Create an error message box."""
    return Panel(
        f"[#FF3B3B]✗[/] {message}",
        title=f"[bold #FF3B3B]{title}[/]",
        border_style="#FF3B3B",
        padding=(0, 2),
    )


def warning_box(message: str, title: str = "Warning") -> Panel:
    """Create a warning message box."""
    return Panel(
        f"[#FFA500]⚠[/] {message}",
        title=f"[bold #FFA500]{title}[/]",
        border_style="#FFA500",
        padding=(0, 2),
    )


def info_box(message: str, title: str = "Info") -> Panel:
    """Create an info message box."""
    return Panel(
        f"[#3B4CCA]ℹ[/] {message}",
        title=f"[bold #3B4CCA]{title}[/]",
        border_style="#3B4CCA",
        padding=(0, 2),
    )


def print_startup_info(tasks_count: int, profiles_count: int, cookies_ok: bool, proxy_count: int) -> None:
    """Print startup information in a nice format."""
    table = Table(
        show_header=False,
        box=box.SIMPLE,
        padding=(0, 2),
        border_style="dim",
    )

    table.add_column("Label", style="dim")
    table.add_column("Value", style="white")
    table.add_column("Status")

    # Tasks
    table.add_row(
        "Tasks",
        str(tasks_count),
        "[#00D26A]✓[/]" if tasks_count > 0 else "[#FF3B3B]✗[/]"
    )

    # Profiles
    table.add_row(
        "Profiles",
        str(profiles_count),
        "[#00D26A]✓[/]" if profiles_count > 0 else "[#FF3B3B]✗[/]"
    )

    # Cookies
    table.add_row(
        "Session",
        "Authenticated" if cookies_ok else "Not logged in",
        "[#00D26A]✓[/]" if cookies_ok else "[#FF3B3B]✗[/]"
    )

    # Proxies
    table.add_row(
        "Proxies",
        str(proxy_count) if proxy_count > 0 else "Direct",
        "[#00D26A]✓[/]" if proxy_count > 0 else "[dim]○[/]"
    )

    console.print(Panel(
        table,
        title="[bold #FFD700]◆[/] [bold white]Configuration[/]",
        border_style="#3B4CCA",
    ))
