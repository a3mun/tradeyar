# ═══════════════════════════════════════════════════════════
# Trademun — API Dockerfile (Root)
# ═══════════════════════════════════════════════════════════

FROM python:3.11-slim

# ─── متغیرهای محیطی ───
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

# ─── وابستگی‌های سیستمی ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── کاربر non-root ───
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# ─── نصب پکیج‌های پایتون (با mirror پارس‌پک) ───
COPY --chown=user requirements.txt ./
RUN pip config set global.index-url https://mirror.abrha.net/repository/pypi/simple/ \
 && pip config set global.trusted-host mirror.abrha.net \
 && pip install --user --no-cache-dir --default-timeout=1000 -r requirements.txt

# ─── کپی کد پروژه ───
COPY --chown=user . .

# ─── پورت ───
EXPOSE 7860

# ─── Health check ───
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# ─── اجرا ───
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2", "--lifespan", "on"]