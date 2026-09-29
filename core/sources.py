"""
core/sources.py
مدیریت منابع دیتا + سوییچ خودکار — نسخه ۲.۰
============================================================
تغییرات نسخه ۲.۰:
  - رفع باگ سوییچ خودکار (اولویت‌دهی بهتر)
  - اضافه detect_source_for_ticker (منبع ترجیحی هر نماد)
  - بهبود is_crypto_symbol (USDT-IRT درست تشخیص)
  - resolve_symbol_and_source پایدارتر
"""

from typing import Optional

from .contracts import DataSource, MarketType

# ═══════════════════════════════════════════════════════════
# منابع
# ═══════════════════════════════════════════════════════════
SOURCES: dict[str, dict] = {
    DataSource.GLOBAL.value: {
        "key": DataSource.GLOBAL.value,
        "icon": "🌍",
        "label": "جهانی",
        "full_name": "yfinance",
        "description": "سهام، فارکس، کالا، شاخص",
        "color": "#06b6d4",
        "default_symbol": "GC=F",
        "default_market_type": MarketType.FUTURES.value,
        "supports_symbols": "all",
        "priority": 10,
    },
    DataSource.NOBITEX.value: {
        "key": DataSource.NOBITEX.value,
        "icon": "🟣",
        "label": "نوبیتکس",
        "full_name": "Nobitex",
        "description": "کریپتو تتری — ۲۲۷ نماد",
        "color": "#a855f7",
        "default_symbol": "USDT-IRT",
        "default_market_type": MarketType.FUTURES.value,
        "supports_symbols": "crypto",
        "priority": 1,
    },
    DataSource.ABANTETHER.value: {
        "key": DataSource.ABANTETHER.value,
        "icon": "🔵",
        "label": "آبان‌تتر",
        "full_name": "AbanTether",
        "description": "قیمت لحظه‌ای کریپتو",
        "color": "#3b82f6",
        "default_symbol": "BTC-USD",
        "default_market_type": MarketType.SPOT.value,
        "supports_symbols": "crypto",
        "priority": 2,
    },
    DataSource.TSETMC.value: {
        "key": DataSource.TSETMC.value,
        "icon": "🇮🇷",
        "label": "بورس تهران",
        "full_name": "TSETMC",
        "description": "سهام بورس تهران",
        "color": "#10b981",
        "default_symbol": "فولاد",
        "default_market_type": MarketType.SPOT.value,
        "supports_symbols": "iran_stocks",
        "priority": 3,
    },
}


def get_source_info(source: str) -> dict:
    return SOURCES.get(source, SOURCES[DataSource.GLOBAL.value])


def get_all_sources() -> list[dict]:
    return list(SOURCES.values())


def get_source_keys() -> list[str]:
    return list(SOURCES.keys())


# ═══════════════════════════════════════════════════════════
# تشخیص نوع نماد
# ═══════════════════════════════════════════════════════════
def is_crypto_symbol(ticker: str) -> bool:
    """آیا نماد کریپتو هست؟ (دقیق‌تر)"""
    if not ticker:
        return False
    if ticker == "USDT-IRT":
        return True
    if ticker.endswith("-USD"):
        try:
            from .nobitex_fetcher import is_in_nobitex

            if is_in_nobitex(ticker):
                return True
        except Exception:
            pass
        try:
            from .abantether_fetcher import is_in_abantether

            if is_in_abantether(ticker):
                return True
        except Exception:
            pass
        return False
    return False


def is_iran_stock(ticker: str) -> bool:
    """آیا نماد بورس تهران هست؟"""
    if not ticker:
        return False
    from .market_lists import get_iran_stock_symbols

    return ticker in get_iran_stock_symbols()


def is_global_symbol(ticker: str) -> bool:
    """آیا نماد yfinance هست؟"""
    if not ticker:
        return False
    if is_crypto_symbol(ticker) or is_iran_stock(ticker):
        return False
    return True


def detect_symbol_type(ticker: str) -> str:
    """تشخیص دقیق نوع نماد"""
    if not ticker:
        return "unknown"

    # ─── بورس تهران ───
    if is_iran_stock(ticker):
        return "iran_stocks"

    # ─── کریپتو با -USD (فقط اگه در نوبیتکس یا آبان‌تتر باشه) ───
    if ticker.endswith("-USD"):
        # چک نوبیتکس
        try:
            from .nobitex_fetcher import is_in_nobitex

            if is_in_nobitex(ticker):
                return "crypto"
        except Exception:
            pass
        # چک آبان‌تتر
        try:
            from .abantether_fetcher import is_in_abantether

            if is_in_abantether(ticker):
                return "crypto"
        except Exception:
            pass
        # fallback: هر -USD دیگه → global
        return "global"

    # ─── USDT-IRT ویژه ───
    if ticker == "USDT-IRT":
        return "crypto"

    # ─── بقیه (طلا، سهام، ...) ───
    return "global"


def is_crypto_symbol(ticker: str) -> bool:
    """آیا نماد کریپتو هست؟"""
    if not ticker:
        return False
    if ticker == "USDT-IRT":
        return True
    if ticker.endswith("-USD"):
        # ← چک دقیق‌تر: فقط اگه در نوبیتکس یا آبان‌تتر باشه
        try:
            from .nobitex_fetcher import is_in_nobitex

            if is_in_nobitex(ticker):
                return True
        except Exception:
            pass
        try:
            from .abantether_fetcher import is_in_abantether

            if is_in_abantether(ticker):
                return True
        except Exception:
            pass
        return False  # ← اگه هیچ‌جا نبود، کریپتو نیست
    return False


# ═══════════════════════════════════════════════════════════
# سازگاری
# ═══════════════════════════════════════════════════════════
def is_symbol_available_in_source(ticker: str, source: str) -> bool:
    """آیا نماد در منبع موجوده؟"""
    if not ticker:
        return False

    source_info = SOURCES.get(source)
    if not source_info:
        return False

    supports = source_info.get("supports_symbols", "all")

    # ─── global: همه نمادهای yfinance (به‌جز بورس تهران) ───
    if supports == "all":
        if is_iran_stock(ticker):
            return False
        # USDT-IRT در yfinance نیست
        if ticker == "USDT-IRT":
            return False
        return True

    # ─── crypto: فقط کریپتو ───
    if supports == "crypto":
        if not is_crypto_symbol(ticker):
            return False

        if source == DataSource.NOBITEX.value:
            try:
                from .nobitex_fetcher import is_in_nobitex

                return is_in_nobitex(ticker)
            except Exception:
                return False
        elif source == DataSource.ABANTETHER.value:
            try:
                from .abantether_fetcher import map_symbol_to_abantether

                return map_symbol_to_abantether(ticker) is not None
            except Exception:
                return False

        return True

    # ─── iran_stocks ───
    if supports == "iran_stocks":
        return is_iran_stock(ticker)

    return False


# ═══════════════════════════════════════════════════════════
# منبع ترجیحی برای هر نماد
# ═══════════════════════════════════════════════════════════
def detect_source_for_ticker(ticker: str) -> str:
    """بهترین منبع برای یه نماد"""
    if not ticker:
        return DataSource.GLOBAL.value

    # ─── ویژه: USDT-IRT ───
    if ticker == "USDT-IRT":
        return DataSource.NOBITEX.value

    # ─── بورس تهران ───
    if is_iran_stock(ticker):
        return DataSource.TSETMC.value

    # ─── کریپتو ───
    if is_crypto_symbol(ticker):
        # اول نوبیتکس
        try:
            from .nobitex_fetcher import is_in_nobitex

            if is_in_nobitex(ticker):
                return DataSource.NOBITEX.value
        except Exception:
            pass
        return DataSource.GLOBAL.value

    # ─── بقیه (طلا، نفت، سهام آمریکا، فارکس) ───
    return DataSource.GLOBAL.value


# ═══════════════════════════════════════════════════════════
# resolve_source (سوییچ خودکار)
# ═══════════════════════════════════════════════════════════
def resolve_source(ticker: str, preferred: Optional[str] = None) -> str:
    """
    منبع مناسب برای یه نماد.

    Args:
        ticker: نماد
        preferred: منبع ترجیحی (اگه سازگار باشه، ترجیح داده می‌شه)
    """
    if not ticker:
        return DataSource.GLOBAL.value

    # اگه preferred سازگار، برگردون
    if preferred and is_symbol_available_in_source(ticker, preferred):
        return preferred

    # منبع ترجیحی بر اساس نوع نماد
    return detect_source_for_ticker(ticker)


def resolve_symbol_and_source(
    ticker: str,
    current_source: str,
) -> tuple[str, str, Optional[str]]:
    """
    تعیین نماد و منبع نهایی + پیام سوییچ.

    Returns:
        (final_ticker, final_source, switch_message)
    """
    if not ticker:
        return ticker, current_source, None

    # اگه سازگار، بدون سوییچ
    if is_symbol_available_in_source(ticker, current_source):
        return ticker, current_source, None

    # پیدا کردن منبع جدید
    new_source = detect_source_for_ticker(ticker)

    if not new_source or new_source == current_source:
        return ticker, current_source, None

    old_info = get_source_info(current_source)
    new_info = get_source_info(new_source)

    message = (
        f"⚠️ نماد «{ticker}» در منبع {old_info['icon']} {old_info['label']} "
        f"موجود نیست.\n"
        f"🔄 به منبع {new_info['icon']} {new_info['label']} سوییچ شد."
    )

    return ticker, new_source, message


# ═══════════════════════════════════════════════════════════
# پیش‌فرض‌ها
# ═══════════════════════════════════════════════════════════
def get_default_symbol_for_source(source: str) -> str:
    return get_source_info(source).get("default_symbol", "GC=F")


def get_default_market_type_for_source(source: str) -> str:
    return get_source_info(source).get("default_market_type", MarketType.SPOT.value)


__all__ = [
    "SOURCES",
    "get_source_info",
    "get_all_sources",
    "get_source_keys",
    "is_crypto_symbol",
    "is_iran_stock",
    "is_global_symbol",
    "detect_symbol_type",
    "detect_source_for_ticker",
    "is_symbol_available_in_source",
    "resolve_source",
    "resolve_symbol_and_source",
    "get_default_symbol_for_source",
    "get_default_market_type_for_source",
]


if __name__ == "__main__":
    print("=" * 60)
    print("تست core/sources.py — نسخه ۲.۰")
    print("=" * 60)
    print()
    tests = [
        ("USDT-IRT", "nobitex"),
        ("GC=F", "nobitex"),  # باید به global سوییچ
        ("BTC-USD", "nobitex"),
        ("BTC-USD", "global"),
        ("PAXG-USD", "nobitex"),
        ("فولاد", "global"),  # باید به tsetmc سوییچ
    ]
    for t, s in tests:
        ft, fs, msg = resolve_symbol_and_source(t, s)
        icon = "🔄" if msg else "✅"
        print(f"   {icon} {t:15} از {s:10} → {fs}")
    print()
    print("[OK] تست کامل شد.")
