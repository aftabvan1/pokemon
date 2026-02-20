"""Terminal display utilities using rich."""
from __future__ import annotations

from typing import List
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from .tasks import Task, TaskManager, State

console = Console()

# State color mapping
STATE_STYLES = {
    State.IDLE: "dim",
    State.MONITORING: "blue",
    State.CARTED: "yellow",
    State.CHECKOUT: "magenta",
    State.CAPTCHA: "yellow bold",
    State.SUCCESS: "green bold",
    State.FAILED: "red",
}


def task_table(tasks: list[Task]) -> Table:
    """Create a table showing task statuses."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        title="Tasks",
    )

    table.add_column("ID", style="dim", width=6)
    table.add_column("Product", width=32)
    table.add_column("Size", justify="center", width=8)
    table.add_column("Profile", style="cyan", width=10)
    table.add_column("State", justify="center", width=12)
    table.add_column("Polls", justify="right", width=7)
    table.add_column("Info", style="dim", width=16)

    for t in tasks:
        style = STATE_STYLES.get(t.state, "white")
        product = t.product_id[:30] + ".." if len(t.product_id) > 32 else t.product_id
        info = (t.order_id or t.error or "")[:14]

        table.add_row(
            t.id,
            product,
            t.size,
            t.profile.name[:10],
            f"[{style}]{t.state.value.upper()}[/]",
            str(t.polls),
            info,
        )

    return table


def summary_panel(manager: TaskManager) -> Panel:
    """Create a summary panel with task counts."""
    s = manager.summary()
    text = (
        f"[blue]Monitoring:[/] {s['monitoring']}  "
        f"[yellow]Carted:[/] {s['carted']}  "
        f"[magenta]Checkout:[/] {s['checkout']}  "
        f"[green]Success:[/] {s['success']}  "
        f"[red]Failed:[/] {s['failed']}"
    )
    return Panel(text, title="Summary", border_style="dim")


def full_display(manager: TaskManager) -> Group:
    """Create full display with table and summary."""
    return Group(task_table(manager.tasks), summary_panel(manager))
