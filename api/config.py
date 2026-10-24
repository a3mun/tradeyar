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

    # ─── CORS (برای فرانت + موبایل + production) ───
    CORS_ORIGINS: list[str] = [
        # ─── Development ───
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.7:3000",
        "http://localhost:5173",
        # ─── Production ───
        "https://trademun.ir",
        "https://www.trademun.ir",
        "https://trademun.pages.dev",
    ]

    # ─── Scheduler ───
    SCHEDULER_ENABLED: bool = True
    BACKTEST_INTERVAL_MINUTES: int = 5

    # ─── Cache TTL (ثانیه) ───
    CACHE_TTL_ANALYZE: int = 60
    CACHE_TTL_SCAN: int = 300

    # ─── نوبیتکس (فاز ۷) ───
    NOBITEX_API_KEY: str = ""
    NOBITEX_SECRET_KEY: str = ""

    # ─── Telegram Bot (فاز ۷) ───
    TELEGRAM_BOT_TOKEN: str = ""

    # ─── Admin API Key (باگ ۴) ───
    # عملیات مخرب مثل DELETE /backtest/reset با هدر X-API-Key محافظت می‌شود.
    # در .env با `openssl rand -hex 32` بساز. خالی = عملیات admin مسدود.
    ADMIN_API_KEY: str = ""

    # ─── JWT (فاز ۷) ───
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ─── JWT (فاز ۱۱) ───
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # ۷ روز

    # ─── Admin (فاز ۱۱) ───
    ADMIN_PHONES: str = "09129630901,09371069753"  # با کاما جدا

    # ─── فراز SMS (فاز ۱۱) ───
    FARAZ_API_KEY: str = ""
    FARAZ_PATTERN_CODE: str = ""  # کد پترن OTP
    FARAZ_SENDER: str = "+983000505"  # پیش‌فرض فراز

    # ─── پلن رایگان (فاز ۱۱) ───
    FREE_PLAN_DAYS: int = 3

    # ─── ارتباط ───
    CONTACT_TELEGRAM: str = "asemun_1993"
    CONTACT_BALE: str = "asemun_1993"

    # ─── پرداخت (فاز ۱۱) ───
    CARD_NUMBER: str = "5859-4710-2303-7983"  # شماره کارت خودت رو بذار
    CARD_HOLDER: str = "محمدمهدی"  # اسم صاحب کارت


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════
settings = Settings()
