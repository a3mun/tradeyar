"""
api/config.py
تنظیمات مرکزی API — با Pydantic Settings
============================================================
خواندن متغیرهای محیطی از .env
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# ═══════════════════════════════════════════════════════════
# مسیرهای پروژه
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════
# تنظیمات اصلی
# ═══════════════════════════════════════════════════════════
class Settings(BaseSettings):
    """تنظیمات اپ — از .env خوانده می‌شود"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── App ───
    APP_NAME: str = "Trademun API"
    APP_VERSION: str = "6.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ─── Database ───
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'trademun.db'}"

    # ─── CORS (برای React) ───
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://trademun.pages.dev",
    ]

    # ─── Scheduler ───
    SCHEDULER_ENABLED: bool = True
    BACKTEST_INTERVAL_MINUTES: int = 30

    # ─── Cache TTL (ثانیه) ───
    CACHE_TTL_ANALYZE: int = 60
    CACHE_TTL_SCAN: int = 300

    # ─── نوبیتکس (فاز ۷) ───
    NOBITEX_API_KEY: str = ""

    # ─── Telegram Bot (فاز ۷) ───
    TELEGRAM_BOT_TOKEN: str = ""

    # ─── JWT (فاز ۷) ───
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════
settings = Settings()
