from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from .client import GoGoClient, LoginResult
from .parser import extract_ticket_number, parse_csrf_token

LOGGER = logging.getLogger(__name__)


@dataclass
class BotResult:
    ok: bool
    ticket_number: Optional[str]
    ticket_id: Optional[str]
    message: str


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default) == "1"


def _within_ticket_window() -> bool:
    if _env_bool("GOGO_SKIP_WINDOW_CHECK", "0"):
        return True
    tz_name = os.getenv("TZ", "America/Los_Angeles")
    now = datetime.now(ZoneInfo(tz_name))
    if now.weekday() != 3:
        return False
    return 7 <= now.hour < 15


def _print_output(result: BotResult) -> None:
    if _env_bool("GOGO_OUTPUT_JSON", "0"):
        payload = {
            "ok": result.ok,
            "ticket_number": result.ticket_number,
            "ticket_id": result.ticket_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": result.message,
        }
        print(json.dumps(payload))
    else:
        if result.ok:
            print(f"Ticket assigned: {result.ticket_number}")
        else:
            print(f"Error: {result.message}")


def _handle_login_fallback(client: GoGoClient, result: LoginResult, last_name: str, case_number: str, csrf: str) -> LoginResult:
    if result.status not in {415, 416}:
        return result
    LOGGER.info("Attempting fallback login flow.")
    fallback = client.fallback_login("permit-login", last_name, case_number, csrf)
    if fallback.ok:
        return fallback
    return client.fallback_login("custom-login", last_name, case_number, csrf)


def run_bot() -> BotResult:
    if not _within_ticket_window():
        message = "Outside Thursday 07:00-15:00 PT window."
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message=message)
        _print_output(result)
        return result

    last_name = os.getenv("GOGO_LAST_NAME")
    case_number = os.getenv("GOGO_CASE_NUMBER")
    if not last_name or not case_number:
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message="Missing credentials.")
        _print_output(result)
        return result

    timeout = int(os.getenv("GOGO_TIMEOUT_SECONDS", "25"))
    user_agent = os.getenv(
        "GOGO_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    cookie_jar = os.getenv("GOGO_COOKIE_JAR")
    client = GoGoClient(timeout, user_agent, cookie_jar)

    LOGGER.info("Fetching homepage.")
    homepage = client.get_homepage()
    csrf = parse_csrf_token(homepage)
    if not csrf:
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message="CSRF token not found.")
        _print_output(result)
        return result

    LOGGER.info("Logging in.")
    login_result = client.login(last_name, case_number, csrf)
    login_result = _handle_login_fallback(client, login_result, last_name, case_number, csrf)
    if not login_result.ok:
        result = BotResult(
            ok=False,
            ticket_number=None,
            ticket_id=None,
            message=login_result.message or "Login failed.",
        )
        _print_output(result)
        return result

    LOGGER.info("Loading ticket options.")
    options = client.get_ticket_options()
    options_csrf = options.get("csrf_token") or csrf
    user_id = options.get("user_id")
    if not user_id:
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message="User ID not found.")
        _print_output(result)
        return result

    LOGGER.info("Requesting one ticket.")
    ticket_response = client.create_one_ticket(user_id, options_csrf)
    status = ticket_response.get("status")
    if status != 200:
        message = ticket_response.get("message") or f"Ticket request failed with status {status}."
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message=message)
        _print_output(result)
        return result

    ticket_id = ticket_response.get("ticket_id")
    if not ticket_id:
        result = BotResult(ok=False, ticket_number=None, ticket_id=None, message="Ticket ID missing.")
        _print_output(result)
        return result

    LOGGER.info("Fetching ticket details.")
    details_html = client.get_ticket_details(str(ticket_id))
    ticket_number = extract_ticket_number(details_html)
    if not ticket_number:
        result = BotResult(ok=False, ticket_number=None, ticket_id=str(ticket_id), message="Ticket number not found.")
        _print_output(result)
        return result

    result = BotResult(ok=True, ticket_number=ticket_number, ticket_id=str(ticket_id), message="Success.")
    _print_output(result)
    return result
