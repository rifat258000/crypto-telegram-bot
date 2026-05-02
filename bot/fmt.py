"""Formatting helpers for Telegram messages."""

from __future__ import annotations


def fmt_number(n: float | int | None) -> str:
    if n is None:
        return "N/A"
    if abs(n) >= 1_000_000_000:
        return f"${n / 1_000_000_000:,.2f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:,.2f}M"
    if abs(n) >= 1_000:
        return f"${n / 1_000:,.2f}K"
    return f"${n:,.6g}"


def fmt_price(n: float | None) -> str:
    if n is None:
        return "N/A"
    if n >= 1:
        return f"${n:,.4f}"
    return f"${n:,.10g}"


def fmt_pct(n: float | None) -> str:
    if n is None:
        return "N/A"
    arrow = "\U0001f7e2" if n >= 0 else "\U0001f534"
    return f"{arrow} {n:+.2f}%"


def cex_price_message(data: dict) -> str:
    md = data.get("market_data", {})
    price = md.get("current_price", {}).get("usd")
    mc = md.get("market_cap", {}).get("usd")
    vol = md.get("total_volume", {}).get("usd")
    high24 = md.get("high_24h", {}).get("usd")
    low24 = md.get("low_24h", {}).get("usd")
    change24 = md.get("price_change_percentage_24h")
    change7d = md.get("price_change_percentage_7d")
    change30d = md.get("price_change_percentage_30d")
    rank = data.get("market_cap_rank")
    supply = md.get("circulating_supply")
    total_supply = md.get("total_supply")
    ath = md.get("ath", {}).get("usd")

    name = data.get("name", "?")
    symbol = (data.get("symbol") or "?").upper()

    lines = [
        f"<b>{name} ({symbol})</b>",
        f"{'#' + str(rank) if rank else 'Unranked'} on CoinGecko\n",
        f"<b>Price:</b> {fmt_price(price)}",
        f"<b>24h Change:</b> {fmt_pct(change24)}",
        f"<b>7d Change:</b> {fmt_pct(change7d)}",
        f"<b>30d Change:</b> {fmt_pct(change30d)}\n",
        f"<b>24h High / Low:</b> {fmt_price(high24)} / {fmt_price(low24)}",
        f"<b>Market Cap:</b> {fmt_number(mc)}",
        f"<b>24h Volume:</b> {fmt_number(vol)}",
        f"<b>Circulating:</b> {fmt_number(supply) if supply else 'N/A'}",
        f"<b>Total Supply:</b> {fmt_number(total_supply) if total_supply else 'N/A'}",
        f"<b>ATH:</b> {fmt_price(ath)}",
    ]
    return "\n".join(lines)


def dex_pair_message(pair: dict) -> str:
    base = pair.get("baseToken", {})
    quote = pair.get("quoteToken", {})
    name = base.get("name", "?")
    symbol = base.get("symbol", "?")
    price_usd = pair.get("priceUsd")
    price_native = pair.get("priceNative")
    chain = pair.get("chainId", "?")
    dex = pair.get("dexId", "?")
    liq = pair.get("liquidity", {}).get("usd")
    vol = pair.get("volume", {}).get("h24")
    txns = pair.get("txns", {}).get("h24", {})
    buys = txns.get("buys", "?")
    sells = txns.get("sells", "?")
    chg5m = pair.get("priceChange", {}).get("m5")
    chg1h = pair.get("priceChange", {}).get("h1")
    chg6h = pair.get("priceChange", {}).get("h6")
    chg24h = pair.get("priceChange", {}).get("h24")
    fdv = pair.get("fdv")
    pair_url = pair.get("url", "")

    lines = [
        f"<b>{name} ({symbol})</b>",
        f"<i>{chain.upper()} • {dex}</i>\n",
        f"<b>Price:</b> {fmt_price(float(price_usd)) if price_usd else 'N/A'}",
        f"<b>Price ({quote.get('symbol', '?')}):</b> {price_native or 'N/A'}",
        f"<b>5m:</b> {fmt_pct(chg5m)} | <b>1h:</b> {fmt_pct(chg1h)}",
        f"<b>6h:</b> {fmt_pct(chg6h)} | <b>24h:</b> {fmt_pct(chg24h)}\n",
        f"<b>Liquidity:</b> {fmt_number(liq)}",
        f"<b>24h Volume:</b> {fmt_number(vol)}",
        f"<b>FDV:</b> {fmt_number(fdv)}",
        f"<b>24h Txns:</b> {buys} buys / {sells} sells",
    ]
    if pair_url:
        lines.append(f'\n<a href="{pair_url}">View on DexScreener</a>')
    return "\n".join(lines)
