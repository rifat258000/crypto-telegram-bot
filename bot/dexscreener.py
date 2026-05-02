"""DexScreener API client for DEX token data."""

from __future__ import annotations

import logging

from bot.http_client import fetch

log = logging.getLogger(__name__)

BASE = "https://api.dexscreener.com"


async def search_pairs(query: str) -> list[dict]:
    try:
        r = await fetch(f"{BASE}/latest/dex/search", params={"q": query})
        r.raise_for_status()
        return (r.json().get("pairs") or [])[:10]
    except Exception:
        log.exception("search_pairs failed for %s", query)
        return []


async def get_pair_by_address(chain: str, pair_address: str) -> dict | None:
    try:
        r = await fetch(f"{BASE}/latest/dex/pairs/{chain}/{pair_address}")
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        return pairs[0] if pairs else None
    except Exception:
        log.exception("get_pair_by_address failed for %s/%s", chain, pair_address)
        return None


async def get_token_pairs(token_address: str) -> list[dict]:
    try:
        r = await fetch(f"{BASE}/latest/dex/tokens/{token_address}")
        r.raise_for_status()
        return (r.json().get("pairs") or [])[:10]
    except Exception:
        log.exception("get_token_pairs failed for %s", token_address)
        return []


async def get_trending_dex() -> list[dict]:
    try:
        r = await fetch(f"{BASE}/token-boosts/latest/v1")
        if r.status_code != 200:
            return []
        data = r.json()
        return (data if isinstance(data, list) else [])[:15]
    except Exception:
        log.exception("get_trending_dex failed")
        return []
