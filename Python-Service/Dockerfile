FROM python:3.11-slim

WORKDIR /app

# xvfb: virtual ekran (headful Chromium headless-dən çox az bot kimi görünür)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth wget gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Chromium + bütün sistem asılılıqları
RUN python -m playwright install --with-deps chromium

COPY . .

ENV SCRAPER_HEADFUL=1 \
    SCRAPER_DEBUG_DIR=/app/debug \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["xvfb-run", "-a", "--server-args=-screen 0 1366x768x24", \
     "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]