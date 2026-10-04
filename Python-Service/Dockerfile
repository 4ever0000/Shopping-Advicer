FROM python:3.11-slim

WORKDIR /app

# Sistem asılılıqlarını quraşdırırıq
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Əvvəlcə playwright paketini tam quraşdırırıq
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir playwright
RUN pip install --no-cache-dir -r requirements.txt

# Playwright və brauzer asılılıqlarını python modulu kimi işə salırıq
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]