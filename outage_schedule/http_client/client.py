from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

import requests

logger = logging.getLogger(__name__)

_USER_AGENT_FILE = Path(__file__).with_name("user-agents.txt")

_FALLBACK_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.127 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
)


@dataclass(frozen=True)
class Fingerprint:
    label: str
    headers: Mapping[str, str]
    keywords: tuple[str, ...] = ()


_FINGERPRINTS: tuple[Fingerprint, ...] = (
    Fingerprint(
        label="chrome",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://off.energy.mk.ua/",
        },
        keywords=("Chrome", "Chromium"),
    ),
    Fingerprint(
        label="firefox",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://off.energy.mk.ua/",
        },
        keywords=("Firefox", "Gecko"),
    ),
    Fingerprint(
        label="safari-ios",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://off.energy.mk.ua/",
        },
        keywords=("iPhone", "Safari"),
    ),
)


@lru_cache(maxsize=1)
def _count_user_agents() -> int:
    try:
        with _USER_AGENT_FILE.open("r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    except FileNotFoundError:
        logger.warning("User-agent file %s missing, falling back to built-in list", _USER_AGENT_FILE)
        return 0


def _read_line(line_number: int) -> str | None:
    with _USER_AGENT_FILE.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh, start=1):
            if idx == line_number:
                return line.strip()
    return None


def _pick_user_agent(rng: random.Random, keywords: Sequence[str]) -> str:
    total = _count_user_agents()
    if total <= 0:
        return rng.choice(_FALLBACK_USER_AGENTS)

    for _ in range(10):
        idx = rng.randint(1, total)
        candidate = _read_line(idx)
        if not candidate or not candidate.strip() or candidate.startswith("#"):
            continue
        if keywords and not any(keyword in candidate for keyword in keywords):
            continue
        return candidate

    return rng.choice(_FALLBACK_USER_AGENTS)


def build_browser_session(seed: int | None = None) -> requests.Session:
    rng = random.Random(seed)
    profile = rng.choice(_FINGERPRINTS)
    headers = dict(profile.headers)
    headers["User-Agent"] = _pick_user_agent(rng, profile.keywords)
    session = requests.Session()
    session.headers.update(headers)
    logger.info("Selected HTTP fingerprint: %s", profile.label)
    return session
