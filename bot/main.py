"""Entry point for the Crypto Telegram Bot.

Runs independently — no AI services required. Uses only free public APIs
(CoinGecko, DexScreener). Auto-restarts on crash via Fly.io + internal loop.
"""

from __future__ import annotations

import logging
import os
import sys
import time

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.handlers import (
    start_cmd,
    price_cmd,
    chart_cmd,
    info_cmd,
    trending_cmd,
    top_cmd,
    dex_cmd,
    search_cmd,
    text_handler,
    callback_handler,
    error_handler,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

MAX_RESTART_ATTEMPTS = 50
RESTART_COOLDOWN = 10


def run_bot(token: str) -> None:
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("p", price_cmd))
    app.add_handler(CommandHandler("chart", chart_cmd))
    app.add_handler(CommandHandler("c", chart_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CommandHandler("i", info_cmd))
    app.add_handler(CommandHandler("trending", trending_cmd))
    app.add_handler(CommandHandler("t", trending_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("dex", dex_cmd))
    app.add_handler(CommandHandler("d", dex_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("s", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    log.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        log.error("TELEGRAM_BOT_TOKEN env var is not set.")
        sys.exit(1)

    for attempt in range(1, MAX_RESTART_ATTEMPTS + 1):
        try:
            run_bot(token)
            break
        except KeyboardInterrupt:
            log.info("Shutting down gracefully.")
            break
        except Exception:
            log.exception("Bot crashed (attempt %d/%d). Restarting in %ds...",
                          attempt, MAX_RESTART_ATTEMPTS, RESTART_COOLDOWN)
            time.sleep(RESTART_COOLDOWN)

    log.info("Bot process exiting.")


if __name__ == "__main__":
    main()
