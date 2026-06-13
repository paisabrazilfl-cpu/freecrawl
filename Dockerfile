FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps 2>/dev/null || playwright install chromium

COPY . .

EXPOSE 8000
