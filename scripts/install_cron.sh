#!/usr/bin/env bash
set -euo pipefail

CRON_LINE='0 7 * * 4 TZ=America/Los_Angeles /usr/bin/env bash -lc "cd /path/to/repo && python -m gogo_bot.cli run-once"'

echo "Cron entry to add:"
echo "${CRON_LINE}"
echo
echo "To install, run:"
echo "(crontab -l 2>/dev/null; echo \"${CRON_LINE}\") | crontab -"
