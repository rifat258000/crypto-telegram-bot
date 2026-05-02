# Crypto Market Telegram Bot

A Telegram bot that provides real-time crypto market data for **any DEX or CEX token**.

## Features

| Command | Description |
|---------|-------------|
| `/price <token>` | Live price from CoinGecko (CEX) + DexScreener (DEX) |
| `/chart <token> [days]` | Price history chart (1d, 7d, 30d, 90d, 365d) |
| `/info <token>` | Full token details (market cap, volume, supply, ATH, description) |
| `/trending` | Trending tokens on CoinGecko + DEX |
| `/top` | Top 20 coins by market cap |
| `/dex <query>` | Search DEX pairs (by name or contract address) |
| `/search <query>` | Search across both CEX & DEX |
| *plain text* | Send any token name or address to get its price |

### Interactive Buttons
- Switch between chart timeframes (1d / 7d / 30d / 90d / 1y)
- Jump from price → chart → info → DEX pairs
- Browse multiple DEX pairs for a token

## Data Sources

- **[CoinGecko](https://www.coingecko.com/)** — CEX tokens, market caps, charts, trending
- **[DexScreener](https://dexscreener.com/)** — DEX pairs across all chains (Ethereum, Solana, BSC, Base, Arbitrum, etc.)

## Setup

### Prerequisites
- Python 3.11+
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Local Development
```bash
export TELEGRAM_BOT_TOKEN="your-token-here"
pip install .
python -m bot.main
```

### Deploy to Fly.io
```bash
fly launch
fly secrets set TELEGRAM_BOT_TOKEN="your-token-here"
fly deploy
```

## Architecture

```
bot/
├── main.py          # Entry point, registers handlers
├── handlers.py      # Telegram command & callback handlers
├── coingecko.py     # CoinGecko API client
├── dexscreener.py   # DexScreener API client
├── charts.py        # Matplotlib price chart generation
└── fmt.py           # Message formatting helpers
```
