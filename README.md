# PowerOut

Automates downloading the current outage schedule from `off.energy.mk.ua` and mirrors it to Google Calendar. Requests are routed through a browser-like session with rotating user-agents, and the calendar is cleaned/recreated on every sync so the events always reflect the latest schedule.

## Features
- **Dynamic data ingest**: `PowerOutageAPI` streams queue definitions, time-series slots, and the active schedule from the public API.
- **Realistic HTTP fingerprints**: headers and user-agents are randomly selected from `http_client/user-agents.txt` to avoid rate limiting.
- **Schedule normalization**: intervals are converted to timezone-aware datetimes and adjacent blocks of the same type are merged.
- **Google Calendar sync**: existing events for the current day are removed, then new events (with optional reminders) are created via the Calendar API.
- **CI automation**: `.github/workflows/sync.yaml` runs the sync daily or on demand and uploads the run log.

## Prerequisites
- Python 3.12+
- Google Cloud OAuth credentials (Desktop app) with Calendar API enabled
- Optional: GitHub repository with Actions enabled for scheduled runs

## Setup
```bash
pip install -r requirements.txt
```

## Configuration
All settings are provided via environment variables. Defaults are shown in parentheses.

| Variable | Description |
| --- | --- |
| `API_BASE_URL` (`https://off.energy.mk.ua/api`) | REST endpoint for outage data |
| `QUEUE_NAME` (`1.1`) | Human-readable queue label to sync |
| `QUEUE_TYPE_ID` (`3`) | Numeric queue type, used when filtering |
| `REMINDER_MINUTES` (`15`) | Popup reminder before each event |
| `GOOGLE_CREDENTIALS_FILE` (`calendar_sync/credentials.json`) | OAuth client JSON path |
| `GOOGLE_TOKEN_FILE` (`calendar_sync/token.json`) | Token cache produced after the first login |
| `CALENDAR_NAME` (`Power Outages`) | Target Google Calendar summary |

Set them ad-hoc:

```bash
export QUEUE_NAME="1.2"
export REMINDER_MINUTES=10
python main.py
```

## Running Locally
1. Ensure the virtual environment is active and dependencies are installed.
2. Place your Google credentials JSON at `calendar_sync/credentials.json`
3. Set `QUEUE_NAME`
4. Execute `python main.py`. Logs are emitted to stdout; warnings include raw HTTP headers/content when Cloudflare returns unexpected payloads.

## GitHub Actions
The `Power Outage Notifier` workflow (`.github/workflows/sync.yaml`) runs nightly at 03:00 UTC and supports manual dispatch. Required secrets:
- `GOOGLE_CREDENTIALS_JSON`: contents of the OAuth client file
- `GOOGLE_TOKEN_JSON`: refresh token JSON (optional; speeds up runs)

Each run installs dependencies, restores credentials, executes `python main.py`, stores the output in `logs/run.log`, and publishes it as an artifact.

