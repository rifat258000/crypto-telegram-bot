"""Shared HTTP client with retry logic for resilient API calls."""

from __future__ import annotations

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]


async def fetch(
    url: str,
    params: dict | None = None,
    retries: int = MAX_RETRIES,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                r = await c.get(url, params=params)
                if r.status_code == 429:
                    wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    log.warning("Rate limited on %s, retrying in %ds", url, wait)
                    await asyncio.sleep(wait)
                    continue
                return r
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            last_exc = exc
            wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            log.warning("Network error on %s (attempt %d/%d): %s — retrying in %ds",
                        url, attempt + 1, retries, exc, wait)
            await asyncio.sleep(wait)
        except Exception as exc:
            last_exc = exc
            log.error("Unexpected error on %s: %s", url, exc)
            break

    log.error("All %d retries exhausted for %s", retries, url)
    if last_exc:
        raise last_exc
    raise httpx.ReadTimeout(f"Failed after {retries} retries: {url}")
