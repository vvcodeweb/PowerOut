from __future__ import annotations

import logging
from typing import Mapping

import requests

logger = logging.getLogger(__name__)


class PowerOutageAPI:
    def __init__(self, base_url: str, session: requests.Session) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session

    def _get_json(self, path: str, *, params: dict | None = None) -> list[Mapping[str, object]]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("HTTP request failed for %s: %s", url, exc)
            raise

        logger.info(
            "Response from %s: status=%s, content-length=%s, content-encoding=%s",
            url,
            response.status_code,
            len(response.content),
            response.headers.get("Content-Encoding", "none"),
        )
        logger.info("Response headers: %s", dict(response.headers))
        
        content_type = response.headers.get("Content-Type", "").lower()
        
        if response.status_code == 403:
            logger.error("403 Forbidden - likely Cloudflare block")
            try:
                preview = response.text[:500]
                logger.error("Response preview: %s", preview)
            except UnicodeDecodeError:
                logger.error("Response is binary/compressed")
            raise requests.RequestException(f"403 Forbidden from {url} - possible Cloudflare block")
        
        if "text/html" in content_type:
            logger.warning("Received HTML instead of JSON: status=%s, content-type=%s", response.status_code, content_type)
            try:
                html_preview = response.text[:1000]
                logger.info("HTML preview: %s", html_preview)
                if "cloudflare" in html_preview.lower() or "challenge" in html_preview.lower() or "just a moment" in html_preview.lower():
                    logger.error("Cloudflare challenge page detected!")
                    raise requests.RequestException(f"Cloudflare challenge page detected: {url}")
            except UnicodeDecodeError:
                logger.warning("Could not decode HTML preview")
        
        logger.info("Raw response content (first 500 bytes): %r", response.content[:500])

        try:
            return response.json()
        except ValueError as exc:
            content_type = response.headers.get("Content-Type", "unknown")
            content_length = len(response.content)
            status_code = response.status_code
            
            preview = ""
            try:
                preview = response.text[:200].replace("\n", " ")
            except (UnicodeDecodeError, AttributeError):
                preview = f"<binary content, {content_length} bytes>"
            
            logger.error(
                "Failed to decode JSON from %s (status %s, content-type %s): %s",
                url,
                status_code,
                content_type,
                preview,
            )
            raise

    def fetch_time_series(self) -> list[Mapping[str, object]]:
        logger.info("Fetching time series")
        return self._get_json("/schedule/time-series")

    def fetch_queues(self, queue_type_id: int) -> list[Mapping[str, object]]:
        logger.info("Fetching outage queues for type %s", queue_type_id)
        return self._get_json(f"/outage-queue/by-type/{queue_type_id}")

    def fetch_active_schedule(self) -> list[Mapping[str, object]]:
        logger.info("Fetching active schedule")
        return self._get_json("/schedule/active")

