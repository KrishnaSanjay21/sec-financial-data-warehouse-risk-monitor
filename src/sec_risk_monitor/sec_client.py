"""Polite, retrying client for public SEC EDGAR endpoints."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from .config import Settings


class SecApiError(RuntimeError):
    """Raised when an SEC endpoint cannot be read safely."""


@dataclass(frozen=True)
class SecResponse:
    endpoint: str
    payload: dict[str, Any]
    fetched_at: datetime
    sha256: str
    etag: str | None
    last_modified: str | None


class SecClient:
    """HTTP client that identifies itself, throttles requests, and records lineage."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._minimum_interval = 1.0 / settings.sec_requests_per_second
        self._last_request = 0.0
        self._lock = threading.Lock()
        self._client = httpx.Client(
            headers={
                "User-Agent": settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
            timeout=45.0,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        with self._lock:
            wait_for = self._minimum_interval - (time.monotonic() - self._last_request)
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, SecApiError)),
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def get_json(self, url: str) -> SecResponse:
        self._throttle()
        response = self._client.get(url)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise SecApiError(f"Retryable SEC response {response.status_code} for {url}")
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise SecApiError(f"Invalid SEC response for {url}: {exc}") from exc

        digest = hashlib.sha256(response.content).hexdigest()
        return SecResponse(
            endpoint=url,
            payload=payload,
            fetched_at=datetime.now(UTC),
            sha256=digest,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def company_tickers(self) -> SecResponse:
        return self.get_json(f"{self.settings.sec_www_url}/files/company_tickers.json")

    def submissions(self, cik: int | str) -> SecResponse:
        return self.get_json(
            f"{self.settings.sec_base_url}/submissions/CIK{int(cik):010d}.json"
        )

    def company_facts(self, cik: int | str) -> SecResponse:
        return self.get_json(
            f"{self.settings.sec_base_url}/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
        )


def resolve_universe(ticker_payload: dict[str, Any], requested: list[str]) -> list[dict[str, Any]]:
    """Resolve configured tickers to SEC CIKs while preserving requested order."""

    lookup = {
        row["ticker"].upper().replace(".", "-"): row
        for row in ticker_payload.values()
    }
    missing = [ticker for ticker in requested if ticker.replace(".", "-") not in lookup]
    if missing:
        raise SecApiError(f"Tickers missing from SEC company file: {', '.join(missing)}")
    return [lookup[ticker.replace(".", "-")] for ticker in requested]

