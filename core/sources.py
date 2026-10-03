"""
core/sources.py
سوییچ خودکار بین منابع — نسخه ۳.۰ (فقط صرافی‌های ایرانی)
============================================================
تغییرات نسخه ۳.۰:
  - اضافه bitpin, wallex
  - حذف global (yfinance)
  - سوییچ خودکار بین نوبیتکس/بیت‌پین/والکس
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# تشخیص منبع از روی نماد
# ═══════════════════════════════════════════════════════════
def detect_source_for_ticker(ticker: str) -> str:
    """تشخیص منبع از روی ticker"""
    if not ticker:
        return "nobitex"

    upper = ticker.upper()

    # ─── بورس تهران (فارسی) ───
    if not ticker[0].isascii():
        return "tsetmc"

    # ─── کریپتو تومانی/تتری ───
    if "-IRT" in upper or "-RLS" in upper:
        return "nobitex"
    if "-USD" in upper or "-USDT" in upper:
        return "nobitex"

    # ─── پیش‌فرض ───
    return "nobitex"


# ═══════════════════════════════════════════════════════════
# سوییچ خودکار
# ═══════════════════════════════════════════════════════════
def resolve_symbol_and_source(
    ticker: str,
    source: str,
) -> tuple[str, str, str]:
    """
    تعیین نماد و منبع نهایی.
    ─── صرافی کریپتو انتخاب‌شده همیشه حفظ می‌شه ───
    ─── فقط TSETMC با کریپتو قاطی نمی‌شه ───
    """
    if not ticker:
        return ticker, source, ""

    is_crypto = ticker[0].isascii() if ticker else True
    is_iranian_stock = not is_crypto

    # ═══ اگه نماد بورسی هست ولی صرافی کریپتو انتخاب شده ═══
    if is_iranian_stock and source in ("nobitex", "bitpin", "wallex", "abantether"):
        return ticker, "tsetmc", "🇮🇷 سوییچ به بورس تهران"

    # ═══ اگه نماد کریپتو هست ولی صرافی بورس انتخاب شده ═══
    if is_crypto and source == "tsetmc":
        return ticker, "nobitex", "🔄 سوییچ به نوبیتکس"

    # ═══ اگه کاربر global خواسته (منسوخ) ═══
    if source == "global":
        if is_iranian_stock:
            return ticker, "tsetmc", "🌍 → بورس تهران"
        return ticker, "nobitex", "🌍 → نوبیتکس"

    # ═══ در همه موارد دیگه، صرافی کاربر حفظ می‌شه ═══
    return ticker, source, ""


# ═══════════════════════════════════════════════════════════
# حل منبع
# ═══════════════════════════════════════════════════════════
def resolve_source(source: str) -> str:
    """نرمال‌سازی منبع"""
    valid = ["nobitex", "abantether", "bitpin", "wallex", "tsetmc"]
    return source if source in valid else "nobitex"


def is_symbol_available_in_source(ticker: str, source: str) -> bool:
    """چک می‌کنه نماد در منبع موجوده یا نه"""
    if not ticker:
        return False
    detected = detect_source_for_ticker(ticker)
    if detected == "tsetmc":
        return source == "tsetmc"
    return source in ("nobitex", "abantether", "bitpin", "wallex")


def get_default_symbol_for_source(source: str) -> str:
    """نماد پیش‌فرض هر منبع"""
    return {
        "nobitex": "BTC-USD",
        "abantether": "BTC-USD",
        "bitpin": "BTC-USD",
        "wallex": "BTC-USD",
        "tsetmc": "فولاد",
    }.get(source, "BTC-USD")


def get_source_info(source: str) -> dict:
    """اطلاعات منبع"""
    return {
        "nobitex": {
            "icon": "🟣",
            "short_name": "نوبیتکس",
            "full_name": "نوبیتکس",
        },
        "abantether": {
            "icon": "🔵",
            "short_name": "آبان‌تتر",
            "full_name": "آبان‌تتر",
        },
        "bitpin": {
            "icon": "🟢",
            "short_name": "بیت‌پین",
            "full_name": "بیت‌پین",
        },
        "wallex": {
            "icon": "🔵",
            "short_name": "والکس",
            "full_name": "والکس",
        },
        "tsetmc": {
            "icon": "🇮🇷",
            "short_name": "بورس تهران",
            "full_name": "بورس تهران",
        },
    }.get(source, {"icon": "•", "short_name": "—", "full_name": "—"})


__all__ = [
    "detect_source_for_ticker",
    "resolve_symbol_and_source",
    "resolve_source",
    "is_symbol_available_in_source",
    "get_default_symbol_for_source",
    "get_source_info",
]
