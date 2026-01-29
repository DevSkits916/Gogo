from __future__ import annotations

import re
from typing import Iterable, Optional

from bs4 import BeautifulSoup


def parse_csrf_token(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    if not meta:
        return None
    return meta.get("content")


def extract_user_id(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    button = soup.find(class_="one-ticket-modal-continue-btn")
    if not button:
        return None
    return button.get("user-id")


def _candidate_numbers(text: str) -> Iterable[tuple[int, str]]:
    for match in re.finditer(r"\b(\d{1,5})\b", text):
        yield match.start(), match.group(1)


def _closest_candidate(text: str, anchors: Iterable[str]) -> Optional[str]:
    lower = text.lower()
    anchor_positions = [lower.find(anchor) for anchor in anchors if lower.find(anchor) != -1]
    if not anchor_positions:
        return None

    best = None
    best_distance = None
    for position, number in _candidate_numbers(text):
        distance = min(abs(position - anchor) for anchor in anchor_positions)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best = number
    return best


def extract_ticket_number(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    anchors = ["ticket number", "ticket #", "your ticket", "ticket"]

    candidate = _closest_candidate(text, anchors)
    if candidate:
        return candidate

    labeled = soup.find(string=re.compile(r"ticket\s*(number|#|no\.?)", re.I))
    if labeled:
        parent_text = labeled.parent.get_text(" ", strip=True)
        candidate = _closest_candidate(parent_text, anchors)
        if candidate:
            return candidate

    return None
