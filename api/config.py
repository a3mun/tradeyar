"""
api/config.py
تنظیمات مرکزی API
"""

from pathlib import Path
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
        "http://192.168.1.7:3000",
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

    ADMIN_API_KEY: str = ""

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    ADMIN_PHONES: str = "09129630901"

    FARAZ_API_KEY: str = ""
    FARAZ_PATTERN_CODE: str = ""
    FARAZ_SENDER: str = "+983000505"
    FREE_PLAN_DAYS: int = 3

    CONTACT_TELEGRAM: str = "asemun_1993"
    CONTACT_BALE: str = "asemun_1993"
    CARD_NUMBER: str = "5859-4710-1084-0910"
    CARD_HOLDER: str = "محمدمهدی"


settings = Settings()
