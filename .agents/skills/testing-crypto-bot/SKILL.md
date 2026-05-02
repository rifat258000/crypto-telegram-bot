---
name: testing-crypto-bot
description: Test the crypto market Telegram bot end-to-end. Use when verifying API integrations, message formatting, chart generation, or deployment health.
---

# Testing the Crypto Telegram Bot

## Overview
This bot uses CoinGecko (CEX) and DexScreener (DEX) APIs to provide crypto market data via Telegram. Testing is primarily done via direct Python API calls since Telegram Web requires phone-number login.

## Devin Secrets Needed
- `TELEGRAM_BOT_TOKEN` — Telegram Bot API token from @BotFather
- `FLY_API_TOKEN` — Fly.io personal access token for deployment management

## Prerequisites
- Python 3.11+ with dependencies installed: `pip install python-telegram-bot[job-queue] httpx matplotlib`
- Fly CLI installed: `curl -L https://fly.io/install.sh | sh`
- Bot deployed on Fly.io app `crypto-tg-bot-rifat`

## Testing Approach

Since Telegram Web requires phone-number authentication (not available in automated environments), test via:

1. **Direct API function calls** — Import and call `bot.coingecko`, `bot.dexscreener`, `bot.charts`, `bot.fmt` modules directly
2. **Telegram Bot API health check** — Call `getMe` endpoint to verify bot is online
3. **Fly.io deployment checks** — Use `flyctl status` and `flyctl logs` to verify bot health

## Key Test Cases

### Bot Health
```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | python3 -m json.tool
```
Expect: `is_bot=true`, correct `username`

### API Integration Tests
Run from the repo root:
```python
import asyncio
from bot import coingecko, dexscreener, charts, fmt

async def test():
    # CoinGecko CEX
    coins = await coingecko.search_coins('bitcoin')
    price = await coingecko.get_price('bitcoin')
    chart = await coingecko.get_market_chart('bitcoin', 7)
    trending = await coingecko.get_trending()
    top = await coingecko.get_top_coins(20)

    # DexScreener DEX
    pairs = await dexscreener.search_pairs('PEPE')
    token_pairs = await dexscreener.get_token_pairs('0x6982508145454Ce325dDbE47a25d4ec3d2311933')

    # Chart generation
    img = charts.generate_price_chart(chart['prices'], title='Test', days=7)
    assert img[:4] == b'\x89PNG' and len(img) > 10000

    # Message formatting
    msg = fmt.cex_price_message(price)
    assert 'Bitcoin (BTC)' in msg and 'Price:' in msg

asyncio.run(test())
```

### Deployment Verification
```bash
export PATH="$HOME/.fly/bin:$PATH"
flyctl status --app crypto-tg-bot-rifat
flyctl logs --app crypto-tg-bot-rifat --no-tail
```
Expect: Machine in `started` state, logs showing `Bot starting...` and successful `getUpdates` polling

## Common Issues
- **CoinGecko rate limits**: Free API has rate limits (~10-30 req/min). If tests fail with HTTP 429, wait and retry.
- **DexScreener token address lookups**: Use full contract addresses (e.g., `0x6982508145454Ce325dDbE47a25d4ec3d2311933` for PEPE on Ethereum).
- **Fly.io deployment**: If the bot isn't responding, check `flyctl logs` for errors. The bot uses polling mode (not webhooks), so it needs a running machine.
- **Chart generation**: Requires matplotlib with Agg backend (headless). This is already configured in `bot/charts.py`.

## Architecture Reference
- `bot/main.py` — Entry point, registers all handlers
- `bot/handlers.py` — Command handlers (/price, /chart, /info, /trending, /top, /dex, /search)
- `bot/coingecko.py` — CoinGecko API client
- `bot/dexscreener.py` — DexScreener API client
- `bot/charts.py` — Matplotlib chart generation
- `bot/fmt.py` — Message formatting helpers
