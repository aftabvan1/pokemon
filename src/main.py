"""CLI entry point using typer."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from . import logger
from .config import Config
from .display import console, task_table, summary_panel
from .tasks import TaskManager

__version__ = "0.1.0"


def version_callback(value: bool):
    if value:
        console.print(f"[bold]Porter[/] v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="porter",
    help="Porter - Auto-purchase bot",
    add_completion=False,
)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
):
    """Porter - Auto-purchase bot."""
    pass


@app.command()
def run(
    tasks: Path = typer.Option(
        Path("data/tasks.csv"), "--tasks", "-t", help="Tasks CSV file"
    ),
    profiles: Path = typer.Option(
        Path("data/profiles.csv"), "--profiles", "-p", help="Profiles CSV file"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Monitor only, no purchase"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
):
    """Start the bot with tasks from CSV files."""
    logger.setup(debug=debug)
    log = logger.get("MAIN")

    config = Config.load()
    manager = TaskManager()

    manager.load_profiles(profiles)
    manager.load_tasks(tasks)

    if not manager.tasks:
        console.print("[red]No tasks loaded. Check your CSV files.[/]")
        raise typer.Exit(1)

    console.print(task_table(manager.tasks))
    console.print(summary_panel(manager))

    if dry_run:
        log.info("Dry run mode — validated, not starting")
        return

    from .runner import run_all
    from .proxy import ProxyPool

    pool = ProxyPool()
    pool.load(Path("data/proxies.txt"))

    log.info(f"Starting {len(manager.tasks)} tasks...")
    asyncio.run(run_all(manager, pool, config.monitor_interval))


@app.command()
def validate(
    tasks: Path = typer.Option(Path("data/tasks.csv"), "--tasks", "-t"),
    profiles: Path = typer.Option(Path("data/profiles.csv"), "--profiles", "-p"),
):
    """Validate CSV files without running."""
    logger.setup()

    manager = TaskManager()
    manager.load_profiles(profiles)
    manager.load_tasks(tasks)

    console.print(f"\n[green]Profiles:[/] {len(manager.profiles)}")
    console.print(f"[green]Tasks:[/] {len(manager.tasks)}\n")

    if manager.tasks:
        console.print(task_table(manager.tasks))


@app.command()
def login():
    """Capture session cookies via browser login."""
    logger.setup()

    from .session import capture_session
    asyncio.run(capture_session())


@app.command()
def templates():
    """Create empty CSV template files."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    tasks_csv = data_dir / "tasks.csv"
    profiles_csv = data_dir / "profiles.csv"

    if not tasks_csv.exists():
        tasks_csv.write_text(
            "product_id,size,profile,proxy_group,priority\n"
        )
        console.print(f"[green]Created {tasks_csv}[/]")

    if not profiles_csv.exists():
        profiles_csv.write_text(
            "profile_name,email,first_name,last_name,address1,address2,"
            "city,state,zip,country,phone,card_number,card_exp,card_cvv\n"
        )
        console.print(f"[green]Created {profiles_csv}[/]")


@app.command()
def test_notify():
    """Send a test Discord notification."""
    logger.setup()

    config = Config.load()
    if not config.discord_webhook:
        console.print("[red]No DISCORD_WEBHOOK_URL configured[/]")
        raise typer.Exit(1)

    from . import notifier

    async def send_test():
        success = await notifier.send("Test notification", level="info")
        if success:
            console.print("[green]Notification sent![/]")
        else:
            console.print("[red]Failed to send[/]")

    asyncio.run(send_test())


@app.command()
def health():
    """Run pre-flight health checks."""
    logger.setup()

    from .proxy import ProxyPool
    from .health import run_all_checks, print_results

    config = Config.load()
    pool = ProxyPool()
    pool.load(Path("data/proxies.txt"))

    async def run_checks():
        results = await run_all_checks(pool, config.discord_webhook)
        all_passed = print_results(results)
        if not all_passed:
            raise typer.Exit(1)

    asyncio.run(run_checks())


@app.command(name="test-proxies")
def test_proxies(
    proxies: Path = typer.Option(
        Path("data/proxies.txt"), "--proxies", "-p", help="Proxies file"
    ),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Timeout per proxy"),
):
    """Test all proxies and show results."""
    logger.setup()

    from .proxy import ProxyPool, warmup_proxies

    pool = ProxyPool()
    count = pool.load(proxies)

    if count == 0:
        console.print("[yellow]No proxies found in file[/]")
        raise typer.Exit(1)

    console.print(f"[blue]Testing {count} proxies...[/]\n")

    async def run_warmup():
        healthy = await warmup_proxies(pool)
        console.print(f"\n[green]Healthy:[/] {healthy}/{count}")

        stats = pool.stats()
        for name, s in stats.items():
            console.print(f"  {name}: {s['healthy']}/{s['total']} healthy")

    asyncio.run(run_warmup())


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
