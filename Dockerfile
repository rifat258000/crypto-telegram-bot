FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY bot/ bot/

RUN pip install --no-cache-dir "python-telegram-bot[job-queue]>=21.0" "httpx>=0.27" "matplotlib>=3.9"

CMD ["python", "-m", "bot.main"]
