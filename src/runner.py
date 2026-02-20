"""Multi-task runner with live display and error isolation."""
from __future__ import annotations

import asyncio
import signal
from typing import Optional

from rich.live import Live
from rich.console import Group

from . import logger
from .tasks import TaskManager, Task, State
from .proxy import ProxyPool
from .session import SessionManager, load_cookies
from .http_client import HTTPClient
from .monitor import check_stock
from .cart import add_to_cart, CartError
from .checkout import run_checkout, CheckoutError
from .captcha import detect as detect_captcha, solve_manually
from .display import console, task_table, summary_panel
from .timing import monitor_interval
from . import notifier

log = logger.get("RUNNER")


class GracefulShutdown:
    """Handle graceful shutdown on Ctrl+C."""

    def __init__(self):
        self.requested = False

    def request(self):
        if self.requested:
            log.warning("Force quitting...")
            raise SystemExit(1)
        log.info("Shutdown requested, finishing current tasks...")
        self.requested = True


shutdown = GracefulShutdown()


async def run_task(
    task: Task,
    client: HTTPClient,
    proxy_pool: ProxyPool,
    interval_ms: float,
) -> None:
    """
    Run single task through full purchase flow.

    Isolated error handling - failures don't affect other tasks.
    """
    task_log = logger.get(task.id)

    try:
        # === MONITORING PHASE ===
        task.state = State.MONITORING

        while task.state == State.MONITORING and not shutdown.requested:
            task.polls += 1

            try:
                result = await check_stock(client, task.product_id)

                if result["in_stock"]:
                    task_log.success(f"Stock found ({task.polls} polls)")
                    await notifier.stock_found(task.product_id)
                    task.state = State.CARTED
                    break

                # Log progress periodically
                if task.polls % 100 == 0:
                    task_log.debug(f"Poll #{task.polls}")

            except Exception as e:
                task_log.warning(f"Poll error: {e}")

            await monitor_interval(interval_ms)

        if shutdown.requested:
            task.state = State.FAILED
            task.error = "Shutdown"
            return

        # === CART PHASE ===
        if task.state == State.CARTED:
            try:
                cart_data = await add_to_cart(client, task.product_id, task.size)
                task.state = State.CHECKOUT

            except CartError as e:
                if "CAPTCHA" in str(e):
                    task.state = State.CAPTCHA
                    task_log.warning("CAPTCHA required for cart")

                    # Try to solve
                    token = await solve_manually(client.client.base_url)
                    if token:
                        # Retry cart with new token
                        try:
                            await add_to_cart(client, task.product_id, task.size)
                            task.state = State.CHECKOUT
                        except Exception as retry_e:
                            task.state = State.FAILED
                            task.error = str(retry_e)[:50]
                            return
                    else:
                        task.state = State.FAILED
                        task.error = "CAPTCHA timeout"
                        return
                else:
                    task.state = State.FAILED
                    task.error = str(e)[:50]
                    return

        # === CHECKOUT PHASE ===
        if task.state == State.CHECKOUT:
            try:
                order_id = await run_checkout(client, task.profile)
                task.state = State.SUCCESS
                task.order_id = order_id
                task_log.success(f"Order placed: {order_id}")
                await notifier.order_placed(order_id)

            except CheckoutError as e:
                if "CAPTCHA" in e.message:
                    task.state = State.CAPTCHA
                    task_log.warning(f"CAPTCHA at {e.step}")

                    token = await solve_manually(client.client.base_url)
                    if token:
                        # Retry checkout
                        try:
                            order_id = await run_checkout(client, task.profile, skip_init=True)
                            task.state = State.SUCCESS
                            task.order_id = order_id
                            await notifier.order_placed(order_id)
                        except Exception as retry_e:
                            task.state = State.FAILED
                            task.error = str(retry_e)[:50]
                            await notifier.error(str(retry_e))
                    else:
                        task.state = State.FAILED
                        task.error = "CAPTCHA timeout"
                else:
                    task.state = State.FAILED
                    task.error = f"{e.step}: {e.message}"[:50]
                    await notifier.error(str(e))

    except Exception as e:
        # Catch-all for unexpected errors
        task_log.error(f"Unexpected error: {e}")
        task.state = State.FAILED
        task.error = str(e)[:50]

    finally:
        # Release sticky proxy
        proxy_pool.release_sticky(task.id)


async def run_all(
    manager: TaskManager,
    proxy_pool: ProxyPool,
    interval_ms: float,
) -> dict:
    """
    Run all tasks concurrently with live display.

    Returns:
        Summary dict with success/failed counts
    """
    # Load session
    try:
        cookies = load_cookies()
    except FileNotFoundError:
        log.error("No session cookies. Run 'login' first.")
        return {"success": 0, "failed": len(manager.tasks)}

    # Setup signal handlers
    def handle_signal(signum, frame):
        shutdown.request()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Get proxy (sticky per task will be handled in run_task)
    proxy_url = proxy_pool.get()

    # Create shared client
    async with HTTPClient(cookies=cookies, proxy=proxy_url) as client:
        tasks = manager.sorted_by_priority()

        async def update_display(live: Live):
            """Update display while tasks running."""
            while any(t.state not in [State.SUCCESS, State.FAILED] for t in tasks):
                live.update(Group(task_table(tasks), summary_panel(manager)))
                await asyncio.sleep(0.25)

        # Run with live display
        with Live(console=console, refresh_per_second=4) as live:
            await asyncio.gather(
                *[run_task(t, client, proxy_pool, interval_ms) for t in tasks],
                update_display(live),
                return_exceptions=True,  # Don't let one failure kill others
            )

    # Final display
    console.print()
    console.print(task_table(manager.tasks))
    console.print(summary_panel(manager))

    # Summary
    s = manager.summary()
    log.info(f"Complete: {s['success']} success, {s['failed']} failed")

    return s
