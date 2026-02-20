"""CLI entry point using typer ⚡."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich import box

from . import logger
from .config import Config
from .display import (
    console, task_table, summary_panel, full_display,
    print_banner, print_banner_small, success_box, error_box, warning_box, info_box,
    LOGO_SMALL, TAGLINE, LIGHTNING_BOLT,
    show_interactive_menu, show_full_status, show_quick_guide,
)
from .tasks import TaskManager

__version__ = "0.1.0"


def version_callback(value: bool):
    if value:
        console.print()
        console.print(f"[bold #FFD700]◆[/] [bold white]PORTER[/] [dim]v{__version__}[/]")
        console.print(f"  [dim italic]Lightning-fast auto-purchase bot[/]")
        console.print()
        raise typer.Exit()


app = typer.Typer(
    name="porter",
    help="Porter - Lightning-fast auto-purchase bot ⚡",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,  # Show menu when no command given
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
):
    """[bold #FFD700]⚡[/] Porter - Lightning-fast auto-purchase bot"""
    # Show interactive menu if no command provided
    if ctx.invoked_subcommand is None:
        show_interactive_menu()


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

    # Print banner
    print_banner()

    config = Config.load()
    manager = TaskManager()

    try:
        manager.load_profiles(profiles)
        manager.load_tasks(tasks)
    except Exception as e:
        console.print(error_box(str(e), "Load Error"))
        raise typer.Exit(1)

    if not manager.tasks:
        console.print(error_box("No tasks loaded. Check your CSV files."))
        raise typer.Exit(1)

    # Show tasks
    console.print(task_table(manager.tasks))
    console.print()
    console.print(summary_panel(manager))

    if dry_run:
        console.print()
        console.print(info_box("Dry run mode — validated, not starting"))
        return

    from .runner import run_all
    from .proxy import ProxyPool

    pool = ProxyPool()
    pool.load(Path("data/proxies.txt"))

    console.print()
    console.print(f"[#FFD700]◆[/] Starting {len(manager.tasks)} tasks...")
    console.print()

    asyncio.run(run_all(manager, pool, config.monitor_interval))


@app.command()
def validate(
    tasks: Path = typer.Option(Path("data/tasks.csv"), "--tasks", "-t"),
    profiles: Path = typer.Option(Path("data/profiles.csv"), "--profiles", "-p"),
):
    """Validate CSV files without running."""
    logger.setup()

    print_banner_small()

    manager = TaskManager()

    try:
        manager.load_profiles(profiles)
        manager.load_tasks(tasks)
    except Exception as e:
        console.print(error_box(str(e)))
        raise typer.Exit(1)

    # Summary table
    from rich.table import Table

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Item", style="dim")
    table.add_column("Count", style="bold white")
    table.add_column("")

    table.add_row(
        "Profiles",
        str(len(manager.profiles)),
        "[#00D26A]✓[/]" if manager.profiles else "[#FF3B3B]✗[/]"
    )
    table.add_row(
        "Tasks",
        str(len(manager.tasks)),
        "[#00D26A]✓[/]" if manager.tasks else "[#FF3B3B]✗[/]"
    )

    console.print(Panel(table, title="[bold #FFD700]◆[/] [bold white]Validation[/]", border_style="#3B4CCA"))
    console.print()

    if manager.tasks:
        console.print(task_table(manager.tasks))


@app.command()
def login():
    """Capture session cookies via browser login."""
    logger.setup()

    print_banner_small()
    console.print(info_box("Opening browser for manual login..."))

    from .session import capture_session
    asyncio.run(capture_session())


@app.command()
def templates():
    """Create empty CSV template files."""
    print_banner_small()

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    tasks_csv = data_dir / "tasks.csv"
    profiles_csv = data_dir / "profiles.csv"

    created = []

    if not tasks_csv.exists():
        tasks_csv.write_text(
            "product_id,size,profile,proxy_group,priority\n"
            "test-pikachu-plush,ONE_SIZE,default,residential,high\n"
            "test-charizard-figure,ONE_SIZE,default,datacenter,normal\n"
        )
        created.append(f"  [dim]•[/] {tasks_csv}")

    if not profiles_csv.exists():
        profiles_csv.write_text(
            "profile_name,email,first_name,last_name,address1,address2,"
            "city,state,zip,country,phone,card_number,card_exp,card_cvv\n"
            "default,test@example.com,John,Doe,123 Main St,,New York,NY,10001,US,5551234567,4111111111111111,12/26,123\n"
        )
        created.append(f"  [dim]•[/] {profiles_csv}")

    if created:
        console.print(success_box("Template files created:\n" + "\n".join(created)))
    else:
        console.print(info_box("Template files already exist"))


@app.command()
def test_notify():
    """Send a test Discord notification."""
    logger.setup()

    print_banner_small()

    config = Config.load()
    if not config.discord_webhook:
        console.print(error_box("No DISCORD_WEBHOOK_URL configured in .env"))
        raise typer.Exit(1)

    from . import notifier

    async def send_test():
        console.print(info_box("Sending test notification..."))
        success = await notifier.send("Test notification from Porter", level="info")
        if success:
            console.print(success_box("Notification sent!"))
        else:
            console.print(error_box("Failed to send notification"))

    asyncio.run(send_test())


@app.command()
def health():
    """Run pre-flight health checks."""
    logger.setup()

    print_banner_small()

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


@app.command(name="check-cookies")
def check_cookies(
    cookies: Path = typer.Option(
        Path("data/cookies.json"), "--cookies", "-c", help="Cookies JSON file"
    ),
):
    """Validate exported cookies and show status."""
    logger.setup()

    print_banner_small()

    from .session import load_session, validate_required_cookies
    from .endpoints import REQUIRED_COOKIES
    from rich.table import Table
    import json

    if not cookies.exists():
        console.print(error_box(f"No cookies file at {cookies}"))
        console.print()
        console.print(Panel(
            "[dim]To export cookies manually:[/]\n\n"
            "  [#FFD700]1.[/] Install [bold]Cookie-Editor[/] extension in Chrome\n"
            "  [#FFD700]2.[/] Go to pokemoncenter.com and log in\n"
            "  [#FFD700]3.[/] Click extension → [bold]Export → JSON[/]\n"
            f"  [#FFD700]4.[/] Save to [cyan]{cookies}[/]",
            title="[bold #3B4CCA]Setup Guide[/]",
            border_style="#3B4CCA",
            padding=(1, 2),
        ))
        raise typer.Exit(1)

    try:
        raw_cookies = json.loads(cookies.read_text())
        session = load_session(cookies)

        # Build status table
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Status", width=3)
        table.add_column("Cookie", style="white")

        # Check auth
        if session.auth_token:
            table.add_row("[#00D26A]✓[/]", "[bold]Auth token[/] [dim]— logged in[/]")
        else:
            table.add_row("[#FF3B3B]✗[/]", "[bold]Auth token[/] [dim]— not logged in[/]")

        # Check bot protection cookies
        missing = validate_required_cookies(raw_cookies)
        present_cookies = {c.get("name") for c in raw_cookies}

        for cookie_name in REQUIRED_COOKIES:
            if cookie_name.endswith("*"):
                prefix = cookie_name[:-1]
                found = any(n.startswith(prefix) for n in present_cookies)
            else:
                found = cookie_name in present_cookies

            if found:
                table.add_row("[#00D26A]✓[/]", cookie_name)
            else:
                table.add_row("[#FF3B3B]✗[/]", f"[dim]{cookie_name}[/]")

        console.print(Panel(
            table,
            title="[bold #FFD700]◆[/] [bold white]Cookie Status[/]",
            border_style="#3B4CCA",
            subtitle=f"[dim]{len(raw_cookies)} cookies total[/]",
        ))

        console.print()
        if missing:
            console.print(warning_box(f"Missing {len(missing)} required cookies. Bot protection may fail."))
        else:
            console.print(success_box("All required cookies present!"))

    except json.JSONDecodeError as e:
        console.print(error_box(f"Invalid JSON: {e}"))
        raise typer.Exit(1)
    except Exception as e:
        console.print(error_box(str(e)))
        raise typer.Exit(1)


@app.command(name="test-proxies")
def test_proxies(
    proxies: Path = typer.Option(
        Path("data/proxies.txt"), "--proxies", "-p", help="Proxies file"
    ),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Timeout per proxy"),
):
    """Test all proxies and show results."""
    logger.setup()

    print_banner_small()

    from .proxy import ProxyPool, warmup_proxies

    pool = ProxyPool()
    count = pool.load(proxies)

    if count == 0:
        console.print(warning_box("No proxies found in file"))
        raise typer.Exit(1)

    console.print(info_box(f"Testing {count} proxies..."))
    console.print()

    async def run_warmup():
        healthy = await warmup_proxies(pool)

        if healthy == count:
            console.print(success_box(f"All {count} proxies healthy!"))
        elif healthy > 0:
            console.print(warning_box(f"{healthy}/{count} proxies healthy"))
        else:
            console.print(error_box("No healthy proxies found"))

        stats = pool.stats()
        for name, s in stats.items():
            console.print(f"  [dim]•[/] {name}: {s['healthy']}/{s['total']} healthy")

    asyncio.run(run_warmup())


@app.command(name="add-task")
def add_task(
    url: Optional[str] = typer.Argument(None, help="Pokemon Center product URL"),
):
    """Add a new task interactively or from a URL."""
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    import csv
    import re

    print_banner_small()

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    tasks_path = data_dir / "tasks.csv"
    profiles_path = data_dir / "profiles.csv"

    # Load existing profiles
    profiles = []
    if profiles_path.exists():
        with open(profiles_path) as f:
            reader = csv.DictReader(f)
            profiles = [row["profile_name"] for row in reader]

    if not profiles:
        console.print(error_box("No profiles found. Run [bold]porter setup[/] first."))
        raise typer.Exit(1)

    # Get URL or prompt for it
    if not url:
        console.print(info_box(
            "Paste a Pokemon Center product URL\n\n"
            "[dim]Example: pokemoncenter.com/en-ca/product/[cyan]100-10341[/]/product-name[/]"
        ))
        console.print()
        url = Prompt.ask("Product URL")

    # Extract human-readable product ID from URL
    match = re.search(r'/product/([^/]+)', url)
    if match:
        human_id = match.group(1)
        console.print(f"  {LIGHTNING_BOLT} Product: [bold cyan]{human_id}[/]")
    else:
        console.print(error_box("Could not parse product ID from URL"))
        raise typer.Exit(1)

    # Fetch the encoded product ID from the page
    console.print(f"  {LIGHTNING_BOLT} Fetching product data...")

    async def fetch_encoded_id():
        from .product import get_encoded_product_id
        from .session import load_session
        from .http_client import HTTPClient

        try:
            session = load_session()
        except FileNotFoundError:
            return None, "No session cookies. Run 'porter login' first."

        async with HTTPClient(
            cookies=session.cookies,
            auth_token=session.auth_token,
        ) as client:
            encoded_id = await get_encoded_product_id(client, human_id)
            return encoded_id, None

    encoded_id, error = asyncio.run(fetch_encoded_id())

    if error:
        console.print(error_box(error))
        raise typer.Exit(1)

    if encoded_id:
        console.print(f"  {LIGHTNING_BOLT} Encoded ID: [bold green]{encoded_id[:25]}...[/]")
        product_id = encoded_id
    else:
        console.print(warning_box(
            "Could not auto-detect encoded ID.\n"
            "The bot may not work correctly without it.\n\n"
            "[dim]Tip: Find the encoded ID in Chrome DevTools when adding to cart[/]"
        ))
        use_human = Confirm.ask("Use human-readable ID anyway?", default=False)
        if use_human:
            product_id = human_id
        else:
            product_id = Prompt.ask("Enter encoded ID manually")

    console.print()

    # Size selection
    console.print("[bold white]Select size:[/]")
    sizes = ["ONE_SIZE", "S", "M", "L", "XL", "XXL", "Other"]
    for i, size in enumerate(sizes, 1):
        console.print(f"  [#FFD700]{i}[/]  {size}")

    size_choice = Prompt.ask("Choice", default="1")
    try:
        size_idx = int(size_choice) - 1
        if 0 <= size_idx < len(sizes) - 1:
            size = sizes[size_idx]
        else:
            size = Prompt.ask("Enter size")
    except ValueError:
        size = size_choice.upper()

    console.print()

    # Profile selection
    if len(profiles) == 1:
        profile = profiles[0]
        console.print(f"  {LIGHTNING_BOLT} Using profile: [bold cyan]{profile}[/]")
    else:
        console.print("[bold white]Select profile:[/]")
        for i, p in enumerate(profiles, 1):
            console.print(f"  [#FFD700]{i}[/]  {p}")
        profile_choice = Prompt.ask("Choice", default="1")
        try:
            profile = profiles[int(profile_choice) - 1]
        except (ValueError, IndexError):
            profile = profiles[0]

    console.print()

    # Priority
    console.print("[bold white]Priority:[/]")
    console.print(f"  [#FFD700]1[/]  high [dim](for limited drops)[/]")
    console.print(f"  [#FFD700]2[/]  normal")
    console.print(f"  [#FFD700]3[/]  low")
    priority_choice = Prompt.ask("Choice", default="1")
    priority_map = {"1": "high", "2": "normal", "3": "low"}
    priority = priority_map.get(priority_choice, "high")

    # Proxy group (default to residential for safety)
    proxy_group = "residential"

    # Show summary
    console.print()
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold white")
    table.add_row("Product", product_id)
    table.add_row("Size", size)
    table.add_row("Profile", profile)
    table.add_row("Priority", priority)

    console.print(Panel(table, title=f"{LIGHTNING_BOLT} [bold white]New Task[/]", border_style="#3B4CCA"))

    if not Confirm.ask("\nAdd this task?", default=True):
        console.print("[dim]Cancelled[/]")
        return

    # Add to CSV
    file_exists = tasks_path.exists() and tasks_path.stat().st_size > 0

    with open(tasks_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["product_id", "size", "profile", "proxy_group", "priority"])
        writer.writerow([product_id, size, profile, proxy_group, priority])

    console.print()
    console.print(success_box(f"Task added! You now have tasks ready to run."))
    console.print()
    console.print(f"  [dim]Run[/] [bold]porter run[/] [dim]to start monitoring[/]")
    console.print()


@app.command(name="list-tasks")
def list_tasks():
    """Show all configured tasks."""
    import csv

    print_banner_small()

    tasks_path = Path("data/tasks.csv")
    if not tasks_path.exists():
        console.print(warning_box("No tasks file found. Run [bold]porter add-task[/] to create one."))
        return

    with open(tasks_path) as f:
        reader = csv.DictReader(f)
        tasks_list = list(reader)

    if not tasks_list:
        console.print(warning_box("No tasks configured. Run [bold]porter add-task[/] to add one."))
        return

    from rich.table import Table

    table = Table(
        title=f"{LIGHTNING_BOLT} [bold white]Tasks[/]",
        border_style="#3B4CCA",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Product ID", style="cyan")
    table.add_column("Size", justify="center")
    table.add_column("Profile", style="dim")
    table.add_column("Priority", justify="center")

    for i, task in enumerate(tasks_list, 1):
        priority_style = {"high": "bold #FFD700", "normal": "white", "low": "dim"}.get(task.get("priority", "normal"), "white")
        table.add_row(
            str(i),
            task.get("product_id", "")[:40],
            task.get("size", ""),
            task.get("profile", ""),
            f"[{priority_style}]{task.get('priority', 'normal')}[/]"
        )

    console.print(table)
    console.print()
    console.print(f"  [dim]Run[/] [bold]porter run[/] [dim]to start monitoring[/]")
    console.print()


@app.command(name="clear-tasks")
def clear_tasks():
    """Clear all tasks."""
    from rich.prompt import Confirm

    print_banner_small()

    tasks_path = Path("data/tasks.csv")
    if not tasks_path.exists():
        console.print(info_box("No tasks file exists."))
        return

    if Confirm.ask(f"{LIGHTNING_BOLT} Clear all tasks?", default=False):
        tasks_path.write_text("product_id,size,profile,proxy_group,priority\n")
        console.print(success_box("All tasks cleared."))
    else:
        console.print("[dim]Cancelled[/]")


@app.command()
def setup():
    """Run the interactive setup wizard."""
    from .wizard import run_setup_wizard
    run_setup_wizard()


@app.command()
def init():
    """Run the interactive setup wizard (alias for setup)."""
    from .wizard import run_setup_wizard
    run_setup_wizard()


@app.command()
def status():
    """Show full configuration status dashboard."""
    show_full_status()


@app.command()
def guide():
    """Show quick start tutorial."""
    show_quick_guide()


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
