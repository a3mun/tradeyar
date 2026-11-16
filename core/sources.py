"""
core/sources.py
سوییچ خودکار بین منابع — نسخه ۳.۲ (اضافه شد xaus)
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

    # 🔴 فارکس، کالا، شاخص (Biquote)
    if upper in (
        "XAU-USD",
        "XAG-USD",
        "USOIL-USD",
        "UKOIL-USD",
        "DXY-USD",
        "US500-USD",
        "US30-USD",
        "USTEC-USD",
        "EUR-USD",
        "DE30-USD",
    ):
        return "forex"

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
    """تعیین نماد و منبع نهایی"""
    if not ticker:
        return ticker, source, ""

    is_crypto = ticker[0].isascii() if ticker else True
    is_iranian_stock = not is_crypto
    upper = ticker.upper()

    # 🔴 فارکس/کالا/شاخص → همیشه forex
    if upper in (
        "XAU-USD",
        "XAG-USD",
        "USOIL-USD",
        "UKOIL-USD",
        "DXY-USD",
        "US500-USD",
        "US30-USD",
        "USTEC-USD",
        "EUR-USD",
        "DE30-USD",
    ):
        return ticker, "forex", "🌍 سوییچ به فارکس"

    # ═══ اگه نماد بورسی هست ولی صرافی کریپتو/فارکس انتخاب شده ═══
    if is_iranian_stock and source in (
        "nobitex",
        "bitpin",
        "wallex",
        "tabdeal",
        "forex",
    ):
        return ticker, "tsetmc", "🇮🇷 سوییچ به بورس تهران"

    # ═══ اگه نماد کریپتو هست ولی صرافی بورس/فارکس انتخاب شده ═══
    if is_crypto and source in ("tsetmc", "forex"):
        return ticker, "nobitex", "🔄 سوییچ به نوبیتکس"

    if source == "global":
        if is_iranian_stock:
            return ticker, "tsetmc", "🌍 → بورس تهران"
        return ticker, "nobitex", "🌍 → نوبیتکس"

    return ticker, source, ""


# ═══════════════════════════════════════════════════════════
# حل منبع
# ═══════════════════════════════════════════════════════════
def resolve_source(source: str) -> str:
    active = ["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc", "forex"]
    if source in active:
        return source

    if is_planned_source(source):
        logger.warning(f"[Sources] «{source}» هنوز پیاده‌سازی نشده")
        return "nobitex"

    return "nobitex"


def is_symbol_available_in_source(ticker: str, source: str) -> bool:
    if not ticker:
        return False
    detected = detect_source_for_ticker(ticker)
    if detected == "tsetmc":
        return source == "tsetmc"
    if detected == "forex":
        return source == "forex"
    return source in ("nobitex", "bitpin", "wallex", "tabdeal")


def get_default_symbol_for_source(source: str) -> str:
    return {
        "nobitex": "BTC-USD",
        "bitpin": "BTC-USD",
        "wallex": "BTC-USD",
        "tabdeal": "BTC-USD",
        "tsetmc": "فولاد",
        "forex": "XAU-USD",
    }.get(source, "BTC-USD")


def get_source_info(source: str) -> dict:
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
            "supports_analysis": False,
        }

    info = {
        "nobitex": {
            "icon": "🟣",
            "short_name": "نوبیتکس",
            "full_name": "نوبیتکس",
            "supports_analysis": True,
        },
        "bitpin": {
            "icon": "🟢",
            "short_name": "بیت‌پین",
            "full_name": "بیت‌پین",
            "supports_analysis": True,
        },
        "wallex": {
            "icon": "🔵",
            "short_name": "والکس",
            "full_name": "والکس",
            "supports_analysis": True,
        },
        "tabdeal": {
            "icon": "🟠",
            "short_name": "تبدیل",
            "full_name": "تبدیل (فقط قیمت و عمق بازار)",
            "supports_analysis": False,
        },
        "tsetmc": {
            "icon": "🇮🇷",
            "short_name": "بورس تهران",
            "full_name": "بورس تهران",
            "supports_analysis": True,
        },
        # 🔴 جدید
        "forex": {
            "icon": "🌍",
            "short_name": "فارکس",
            "full_name": "Biquote — فارکس، کالا، شاخص‌ها",
            "supports_analysis": True,
        },
    }.get(
        source,
        {"icon": "•", "short_name": "—", "full_name": "—", "supports_analysis": False},
    )

    info.setdefault("planned", False)
    info.setdefault("active", True)
    return info


def source_supports_analysis(source: str) -> bool:
    return bool(get_source_info(source).get("supports_analysis", False))


def get_all_sources_info() -> list[dict]:
    from .contracts import DataSource

    items = []
    for value in DataSource.all():
        if value == "global":
            continue
        info = get_source_info(value)
        items.append(
            {
                "value": value,
                "icon": info["icon"],
                "label": info["short_name"],
                "full_name": info["full_name"],
                "planned": info["planned"],
                "active": info["active"],
                "supports_analysis": info["supports_analysis"],
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
    "source_supports_analysis",
]
