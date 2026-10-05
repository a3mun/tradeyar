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

from .contracts import is_planned_source

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
    if is_iranian_stock and source in ("nobitex", "bitpin", "wallex", "tabdeal"):
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
    """
    نرمال‌سازی منبع.

    ⚠️ صرافی‌های placeholder (رمزینکس، توبیت، بینگ‌ایکس)
       هنوز fetcher ندارند. اگر کسی آن‌ها را صدا بزند، به
       نوبیتکس fallback می‌شوند — همان رفتار قبلی برای منبع
       ناشناخته. این‌طوری کد جدید کرش نمی‌کند.
    """
    active = ["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]
    if source in active:
        return source

    if is_planned_source(source):
        logger.warning(
            f"[Sources] «{source}» هنوز پیاده‌سازی نشده (فاز ۷) "
            f"— استفاده از نوبیتکس"
        )
        return "nobitex"

    return "nobitex"


def is_symbol_available_in_source(ticker: str, source: str) -> bool:
    """چک می‌کنه نماد در منبع موجوده یا نه"""
    if not ticker:
        return False
    detected = detect_source_for_ticker(ticker)
    if detected == "tsetmc":
        return source == "tsetmc"
    return source in ("nobitex", "bitpin", "wallex", "tabdeal")


def get_default_symbol_for_source(source: str) -> str:
    """نماد پیش‌فرض هر منبع"""
    return {
        "nobitex": "BTC-USD",
        "bitpin": "BTC-USD",
        "wallex": "BTC-USD",
        "tabdeal": "BTC-USD",
        "tsetmc": "فولاد",
    }.get(source, "BTC-USD")


def get_source_info(source: str) -> dict:
    """
    اطلاعات منبع — شامل وضعیت «به‌زودی».

    Returns:
        dict با ``icon``, ``short_name``, ``full_name`` و
        ``planned`` (آیا هنوز پیاده‌سازی نشده).
    """
    if is_planned_source(source):
        return {
            "icon": "⏳",
            "short_name": {
                "ramzinex": "رمزینکس",
                "toobit": "توبیت",
                "bingx": "بینگ‌ایکس",
                "bit24": "بیت۲۴",
            }.get(source, source),
            "full_name": "به‌زودی",
            "planned": True,
            "active": False,
        }

    info = {
        "nobitex": {
            "icon": "🟣",
            "short_name": "نوبیتکس",
            "full_name": "نوبیتکس",
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
        "tabdeal": {
            "icon": "🟠",
            "short_name": "تبدیل",
            "full_name": "تبدیل (قیمت و عمق بازار)",
        },
        "tsetmc": {
            "icon": "🇮🇷",
            "short_name": "بورس تهران",
            "full_name": "بورس تهران",
        },
    }.get(source, {"icon": "•", "short_name": "—", "full_name": "—"})

    info.setdefault("planned", False)
    info.setdefault("active", True)
    return info


def get_all_sources_info() -> list[dict]:
    """
    لیست همه‌ی منابع با وضعیتشان — برای پر کردن SettingsPanel.

    Returns:
        list از ``{"value", "icon", "label", "planned", "active"}``
    """
    from .contracts import DataSource

    items = []
    for value in DataSource.all():
        if value == "global":
            continue  # ─── منسوخ ───
        info = get_source_info(value)
        items.append(
            {
                "value": value,
                "icon": info["icon"],
                "label": info["short_name"],
                "full_name": info["full_name"],
                "planned": info["planned"],
                "active": info["active"],
            }
        )
    return items


__all__ = [
    "detect_source_for_ticker",
    "resolve_symbol_and_source",
    "resolve_source",
    "is_symbol_available_in_source",
    "get_default_symbol_for_source",
    "get_source_info",
    "get_all_sources_info",
]
