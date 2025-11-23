from dataclasses import dataclass
import datetime
from typing import TypedDict


@dataclass(frozen=True)
class AppConfig:
    base_url: str
    queue_name: str
    queue_type_id: int
    reminder_minutes: int
    credentials_file: str
    token_file: str
    calendar_name: str
    
class IntervalDict(TypedDict):
    start: datetime
    end: datetime
    type: str
