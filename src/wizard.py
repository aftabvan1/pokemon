"""Interactive setup wizard for first-time users ⚡."""
from __future__ import annotations

import asyncio
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .display import (
    console, success_box, error_box, warning_box, info_box,
    LIGHTNING, LIGHTNING_BOLT, BRAND_PRIMARY, BRAND_SECONDARY,
    BRAND_SUCCESS, BRAND_ERROR,
)

# ═══════════════════════════════════════════════════════════════════════════════
# WIZARD CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

WIZARD_HEADER = f"""
[bold {BRAND_PRIMARY}]{LIGHTNING} PORTER SETUP WIZARD {LIGHTNING}[/]
[dim]Let's get you up and running in no time![/]
"""

STEPS = [
    ("env", "Environment Configuration", True),      # (id, name, required)
    ("cookies", "Session Cookies", True),
    ("profiles", "Billing Profiles", True),
    ("tasks", "Purchase Tasks", True),
    ("proxies", "Proxy Configuration", False),
    ("discord", "Discord Notifications", False),
]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP CHECKING
# ═══════════════════════════════════════════════════════════════════════════════

def check_step_complete(step: str) -> bool:
    """Check if a setup step is already complete."""
    data_dir = Path("data")

    if step == "env":
        return Path(".env").exists()

    elif step == "cookies":
        cookies_path = data_dir / "cookies.json"
        if not cookies_path.exists():
            return False
        try:
            import json
            cookies = json.loads(cookies_path.read_text())
            return len(cookies) > 0
        except:
            return False

    elif step == "profiles":
        path = data_dir / "profiles.csv"
        if not path.exists():
            return False
        lines = path.read_text().strip().split('\n')
        return len(lines) > 1  # More than just header

    elif step == "tasks":
        path = data_dir / "tasks.csv"
        if not path.exists():
            return False
        lines = path.read_text().strip().split('\n')
        return len(lines) > 1

    elif step == "proxies":
        # Proxies are optional, so always "complete" if checked
        return True

    elif step == "discord":
        if not Path(".env").exists():
            return False
        content = Path(".env").read_text()
        for line in content.splitlines():
            if line.startswith("DISCORD_WEBHOOK_URL="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return bool(value)
        return False

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WIZARD
# ═══════════════════════════════════════════════════════════════════════════════

def run_setup_wizard() -> None:
    """Run the interactive setup wizard."""
    console.print()
    console.print(Panel(
        WIZARD_HEADER,
        border_style=BRAND_PRIMARY,
        padding=(1, 4),
    ))
    console.print()

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    # Show current progress
    console.print("[bold white]Setup Progress:[/]\n")

    incomplete_steps = []
    for step_id, step_name, required in STEPS:
        complete = check_step_complete(step_id)
        if complete:
            console.print(f"  [{BRAND_SUCCESS}]✓[/] {step_name}")
        else:
            status = "[dim](required)[/]" if required else "[dim](optional)[/]"
            console.print(f"  [{BRAND_ERROR}]○[/] {step_name} {status}")
            incomplete_steps.append((step_id, step_name, required))

    console.print()

    # Check if all required steps complete
    required_incomplete = [s for s in incomplete_steps if s[2]]
    if not required_incomplete:
        console.print(success_box(
            f"All required setup complete! {LIGHTNING}\n\n"
            "Run [bold]porter run[/] to start monitoring"
        ))
        return

    # Show remaining count
    console.print(f"[dim]{len(incomplete_steps)} steps remaining[/]")
    console.print()

    if not Confirm.ask(f"{LIGHTNING} Continue with setup?", default=True):
        return

    # Run each incomplete step
    for i, (step_id, step_name, required) in enumerate(incomplete_steps):
        console.print()
        console.print(f"[bold {BRAND_PRIMARY}]{'─' * 50}[/]")
        console.print(f"[bold {BRAND_PRIMARY}]{LIGHTNING}[/] [bold white]{step_name}[/]")
        console.print(f"[bold {BRAND_PRIMARY}]{'─' * 50}[/]")
        console.print()

        if step_id == "env":
            setup_env()
        elif step_id == "cookies":
            setup_cookies()
        elif step_id == "profiles":
            setup_profiles()
        elif step_id == "tasks":
            setup_tasks()
        elif step_id == "proxies":
            setup_proxies()
        elif step_id == "discord":
            setup_discord()

        # Check if user wants to continue (unless last step)
        if i < len(incomplete_steps) - 1:
            console.print()
            if not Confirm.ask("Continue to next step?", default=True):
                break

    # Final summary
    console.print()
    console.print(Panel(
        f"[bold {BRAND_SUCCESS}]{LIGHTNING} Setup complete! {LIGHTNING}[/]\n\n"
        "[bold white]Next steps:[/]\n"
        f"  [{BRAND_PRIMARY}]1.[/] Run [bold]porter validate[/] to check your config\n"
        f"  [{BRAND_PRIMARY}]2.[/] Run [bold]porter health[/] to test connectivity\n"
        f"  [{BRAND_PRIMARY}]3.[/] Run [bold]porter run --dry-run[/] to test without purchasing",
        title=f"{LIGHTNING_BOLT} [bold white]Ready to Go![/]",
        border_style=BRAND_SUCCESS,
        padding=(1, 2),
    ))


# ═══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL SETUP STEPS
# ═══════════════════════════════════════════════════════════════════════════════

def setup_env() -> None:
    """Create .env file with required variables."""
    env_path = Path(".env")

    if env_path.exists():
        console.print(info_box(".env file already exists"))
        if not Confirm.ask("Overwrite existing .env?", default=False):
            return

    console.print("Creating environment configuration...\n")

    # Prompt for values (optional)
    email = Prompt.ask("Pokemon Center email [dim](optional)[/]", default="")
    password = ""
    if email:
        password = Prompt.ask("Pokemon Center password [dim](optional)[/]", default="", password=True)

    env_content = f'''# Porter Configuration
# Generated by setup wizard

# Pokemon Center Credentials (optional - cookies are primary auth)
PC_EMAIL={email}
PC_PASSWORD={password}

# Discord Notifications (optional)
DISCORD_WEBHOOK_URL=

# Timing Configuration
MONITOR_INTERVAL=0.3
CHECKOUT_TIMEOUT=30
'''

    env_path.write_text(env_content)
    console.print()
    console.print(success_box("Created .env file"))


def setup_cookies() -> None:
    """Guide user through cookie capture."""
    console.print(Panel(
        "[bold]Cookie capture is required for authentication.[/]\n\n"
        "Two options:\n\n"
        f"  [{BRAND_PRIMARY}]A.[/] [bold]Manual export[/] (recommended)\n"
        "     1. Install Cookie-Editor extension in Chrome\n"
        "     2. Log in to pokemoncenter.com\n"
        "     3. Export cookies as JSON\n"
        "     4. Save to [cyan]data/cookies.json[/]\n\n"
        f"  [{BRAND_PRIMARY}]B.[/] [bold]Browser login[/] (may be blocked)\n"
        "     Run [cyan]porter login[/] to open browser\n"
        "     [dim]Note: Imperva may block automated browsers[/]",
        title=f"[bold {BRAND_SECONDARY}]Session Setup[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    ))

    choice = Prompt.ask(
        "\nChoose option",
        choices=["a", "b", "skip"],
        default="a"
    )

    if choice == "b":
        console.print()
        console.print(info_box("Opening browser for login..."))
        try:
            from .session import capture_session
            asyncio.run(capture_session())
        except Exception as e:
            console.print(error_box(f"Browser login failed: {e}\n\nTry manual export instead."))
    elif choice == "a":
        console.print()
        console.print(info_box(
            "Manual export steps:\n\n"
            "1. Open Chrome and go to pokemoncenter.com\n"
            "2. Log in to your account\n"
            "3. Click the Cookie-Editor extension\n"
            "4. Click Export → JSON\n"
            "5. Save to data/cookies.json"
        ))
        Prompt.ask("\n[dim]Press Enter when done[/]", default="")

        # Check if cookies were saved
        if Path("data/cookies.json").exists():
            console.print(success_box("Cookies file found!"))
        else:
            console.print(warning_box("Cookies file not found. You can add it later."))


def setup_profiles() -> None:
    """Guide user through profile creation."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    profiles_path = data_dir / "profiles.csv"

    if not profiles_path.exists() or profiles_path.read_text().strip().count('\n') == 0:
        # Create template with header
        profiles_path.write_text(
            "profile_name,email,first_name,last_name,address1,address2,"
            "city,state,zip,country,phone,card_number,card_exp,card_cvv\n"
        )
        console.print(success_box(f"Created {profiles_path}"))

    console.print(Panel(
        f"Edit [cyan]data/profiles.csv[/] to add your billing profiles.\n\n"
        "[bold]Required columns:[/]\n"
        "  profile_name, email, first_name, last_name,\n"
        "  address1, address2, city, state, zip, country,\n"
        "  phone, card_number, card_exp, card_cvv\n\n"
        "[bold]Example row:[/]\n"
        "  [dim]default,john@email.com,John,Doe,123 Main St,,Toronto,ON,M5V1A1,CA,4165551234,4111111111111111,12/26,123[/]\n\n"
        f"[{BRAND_WARNING}]⚠[/] [dim]Keep this file secure - it contains sensitive data[/]",
        title=f"[bold {BRAND_SECONDARY}]Profiles Setup[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    ))

    if Confirm.ask("\nCreate example profile?", default=True):
        # Add example row if only header exists
        content = profiles_path.read_text().strip()
        if content.count('\n') == 0:  # Only header
            profiles_path.write_text(
                content + "\n"
                "default,your@email.com,John,Doe,123 Main St,,Toronto,ON,M5V1A1,CA,4165551234,4111111111111111,12/26,123\n"
            )
            console.print(success_box("Added example profile (edit with your details)"))


def setup_tasks() -> None:
    """Guide user through task creation."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    tasks_path = data_dir / "tasks.csv"

    if not tasks_path.exists() or tasks_path.read_text().strip().count('\n') == 0:
        tasks_path.write_text("product_id,size,profile,proxy_group,priority\n")
        console.print(success_box(f"Created {tasks_path}"))

    console.print(Panel(
        f"Edit [cyan]data/tasks.csv[/] to add products to monitor.\n\n"
        "[bold]Columns:[/]\n"
        "  • product_id  - From product URL\n"
        "  • size        - ONE_SIZE, S, M, L, etc.\n"
        "  • profile     - Profile name from profiles.csv\n"
        "  • proxy_group - residential, datacenter, or default\n"
        "  • priority    - high, normal, or low\n\n"
        "[bold]Finding product IDs:[/]\n"
        f"  URL: pokemoncenter.com/product/[{BRAND_PRIMARY}]PRODUCT-ID[/]/name\n\n"
        "[bold]Example:[/]\n"
        "  [dim]pikachu-plush-123,ONE_SIZE,default,residential,high[/]",
        title=f"[bold {BRAND_SECONDARY}]Tasks Setup[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    ))

    if Confirm.ask("\nCreate example tasks?", default=True):
        content = tasks_path.read_text().strip()
        if content.count('\n') == 0:  # Only header
            tasks_path.write_text(
                content + "\n"
                "example-pikachu-plush,ONE_SIZE,default,residential,high\n"
                "example-charizard-figure,ONE_SIZE,default,datacenter,normal\n"
            )
            console.print(success_box("Added example tasks (edit with real product IDs)"))


def setup_proxies() -> None:
    """Guide user through proxy setup."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    proxies_path = data_dir / "proxies.txt"

    console.print(Panel(
        "[bold]Proxies are optional[/] but recommended for:\n"
        "  • Avoiding rate limits\n"
        "  • Multiple concurrent tasks\n"
        "  • IP rotation\n\n"
        "[bold]Format:[/] One proxy per line\n"
        f"  [{BRAND_PRIMARY}]http://user:pass@host:port[/]\n"
        f"  [{BRAND_PRIMARY}]socks5://user:pass@host:port[/]\n\n"
        "[bold]Proxy groups:[/]\n"
        "  Add [dim]# residential[/] or [dim]# datacenter[/] comments\n"
        "  to group proxies by type",
        title=f"[bold {BRAND_SECONDARY}]Proxy Setup[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    ))

    if not proxies_path.exists():
        if Confirm.ask("\nCreate proxies.txt template?", default=True):
            proxies_path.write_text(
                "# Porter Proxy List\n"
                "# Format: protocol://user:pass@host:port\n"
                "# Group with comments: # residential, # datacenter\n"
                "#\n"
                "# Example:\n"
                "# http://user:pass@proxy.example.com:8080\n"
            )
            console.print(success_box(f"Created {proxies_path}"))
    else:
        console.print(info_box(f"Proxies file exists at {proxies_path}"))


def setup_discord() -> None:
    """Guide user through Discord webhook setup."""
    console.print(Panel(
        "[bold]Discord notifications[/] alert you when:\n"
        f"  • {LIGHTNING} Stock is detected\n"
        "  • ✓ Order is placed\n"
        "  • ⚠ CAPTCHA needs solving\n"
        "  • ✗ Errors occur\n\n"
        "[bold]To get a webhook URL:[/]\n"
        f"  [{BRAND_PRIMARY}]1.[/] Open Discord server settings\n"
        f"  [{BRAND_PRIMARY}]2.[/] Go to Integrations → Webhooks\n"
        f"  [{BRAND_PRIMARY}]3.[/] Create new webhook\n"
        f"  [{BRAND_PRIMARY}]4.[/] Copy the URL",
        title=f"[bold {BRAND_SECONDARY}]Discord Setup[/]",
        border_style=BRAND_SECONDARY,
        padding=(1, 2),
    ))

    webhook = Prompt.ask("\nDiscord webhook URL [dim](or Enter to skip)[/]", default="")

    if webhook:
        env_path = Path(".env")
        if env_path.exists():
            content = env_path.read_text()
            if "DISCORD_WEBHOOK_URL=" in content:
                # Replace existing
                import re
                content = re.sub(
                    r'DISCORD_WEBHOOK_URL=.*',
                    f'DISCORD_WEBHOOK_URL={webhook}',
                    content
                )
            else:
                content += f"\nDISCORD_WEBHOOK_URL={webhook}\n"
            env_path.write_text(content)
        else:
            env_path.write_text(f"DISCORD_WEBHOOK_URL={webhook}\n")

        console.print(success_box("Saved Discord webhook"))

        # Offer to test
        if Confirm.ask("Send test notification?", default=True):
            from . import notifier

            async def test():
                success = await notifier.send(f"{LIGHTNING} Porter test notification!", level="info")
                if success:
                    console.print(success_box("Test notification sent!"))
                else:
                    console.print(error_box("Failed to send notification"))

            asyncio.run(test())
