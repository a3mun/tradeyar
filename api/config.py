"""
api/config.py
تنظیمات مرکزی API
"""

from pathlib import Path
import logging
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


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
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'trademun.db'}"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "https://trademun.ir",
        "https://www.trademun.ir",
        "https://trademun.pages.dev",
    ]

    SCHEDULER_ENABLED: bool = True
    BACKTEST_INTERVAL_MINUTES: int = 5
    CACHE_TTL_ANALYZE: int = 60
    CACHE_TTL_SCAN: int = 300

    NOBITEX_API_KEY: str = ""
    NOBITEX_SECRET_KEY: str = ""

    # ─── تلگرام ───
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    # ─── بله ───
    BALE_BOT_TOKEN: str = ""
    BALE_CHAT_ID: str = ""

    DISABLE_NOTIFICATIONS: str = "false"  # یا bool = False

    ADMIN_API_KEY: str = ""

    # 🔒 قفل دسترسی API/WebSocket (ورود + اشتراک معتبر یا دوره رایگان).
    # پیش‌فرض روشن (fail-closed): اگر .env گم شد یا ست نشد، API باز نمی‌ماند.
    # برای توسعه‌ی لوکال بدون ورود، صراحتاً ENFORCE_AUTH=false بگذارید.
    ENFORCE_AUTH: bool = True

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    ADMIN_PHONES: str = ""  # مثال: "0912xxxxxxx,0935xxxxxxx" — از .env بخوان

    FARAZ_API_KEY: str = ""
    FARAZ_PATTERN_CODE: str = ""
    FARAZ_PATTERN_NEW_USER: str = "4eoqoCFhwJ"  # 🔴 پترن اطلاع‌رسانی ثبت‌نام
    FARAZ_SENDER: str = "+983000505"
    FREE_PLAN_DAYS: int = 3

    CONTACT_TELEGRAM: str = "asemun_1993"
    CONTACT_BALE: str = "asemun_1993"
    CARD_NUMBER: str = "5859-4710-1084-0910"

    # 🔴 تنظیمات زیبال
    ZIBAL_MERCHANT: str
    # ZIBAL_CALLBACK_URL: str = "http://127.0.0.1:8001/subscription/verify-zibal"  # لوکال
    ZIBAL_CALLBACK_URL: str = (
        "https://api.trademun.ir/subscription/verify-zibal"  # سرور
    )
    # 🔴 آدرس فرانت برای ریدایرکت
    # FRONTEND_URL: str = "http://localhost:3000"  # لوکال
    FRONTEND_URL: str = "https://trademun.ir"  # سرور

    @model_validator(mode="after")
    def _check_jwt_secret(self):
        weak = self.JWT_SECRET == "change-me-in-production" or len(self.JWT_SECRET) < 32
        if weak:
            msg = "JWT_SECRET ضعیف/پیش‌فرض است. با `openssl rand -hex 32` یک مقدار قوی در .env بگذارید."
            if self.DEBUG:
                logging.getLogger(__name__).warning("⚠️ " + msg)
            else:
                raise ValueError(msg)
        return self


settings = Settings()
