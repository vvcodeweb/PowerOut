from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from utils.models import AppConfig

API_BASE_URL = "https://off.energy.mk.ua/api"
KYIV = "Europe/Kyiv"
KYIV_TZ = ZoneInfo(KYIV)

_DEFAULT_QUEUE_TYPE_ID = 3
_DEFAULT_QUEUE_NAME = "1.1"
_DEFAULT_REMINDER_MINUTES = 15
_DEFAULT_CREDENTIALS_FILE = "calendar_sync/credentials.json"
_DEFAULT_TOKEN_FILE = "calendar_sync/token.json"
_DEFAULT_CALENDAR_NAME = "Power Outages"


def _int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw!r}") from exc


def get_app_config() -> AppConfig:
    return AppConfig(
        base_url=os.getenv("API_BASE_URL", API_BASE_URL),
        queue_name=os.getenv("QUEUE_NAME", _DEFAULT_QUEUE_NAME),
        queue_type_id=_int_from_env("QUEUE_TYPE_ID", _DEFAULT_QUEUE_TYPE_ID),
        reminder_minutes=_int_from_env("REMINDER_MINUTES", _DEFAULT_REMINDER_MINUTES),
        credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", _DEFAULT_CREDENTIALS_FILE),
        token_file=os.getenv("GOOGLE_TOKEN_FILE", _DEFAULT_TOKEN_FILE),
        calendar_name=os.getenv("CALENDAR_NAME", _DEFAULT_CALENDAR_NAME),
    )
