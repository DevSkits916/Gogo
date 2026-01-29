from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Dict, Optional

import requests
from requests.cookies import RequestsCookieJar

from .parser import extract_user_id, parse_csrf_token

LOGGER = logging.getLogger(__name__)


@dataclass
class LoginResult:
    ok: bool
    status: Optional[int] = None
    redirect: Optional[str] = None
    message: Optional[str] = None


class GoGoClient:
    BASE_URL = "https://www.thegiftofgroceries.com"

    def __init__(self, timeout_seconds: int, user_agent: str, cookie_jar_path: Optional[str]) -> None:
        self.timeout = (timeout_seconds, timeout_seconds)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.cookie_jar_path = cookie_jar_path
        if cookie_jar_path:
            jar = RequestsCookieJar()
            self.session.cookies = jar

    def _save_cookies(self) -> None:
        if not self.cookie_jar_path:
            return
        with open(self.cookie_jar_path, "w", encoding="utf-8") as handle:
            json.dump(self.session.cookies.get_dict(), handle)

    def _load_cookies(self) -> None:
        if not self.cookie_jar_path or not os.path.exists(self.cookie_jar_path):
            return
        try:
            with open(self.cookie_jar_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                self.session.cookies.update(data)
        except json.JSONDecodeError:
            LOGGER.warning("Cookie jar is not valid JSON, ignoring.")

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        data: Any = None,
        json_body: Any = None,
        allow_retry: bool = False,
    ) -> requests.Response:
        attempts = 0
        delay = 1.0
        while True:
            attempts += 1
            LOGGER.debug("Request %s %s attempt %s", method, url, attempts)
            response = self.session.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json_body,
                timeout=self.timeout,
            )
            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS or not allow_retry or attempts >= 3:
                return response

            LOGGER.warning("Rate limited. Retrying in %.1fs", delay)
            time.sleep(delay)
            delay = min(delay * 2, 20)

    def get_homepage(self) -> str:
        self._load_cookies()
        response = self._request("GET", f"{self.BASE_URL}/")
        response.raise_for_status()
        return response.text

    def login(self, last_name: str, case_number: str, csrf_token: str) -> LoginResult:
        url = f"{self.BASE_URL}/login"
        payload = {
            "last_name": last_name,
            "case_number": case_number,
            "confirm_case_number": "",
            "_token": csrf_token,
        }
        headers = {
            "Referer": f"{self.BASE_URL}/",
            "Origin": self.BASE_URL,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }
        response = self._request("POST", url, headers=headers, data=payload, allow_retry=True)
        try:
            data = response.json()
        except ValueError:
            LOGGER.error("Login response was not JSON.")
            return LoginResult(ok=False, status=response.status_code, message="Login response invalid.")

        status = data.get("status")
        message = data.get("message")
        LOGGER.debug("Login response status=%s message=%s", status, message)

        if status in {201, 200, 204, 203}:
            self._save_cookies()
            return LoginResult(ok=True, status=status, redirect=data.get("redirect"))

        if status in {415, 416}:
            return LoginResult(ok=False, status=status, message=message or "Login requires extra step.")

        if status == 405:
            return LoginResult(ok=False, status=status, message=message or "Validation errors.")

        if status in {410, 417, 418, 420, 421}:
            return LoginResult(ok=False, status=status, message=message or "Login unavailable.")

        return LoginResult(ok=False, status=status, message=message or "Login failed.")

    def fallback_login(self, endpoint: str, last_name: str, case_number: str, csrf_token: str) -> LoginResult:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        if endpoint.endswith("custom-login"):
            form_data = {
                "last_name": last_name,
                "case_number": case_number,
                "_token": csrf_token,
            }
            response = self._request("POST", url, data=form_data, allow_retry=True)
        else:
            payload = {
                "last_name": last_name,
                "case_number": case_number,
                "confirm_case_number": "",
                "_token": csrf_token,
            }
            response = self._request("POST", url, data=payload, allow_retry=True)

        try:
            data = response.json()
        except ValueError:
            return LoginResult(ok=False, status=response.status_code, message="Fallback login invalid response.")

        status = data.get("status")
        if status in {201, 200, 204, 203}:
            self._save_cookies()
            return LoginResult(ok=True, status=status, redirect=data.get("redirect"))
        return LoginResult(ok=False, status=status, message=data.get("message"))

    def get_ticket_options(self) -> Dict[str, Optional[str]]:
        url = f"{self.BASE_URL}/user/get-ticket-options"
        response = self._request("GET", url)
        response.raise_for_status()
        html = response.text
        return {
            "csrf_token": parse_csrf_token(html),
            "user_id": extract_user_id(html),
            "html": html,
        }

    def create_one_ticket(self, user_id: str, csrf_token: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/manage-tickets-generation"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/user/get-ticket-options",
        }
        payload = {"submission_type": 0, "userId": user_id, "_token": csrf_token}
        response = self._request(
            "POST",
            url,
            headers=headers,
            json_body=payload,
            allow_retry=True,
        )
        try:
            data = response.json()
        except ValueError:
            return {"status": response.status_code, "message": "Ticket creation response invalid."}
        return data

    def get_ticket_details(self, ticket_id: str) -> str:
        url = f"{self.BASE_URL}/one-ticket-details/{ticket_id}"
        response = self._request("GET", url)
        response.raise_for_status()
        return response.text
