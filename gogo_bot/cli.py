from __future__ import annotations

import argparse
import sys

from .bot import run_bot
from .logging_conf import configure_logging
from .schedule import run_daemon


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GoGo HTTP Ticket Bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-once", help="Run the ticket bot once.")
    subparsers.add_parser("daemon", help="Run the ticket bot on schedule.")

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-once":
        result = run_bot()
        return 0 if result.ok else 1

    if args.command == "daemon":
        run_daemon()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
