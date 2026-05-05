"""Telegram bot command & callback handlers."""

from __future__ import annotations

import io
import logging
import re
import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import coingecko, dexscreener, charts, fmt, calc, wallet

log = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────────────

HELP_TEXT = (
    "<b>Crypto Market Bot</b>\n\n"
    "<b>Commands:</b>\n"
    "/price (/p) &lt;token&gt; — Live price (CEX + DEX)\n"
    "/chart (/c) &lt;token&gt; [1|7|30|90|365] — Price chart\n"
    "/info (/i) &lt;token&gt; — Detailed token info\n"
    "/trending (/t) — Trending tokens\n"
    "/top — Top 20 coins by market cap\n"
    "/dex (/d) &lt;query&gt; — Search DEX pairs\n"
    "/search (/s) &lt;query&gt; — Search all tokens\n"
    "/help — Show this message\n\n"
    "<b>No command needed:</b>\n"
    "• <code>50 btc</code> — Total price of 50 BTC\n"
    "• <code>23+23</code> — Calculator\n"
    "• Paste wallet address — Multi-chain balances\n"
    "• Type any token name — Quick price\n\n"
    "<b>Works in groups!</b>\n"
    "<i>@mention me for price/token lookup.\n"
    "Calculator &amp; crypto qty work without mention (if admin).</i>"
)


async def _safe_reply(update: Update, text: str, **kw):
    msg = update.message or (update.callback_query and update.callback_query.message)
    if msg:
        await msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, **kw)


def _hd_logo_url(data: dict) -> str:
    """Extract the highest resolution logo URL available."""
    images = data.get("image") or {}
    large_url = images.get("large") or ""
    if large_url:
        return large_url.replace("/large/", "/original/")
    return ""


def _dex_hd_logo_url(pair: dict) -> str:
    """Extract HD logo URL from DexScreener pair data."""
    info = pair.get("info") or {}
    url = info.get("imageUrl") or ""
    if url and "width=" in url:
        # Remove size constraints for full resolution
        base = url.split("?")[0]
        return base
    return url


async def _safe_reply_photo(update: Update, photo_url: str, caption: str, **kw):
    """Send a photo with caption. Falls back to text if photo fails."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if not msg:
        return
    try:
        await msg.reply_photo(
            photo=photo_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            **kw,
        )
    except Exception:
        await msg.reply_text(caption, parse_mode=ParseMode.HTML, disable_web_page_preview=True, **kw)


# ── /start & /help ──────────────────────────────────────────────────────

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(update, HELP_TEXT)


# ── /price ──────────────────────────────────────────────────────────────


def _best_coin(coins: list[dict], query: str) -> dict | None:
    q = query.lower().strip()
    # Exact name match is strongest (e.g. "bitcoin" → Bitcoin)
    for c in coins:
        if (c.get("name") or "").lower() == q:
            return c
    # Exact symbol match, but prefer ranked coins to avoid meme token hijacking
    sym_matches = [c for c in coins if (c.get("symbol") or "").lower() == q]
    ranked = [c for c in sym_matches if c.get("market_cap_rank")]
    if ranked:
        return min(ranked, key=lambda c: c["market_cap_rank"])
    if sym_matches:
        return sym_matches[0]
    return None


async def _show_price(update: Update, coin_id: str, query: str):
    data = await coingecko.get_price(coin_id)
    if data:
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📈 Chart 7d", callback_data=f"chart:{coin_id}:7"),
                InlineKeyboardButton("📊 Chart 30d", callback_data=f"chart:{coin_id}:30"),
            ],
            [
                InlineKeyboardButton("ℹ️ Full Info", callback_data=f"info:{coin_id}"),
                InlineKeyboardButton("🔍 DEX Pairs", callback_data=f"dex_search:{query[:53]}"),
            ],
        ])
        logo_url = _hd_logo_url(data)
        caption = fmt.cex_price_message(data)
        if logo_url:
            await _safe_reply_photo(update, logo_url, caption, reply_markup=kb)
        else:
            await _safe_reply(update, caption, reply_markup=kb)
        return True
    return False


async def price_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await _safe_reply(update, "Usage: /price &lt;token&gt;\nExample: /price bitcoin")
        return
    query = " ".join(ctx.args)
    await _safe_reply(update, f"Looking up <b>{query}</b>...")

    # Try CoinGecko first
    coins = await coingecko.search_coins(query)
    if coins:
        # Check for exact symbol/name match first
        best = _best_coin(coins, query)
        if best:
            if await _show_price(update, best["id"], query):
                return
        elif len(coins) == 1:
            if await _show_price(update, coins[0]["id"], query):
                return
        else:
            # Multiple ambiguous results — show selection buttons
            buttons = []
            seen = set()
            for c in coins[:8]:
                cid = c["id"]
                if cid in seen:
                    continue
                seen.add(cid)
                name = c.get("name", cid)
                sym = (c.get("symbol") or "").upper()
                rank = c.get("market_cap_rank")
                label = f"{name} ({sym})"
                if rank:
                    label += f" #{rank}"
                buttons.append(
                    [InlineKeyboardButton(label, callback_data=f"price_cb:{cid}")]
                )
            kb = InlineKeyboardMarkup(buttons)
            await _safe_reply(
                update,
                f"Multiple tokens found for <b>{query}</b>.\n"
                "Pick the one you want:",
                reply_markup=kb,
            )
            return

    # Fallback: try DexScreener
    pairs = await dexscreener.search_pairs(query)
    if pairs:
        pair = pairs[0]
        kb = _dex_pair_keyboard(pairs)
        logo_url = _dex_hd_logo_url(pair)
        caption = fmt.dex_pair_message(pair)
        if logo_url:
            await _safe_reply_photo(update, logo_url, caption, reply_markup=kb)
        else:
            await _safe_reply(update, caption, reply_markup=kb)
        return

    await _safe_reply(update, f"No results found for <b>{query}</b>.")


# ── /chart ──────────────────────────────────────────────────────────────

async def chart_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await _safe_reply(update, "Usage: /chart &lt;token&gt; [days]\nExample: /chart bitcoin 30")
        return
    days = 7
    if ctx.args[-1].isdigit():
        days = int(ctx.args[-1])
        query = " ".join(ctx.args[:-1])
    else:
        query = " ".join(ctx.args)

    if not query:
        await _safe_reply(update, "Please provide a token name.")
        return

    await _safe_reply(update, f"Generating chart for <b>{query}</b> ({days}d)...")
    coins = await coingecko.search_coins(query)
    if not coins:
        await _safe_reply(update, f"Token <b>{query}</b> not found.")
        return

    coin_id = coins[0]["id"]
    chart_data = await coingecko.get_market_chart(coin_id, days)
    if not chart_data or not chart_data.get("prices"):
        await _safe_reply(update, "Could not fetch chart data.")
        return

    name = coins[0].get("name", query)
    symbol = coins[0].get("symbol", "").upper()
    img = charts.generate_price_chart(
        chart_data["prices"],
        title=f"{name} ({symbol}) — {days}d",
        days=days,
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1d", callback_data=f"chart:{coin_id}:1"),
            InlineKeyboardButton("7d", callback_data=f"chart:{coin_id}:7"),
            InlineKeyboardButton("30d", callback_data=f"chart:{coin_id}:30"),
            InlineKeyboardButton("90d", callback_data=f"chart:{coin_id}:90"),
            InlineKeyboardButton("1y", callback_data=f"chart:{coin_id}:365"),
        ],
        [InlineKeyboardButton("💰 Price", callback_data=f"price_cb:{coin_id}")],
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_photo(photo=io.BytesIO(img), caption=f"{name} ({symbol}) — {days}d chart", reply_markup=kb)


# ── /info ───────────────────────────────────────────────────────────────

async def info_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await _safe_reply(update, "Usage: /info &lt;token&gt;\nExample: /info ethereum")
        return
    query = " ".join(ctx.args)
    await _safe_reply(update, f"Fetching info for <b>{query}</b>...")

    coins = await coingecko.search_coins(query)
    if coins:
        data = await coingecko.get_price(coins[0]["id"])
        if data:
            desc = (data.get("description", {}).get("en") or "")[:500]
            links = data.get("links", {})
            homepage = (links.get("homepage") or [""])[0]
            text = fmt.cex_price_message(data)
            if desc:
                # strip HTML tags from CoinGecko description
                import re
                desc_clean = re.sub(r"<[^>]+>", "", desc)
                text += f"\n\n<b>About:</b> {desc_clean}..."
            if homepage:
                text += f'\n<b>Website:</b> <a href="{homepage}">{homepage}</a>'
            await _safe_reply(update, text)
            return

    pairs = await dexscreener.search_pairs(query)
    if pairs:
        await _safe_reply(update, fmt.dex_pair_message(pairs[0]))
        return

    await _safe_reply(update, f"No info found for <b>{query}</b>.")


# ── /trending ───────────────────────────────────────────────────────────

async def trending_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(update, "Fetching trending tokens...")
    coins = await coingecko.get_trending()
    if not coins:
        await _safe_reply(update, "Could not fetch trending tokens.")
        return

    lines = ["<b>🔥 Trending on CoinGecko</b>\n"]
    for i, c in enumerate(coins, 1):
        item = c.get("item", {})
        name = item.get("name", "?")
        symbol = item.get("symbol", "?")
        rank = item.get("market_cap_rank") or "—"
        coin_id = item.get("id", "")
        price_btc = item.get("price_btc")
        price_str = f" | {price_btc:.8f} BTC" if price_btc else ""
        lines.append(f"{i}. <b>{name}</b> ({symbol}) #{rank}{price_str}")

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔥 DEX Trending", callback_data="dex_trending"),
    ]])
    await _safe_reply(update, "\n".join(lines), reply_markup=kb)


# ── /top ────────────────────────────────────────────────────────────────

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(update, "Fetching top coins...")
    coins = await coingecko.get_top_coins(20)
    if not coins:
        await _safe_reply(update, "Could not fetch top coins.")
        return

    lines = ["<b>🏆 Top 20 by Market Cap</b>\n"]
    for i, c in enumerate(coins, 1):
        symbol = c.get("symbol", "?").upper()
        price = c.get("current_price")
        change = c.get("price_change_percentage_24h")
        mc = c.get("market_cap")
        lines.append(
            f"{i}. <b>{symbol}</b> {fmt.fmt_price(price)} "
            f"{fmt.fmt_pct(change)} | MC: {fmt.fmt_number(mc)}"
        )
    await _safe_reply(update, "\n".join(lines))


# ── /dex ────────────────────────────────────────────────────────────────

async def dex_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await _safe_reply(update, "Usage: /dex &lt;token or address&gt;\nExample: /dex PEPE")
        return
    query = " ".join(ctx.args)
    await _safe_reply(update, f"Searching DEX pairs for <b>{query}</b>...")

    # If it looks like a contract address, use token endpoint
    if len(query) > 30 and not " " in query:
        pairs = await dexscreener.get_token_pairs(query)
    else:
        pairs = await dexscreener.search_pairs(query)

    if not pairs:
        await _safe_reply(update, f"No DEX pairs found for <b>{query}</b>.")
        return

    pair = pairs[0]
    kb = _dex_pair_keyboard(pairs)
    await _safe_reply(update, fmt.dex_pair_message(pair), reply_markup=kb)


# ── /search ─────────────────────────────────────────────────────────────

async def search_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await _safe_reply(update, "Usage: /search &lt;query&gt;")
        return
    query = " ".join(ctx.args)
    await _safe_reply(update, f"Searching for <b>{query}</b> across CEX & DEX...")

    cex_coins = await coingecko.search_coins(query)
    dex_pairs = await dexscreener.search_pairs(query)

    lines = []
    if cex_coins:
        lines.append("<b>CEX Results (CoinGecko):</b>")
        for c in cex_coins[:5]:
            name = c.get("name", "?")
            symbol = c.get("symbol", "?").upper()
            rank = c.get("market_cap_rank")
            rank_str = f" #{rank}" if rank else ""
            lines.append(f"• <b>{name}</b> ({symbol}){rank_str}")
        lines.append("")

    if dex_pairs:
        lines.append("<b>DEX Results (DexScreener):</b>")
        for p in dex_pairs[:5]:
            base = p.get("baseToken", {})
            name = base.get("name", "?")
            symbol = base.get("symbol", "?")
            chain = p.get("chainId", "?")
            price = p.get("priceUsd")
            price_str = f" — {fmt.fmt_price(float(price))}" if price else ""
            lines.append(f"• <b>{name}</b> ({symbol}) [{chain}]{price_str}")

    if not lines:
        await _safe_reply(update, f"No results for <b>{query}</b>.")
        return

    buttons = []
    if cex_coins:
        cid = cex_coins[0]["id"]
        buttons.append([
            InlineKeyboardButton("💰 Price", callback_data=f"price_cb:{cid}"),
            InlineKeyboardButton("📈 Chart", callback_data=f"chart:{cid}:7"),
        ])
    if dex_pairs:
        buttons.append([InlineKeyboardButton("🔍 DEX Details", callback_data=f"dex_search:{query[:53]}")])

    kb = InlineKeyboardMarkup(buttons) if buttons else None
    await _safe_reply(update, "\n".join(lines), reply_markup=kb)


# ── plain text handler (search by name or address) ──────────────────────

BOT_USERNAME: str | None = None
BOT_ID: int | None = None


async def _bot_is_admin(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    global BOT_ID
    try:
        if BOT_ID is None:
            bot_info = await ctx.bot.get_me()
            BOT_ID = bot_info.id
        member = await ctx.bot.get_chat_member(chat_id, BOT_ID)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global BOT_USERNAME
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # In group chats: @mention required for price/token lookup.
    # Math calc & crypto qty work without mention (if bot is admin).
    chat_type = update.effective_chat.type if update.effective_chat else "private"
    is_group = chat_type in ("group", "supergroup")
    mentioned = False
    if is_group:
        if BOT_USERNAME is None:
            bot_info = await ctx.bot.get_me()
            BOT_USERNAME = bot_info.username or ""
        mention = f"@{BOT_USERNAME}"
        has_mention = mention.lower() in text.lower()

        if has_mention:
            mentioned = True
            text = re.sub(re.escape(mention), "", text, flags=re.IGNORECASE).strip()
            if not text:
                await _safe_reply(update, HELP_TEXT)
                return
        else:
            # Not mentioned — only allow math/crypto-qty if bot is admin
            is_admin = await _bot_is_admin(update.effective_chat.id, ctx)
            if not is_admin:
                return

    # 1) Math calculator: 23+23, 100/5, etc. (works without mention in groups)
    math_result = calc.try_math(text)
    if math_result:
        await _safe_reply(update, math_result)
        return

    # 2) Crypto quantity: "50 btc", "2 eth" (works without mention in groups)
    parsed = calc.parse_crypto_qty(text)
    if parsed:
        qty, symbol = parsed
        coins = await coingecko.search_coins(symbol)
        if coins:
            best = _best_coin(coins, symbol)
            coin_id = best["id"] if best else coins[0]["id"]
            data = await coingecko.get_price(coin_id)
            if data:
                md = data.get("market_data") or {}
                price = (md.get("current_price") or {}).get("usd")
                if price:
                    total = price * qty
                    name = data.get("name", symbol.upper())
                    sym = (data.get("symbol") or symbol).upper()
                    logo_url = _hd_logo_url(data)
                    msg = (
                        f"<b>{qty:,.6g} {sym}</b>\n\n"
                        f"💰 Price: <b>{fmt.fmt_price(price)}</b>\n"
                        f"💵 Total: <b>${total:,.2f}</b>"
                    )
                    if logo_url:
                        await _safe_reply_photo(update, logo_url, msg)
                    else:
                        await _safe_reply(update, msg)
                    return

    # In groups without @mention, stop here — no token/wallet/price lookup
    if is_group and not mentioned:
        return

    # 3) Wallet address: show multi-chain balances (requires @mention in groups)
    clean = text.split()[0] if text.split() else text
    if wallet.detect_address_type(clean):
        await _safe_reply(update, "Looking up wallet balances...")
        result = await wallet.get_wallet_balances(clean)
        if result:
            await _safe_reply(update, result)
            return

    # 4) Default: search token by name (requires @mention in groups)
    ctx.args = text.split()
    await price_cmd(update, ctx)


# ── callback query handler ──────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    try:
        if data.startswith("price_cb:"):
            coin_id = data.split(":", 1)[1]
            d = await coingecko.get_price(coin_id)
            if d:
                logo_url = _hd_logo_url(d)
                caption = fmt.cex_price_message(d)
                if logo_url:
                    try:
                        await q.message.reply_photo(
                            photo=logo_url, caption=caption, parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        await q.message.reply_text(caption, parse_mode=ParseMode.HTML)
                else:
                    await q.message.reply_text(caption, parse_mode=ParseMode.HTML)
            else:
                await q.message.reply_text("Could not fetch price.")

        elif data.startswith("chart:"):
            parts = data.split(":")
            coin_id = parts[1]
            days = int(parts[2]) if len(parts) > 2 else 7
            chart_data = await coingecko.get_market_chart(coin_id, days)
            if chart_data and chart_data.get("prices"):
                img = charts.generate_price_chart(chart_data["prices"], title=f"{coin_id} — {days}d", days=days)
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("1d", callback_data=f"chart:{coin_id}:1"),
                        InlineKeyboardButton("7d", callback_data=f"chart:{coin_id}:7"),
                        InlineKeyboardButton("30d", callback_data=f"chart:{coin_id}:30"),
                        InlineKeyboardButton("90d", callback_data=f"chart:{coin_id}:90"),
                        InlineKeyboardButton("1y", callback_data=f"chart:{coin_id}:365"),
                    ],
                    [InlineKeyboardButton("💰 Price", callback_data=f"price_cb:{coin_id}")],
                ])
                await q.message.reply_photo(photo=io.BytesIO(img), caption=f"{coin_id} — {days}d chart", reply_markup=kb)
            else:
                await q.message.reply_text("Could not fetch chart data.")

        elif data.startswith("info:"):
            coin_id = data.split(":", 1)[1]
            d = await coingecko.get_price(coin_id)
            if d:
                await q.message.reply_text(fmt.cex_price_message(d), parse_mode=ParseMode.HTML)

        elif data.startswith("dex_search:"):
            query = data.split(":", 1)[1]
            pairs = await dexscreener.search_pairs(query)
            if pairs:
                kb = _dex_pair_keyboard(pairs)
                await q.message.reply_text(fmt.dex_pair_message(pairs[0]), parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await q.message.reply_text("No DEX pairs found.")

        elif data.startswith("dex_pair:"):
            parts = data.split(":", 2)
            chain, addr = parts[1], parts[2]
            pair = await dexscreener.get_pair_by_address(chain, addr)
            if pair:
                await q.message.reply_text(fmt.dex_pair_message(pair), parse_mode=ParseMode.HTML)
            else:
                await q.message.reply_text("Pair not found.")

        elif data == "dex_trending":
            pairs = await dexscreener.get_trending_dex()
            if not pairs:
                await q.message.reply_text("Could not fetch DEX trending.")
                return
            lines = ["<b>🔥 DEX Boosted Tokens</b>\n"]
            for i, t in enumerate(pairs[:10], 1):
                name = t.get("description") or t.get("tokenAddress", "?")[:12]
                chain = t.get("chainId", "?")
                url = t.get("url", "")
                link = f' <a href="{url}">view</a>' if url else ""
                lines.append(f"{i}. <b>{name}</b> [{chain}]{link}")
            await q.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    except Exception:
        log.error("callback error: %s", traceback.format_exc())
        await q.message.reply_text("Something went wrong. Please try again.")


# ── error handler ───────────────────────────────────────────────────────

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error("Unhandled exception: %s", ctx.error, exc_info=ctx.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Temporary error — please try again in a moment."
            )
        except Exception:
            pass


# ── keyboard helpers ────────────────────────────────────────────────────

def _dex_pair_keyboard(pairs: list[dict]) -> InlineKeyboardMarkup | None:
    buttons = []
    for p in pairs[1:5]:
        base = p.get("baseToken", {})
        symbol = base.get("symbol", "?")
        chain = p.get("chainId", "?")
        addr = p.get("pairAddress", "")
        if addr:
            buttons.append(InlineKeyboardButton(
                f"{symbol} ({chain})", callback_data=f"dex_pair:{chain}:{addr}"[:64]
            ))
    if not buttons:
        return None
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)
