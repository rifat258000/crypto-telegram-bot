"""DexScreener API client for DEX token data."""

from __future__ import annotations

import httpx

BASE = "https://api.dexscreener.com"
TIMEOUT = 15


async def search_pairs(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/latest/dex/search", params={"q": query})
        r.raise_for_status()
        return (r.json().get("pairs") or [])[:10]


async def get_pair_by_address(chain: str, pair_address: str) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/latest/dex/pairs/{chain}/{pair_address}")
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        return pairs[0] if pairs else None


async def get_token_pairs(token_address: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/latest/dex/tokens/{token_address}")
        r.raise_for_status()
        return (r.json().get("pairs") or [])[:10]


async def get_trending_dex() -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/token-boosts/latest/v1")
        if r.status_code != 200:
            return []
        return (r.json() if isinstance(r.json(), list) else [])[:15]
