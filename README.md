# GoGo HTTP Ticket Bot

Python 3.11 bot that logs into https://www.thegiftofgroceries.com, selects **One Ticket**, and prints the ticket number for today using direct HTTP requests (no browser automation).

## Requirements

* Python 3.11
* `requests`, `beautifulsoup4`, `lxml`, `apscheduler`

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Required:

* `GOGO_LAST_NAME`
* `GOGO_CASE_NUMBER`

Optional:

* `TZ` (default: `America/Los_Angeles`)
* `GOGO_TIMEOUT_SECONDS` (default: `25`)
* `GOGO_USER_AGENT` (default: realistic desktop UA)
* `GOGO_VERBOSE` (`0/1`)
* `GOGO_OUTPUT_JSON` (`0/1`)
* `GOGO_DAEMON` (`0/1`) for schedule loop
* `GOGO_COOKIE_JAR` (path to JSON file for cookie persistence)
* `GOGO_SKIP_WINDOW_CHECK` (`1` to skip Thu 07:00–15:00 PT window check)

## Run Once

```bash
python -m gogo_bot.cli run-once
```

Expected output:

```
Ticket assigned: 1234
```

## Scheduler Options

### Cron Example

Run every Thursday at 7:00 AM America/Los_Angeles:

```
0 7 * * 4 TZ=America/Los_Angeles /usr/bin/env bash -lc "cd /path/to/repo && python -m gogo_bot.cli run-once"
```

Use the helper:

```bash
bash scripts/install_cron.sh
```

### In-App Scheduler (APScheduler)

```bash
python -m gogo_bot.cli daemon
```

The scheduler uses a cron trigger for Thursdays at 07:00 AM in the configured timezone.

## Troubleshooting

* **Login requires extra step**: The bot attempts `/permit-login` and `/custom-login` when `/login` returns a warning status.
* **Rate limited**: The bot retries up to 3 times with exponential backoff for HTTP 429.
* **Outside time window**: By default the bot will only run between 07:00–15:00 PT on Thursdays. Set `GOGO_SKIP_WINDOW_CHECK=1` to override.
* **Account disabled / queue**: The response message is printed and the program exits non-zero.

## Tests

```bash
pytest
```
