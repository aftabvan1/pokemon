# Porter

Auto-purchase bot with multi-task support, proxy rotation, and CAPTCHA handling.

## Features

- **Fast HTTP/2** - Connection pooling and keep-alive for speed
- **Anti-detection** - Browser-accurate headers, request jitter, human-like timing
- **Multi-task** - Run multiple monitors concurrently from CSV
- **Proxy support** - Groups, rotation, sticky sessions per task
- **CAPTCHA handling** - Auto-detect, browser popup for manual solve
- **Discord notifications** - Alerts for stock, orders, errors
- **Live display** - Rich terminal UI with task status

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy environment template
cp .env.example .env
# Edit .env with your Discord webhook

# Capture session cookies
python -m src.main login

# Add your tasks and profiles to data/*.csv

# Validate setup
python -m src.main validate

# Run (dry-run first)
python -m src.main run --dry-run

# Run for real
python -m src.main run
```

## Configuration

### Environment Variables (.env)

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
MONITOR_INTERVAL=300    # ms between polls
CHECKOUT_TIMEOUT=30     # seconds
```

### Tasks (data/tasks.csv)

```csv
product_id,size,profile,proxy_group,priority
SKU-12345,M,default,residential,1
SKU-67890,L,default,datacenter,2
```

### Profiles (data/profiles.csv)

```csv
profile_name,email,first_name,last_name,address1,address2,city,state,zip,country,phone,card_number,card_exp,card_cvv
default,you@email.com,John,Doe,123 Main St,,City,CA,90210,US,5551234567,4111111111111111,12/25,123
```

### Proxies (data/proxies.txt)

```
http://user:pass@proxy1.example.com:8080
http://user:pass@proxy2.example.com:8080
```

## CLI Commands

```bash
# Run the bot
python -m src.main run [--tasks FILE] [--profiles FILE] [--dry-run] [--debug]

# Validate CSV files
python -m src.main validate

# Capture session via browser login
python -m src.main login

# Create empty CSV templates
python -m src.main templates

# Test Discord webhook
python -m src.main test-notify

# Run health checks
python -m src.main health

# Test proxies
python -m src.main test-proxies
```

## Endpoint Mapping

Before the bot works, you must map real API endpoints. See [docs/ENDPOINT_MAPPING.md](docs/ENDPOINT_MAPPING.md).

## Architecture

```
Monitor (poll) ──► Stock Found ──► Add to Cart ──► Checkout ──► Order
       │                               │              │
       └── Jitter ◄────────────────────┴── CAPTCHA? ──┘
                                              │
                                        Browser Popup
                                        (manual solve)
```

## Project Structure

```
src/
├── main.py          # CLI entry point
├── runner.py        # Task orchestration
├── monitor.py       # Stock polling
├── cart.py          # Add to cart
├── checkout.py      # Checkout flow
├── captcha.py       # CAPTCHA detection/solving
├── session.py       # Cookie/session management
├── proxy.py         # Proxy pool with groups
├── http_client.py   # HTTP/2 client with retries
├── headers.py       # Browser-accurate headers
├── timing.py        # Jitter and human delays
├── health.py        # Pre-flight checks
├── notifier.py      # Discord webhooks
├── display.py       # Rich terminal UI
├── tasks.py         # Task/profile management
├── endpoints.py     # API endpoint config
├── config.py        # Environment config
└── logger.py        # Logging setup
```

## License

Private - not for distribution.
