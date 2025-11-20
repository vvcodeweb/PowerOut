from __future__ import annotations

import logging
import time
from datetime import datetime
from calendar_sync.sync import calendar_sync_intervals
from config import KYIV_TZ, get_app_config
from http_client.client import build_browser_session
from models import AppConfig, IntervalDict
from power_api import PowerOutageAPI
from utils import merge_adjacent_intervals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config: AppConfig = get_app_config()
    session = build_browser_session()
    api = PowerOutageAPI(config.base_url, session)

    logger.info(
        "Starting sync for queue %s (type %s) with %s-minute reminders",
        config.queue_name,
        config.queue_type_id,
        config.reminder_minutes,
    )

    queues = api.fetch_queues(config.queue_type_id)
    queue = next((q for q in queues if q["name"] == config.queue_name), None)
    if not queue:
        raise ValueError(f"Queue {config.queue_name} not found")

    logger.info("Matched queue id=%s", queue["id"])
    time.sleep(1)

    queue_id = queue["id"]

    time_series = api.fetch_time_series()
    logger.info("Loaded %d time series entries", len(time_series))
    time.sleep(1)

    active_schedule = api.fetch_active_schedule()
    logger.info("Loaded %d active schedule entries", len(active_schedule))

    today = datetime.now(KYIV_TZ).date()

    schedule_times: list[IntervalDict] = []
    for item in active_schedule:
        if item["outage_queue_id"] == queue_id:
            for slot in time_series:
                if slot["id"] == item["time_series_id"]:
                    start_time = datetime.strptime(slot["start"], "%H:%M:%S").time()
                    end_time = datetime.strptime(slot["end"], "%H:%M:%S").time()

                    start_dt = datetime.combine(today, start_time, tzinfo=KYIV_TZ)
                    end_dt = datetime.combine(today, end_time, tzinfo=KYIV_TZ)
                    schedule_times.append({
                        "start": start_dt,
                        "end": end_dt,
                        "type": item["type"],
                    })

    logger.info("Collected %d intervals before merge", len(schedule_times))
    schedule_times = merge_adjacent_intervals(schedule_times)
    logger.info("Intervals after merge: %d", len(schedule_times))

    calendar_sync_intervals(schedule_times, reminder_minutes=config.reminder_minutes)


if __name__ == "__main__":
    main()