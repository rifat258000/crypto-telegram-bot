"""CoinGecko API client for CEX token data."""

from __future__ import annotations

import httpx

BASE = "https://api.coingecko.com/api/v3"
TIMEOUT = 15


async def search_coins(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/search", params={"query": query})
        r.raise_for_status()
        return r.json().get("coins", [])[:10]


async def get_price(coin_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BASE}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def get_market_chart(coin_id: str, days: int = 7) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BASE}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": str(days)},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def get_trending() -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/search/trending")
        r.raise_for_status()
        return r.json().get("coins", [])[:15]


async def get_top_coins(per_page: int = 20) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": str(per_page),
                "page": "1",
                "sparkline": "false",
            },
        )
        r.raise_for_status()
        return r.json()
