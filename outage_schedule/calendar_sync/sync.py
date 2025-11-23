from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from config import KYIV, KYIV_TZ, get_app_config
from models import AppConfig, IntervalDict

SCOPES = ["https://www.googleapis.com/auth/calendar"]

logger = logging.getLogger(__name__)


def _load_credentials(config: AppConfig) -> Credentials:
    creds: Credentials | None = None

    if os.path.exists(config.token_file):
        logger.info("Loading credentials from %s", config.token_file)
        creds = Credentials.from_authorized_user_file(config.token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            if not os.path.exists(config.credentials_file):
                raise FileNotFoundError(
                    f"Google credentials file '{config.credentials_file}' not found. "
                )
            logger.info("Running OAuth flow using %s", config.credentials_file)
            flow = InstalledAppFlow.from_client_secrets_file(config.credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(config.token_file, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def get_calendar_service(config: AppConfig) -> Resource:
    logger.info("Building Google Calendar service")
    creds = _load_credentials(config)
    return build("calendar", "v3", credentials=creds)


def get_or_create_calendar(service: Resource, calendar_name: str) -> str:
    logger.info("Looking up calendar '%s'", calendar_name)
    calendars = service.calendarList().list(showHidden=True).execute()
    for entry in calendars.get("items", []):
        if entry.get("summary") == calendar_name:
            logger.info("Found existing calendar id=%s", entry["id"])
            return entry["id"]

    body = {
        "summary": calendar_name,
        "timeZone": KYIV,
    }
    logger.info("Creating calendar '%s'", calendar_name)
    created = service.calendars().insert(body=body).execute()
    return created["id"]

def cleanup_events_today(
    service: Resource,
    calendar_id: str,
    *,
    day: dt.date | None = None,
) -> None:
    if day is None:
        day = dt.datetime.now(KYIV_TZ).date()

    start_of_day = dt.datetime.combine(day, dt.time.min, tzinfo=KYIV_TZ)
    end_of_day = start_of_day + dt.timedelta(days=1)

    time_min = start_of_day.isoformat()
    time_max = end_of_day.isoformat()

    deleted = 0
    page_token = None
    while True:
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )

        events = events_result.get("items", [])
        for event in events:
            service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            deleted += 1

        page_token = events_result.get("nextPageToken")
        if not page_token:
            break

    logger.info("Deleted %d events for %s", deleted, day.isoformat())

def calendar_sync_intervals(
    intervals: Iterable[IntervalDict],
    *,
    reminder_minutes: int,
) -> None:
    intervals = list(intervals)
    if not intervals:
        logger.info("No intervals to sync, skipping Google Calendar update")
        return

    logger.info(
        "Syncing %d intervals to Google Calendar (reminder %d min)",
        len(intervals),
        reminder_minutes,
    )
    config = get_app_config()
    service = get_calendar_service(config)
    calendar_id = get_or_create_calendar(service, config.calendar_name)

    today = dt.datetime.now(KYIV_TZ).date()

    cleanup_events_today(service, calendar_id, day=today)

    for item in intervals:
        start: dt.datetime = item["start"]
        end: dt.datetime = item["end"]
        itype = item.get("type", "OFF")
        summary = {
            "OFF": "Power OFF",
            "PROBABLY_OFF": "Power PROBABLY OFF",
        }.get(itype, "Power status")

        description = f"Queue outage type: {itype}"

        event_body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start.astimezone(KYIV_TZ).isoformat(),
                "timeZone": "Europe/Kyiv",
            },
            "end": {
                "dateTime": end.astimezone(KYIV_TZ).isoformat(),
                "timeZone": "Europe/Kyiv",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": reminder_minutes},
                ],
            },
        }

        service.events().insert(calendarId=calendar_id, body=event_body).execute()
        logger.info(
            "Created event %s %s - %s",
            summary,
            event_body["start"]["dateTime"],
            event_body["end"]["dateTime"],
        )