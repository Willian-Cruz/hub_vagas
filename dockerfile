# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Hub Vagas
# Deploy: Render (Background Worker com Cron Job)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Evita arquivos .pyc e garante logs em tempo real no Render
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Dependências de sistema ───────────────────────────────────────────────────
# libpq-dev + gcc: necessários para psycopg2 compilar
# chromium + libs: necessários para o Playwright (VagasScraper)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        chromium \
        chromium-driver \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Playwright usa o Chromium do sistema operacional
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin \
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# ── Diretório de trabalho ─────────────────────────────────────────────────────
WORKDIR /app

# ── Dependências Python ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Código da aplicação ───────────────────────────────────────────────────────
COPY app/ ./

# ── Diretórios de saída ───────────────────────────────────────────────────────
RUN mkdir -p /app/logs /app/dashboard

# ── Comando padrão ────────────────────────────────────────────────────────────
# No Render, este container é configurado como Cron Job.
# O Render dispara este comando no horário agendado,
# aguarda a conclusão e registra o código de saída.
CMD ["python", "main.py"]