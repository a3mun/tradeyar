"""
core/market_lists.py
لیست نمادهای هر بازار — نسخه ۵.۰
============================================================
تغییرات نسخه ۵.۰:
  - اضافه `get_top_symbols_by_volume` (Top 50 per صرافی)
  - کش ۱ ساعته برای لیست‌های تازه
"""

import json
from pathlib import Path
from typing import Optional

TSETMC_CACHE = Path("data/tsetmc_symbols.json")


# ═══════════════════════════════════════════════════════════
# دسته‌بندی
# ═══════════════════════════════════════════════════════════
MARKET_CATEGORIES = {
    "crypto": {
        "key": "crypto",
        "name": "💰 کریپتو",
        "icon": "💰",
        "description": "ارزهای دیجیتال",
        "source": "nobitex",
        "tickers": [
            ("BTC-USD", "بیت‌کوین"),
            ("ETH-USD", "اتریوم"),
            ("SOL-USD", "سولانا"),
            ("XRP-USD", "ریپل"),
            ("BNB-USD", "بایننس کوین"),
            ("ADA-USD", "کاردانو"),
            ("DOGE-USD", "دوج‌کوین"),
            ("TON-USD", "تون‌کوین"),
            ("AVAX-USD", "آوالانچ"),
            ("DOT-USD", "پولکادات"),
            ("MATIC-USD", "ماتیک"),
            ("LINK-USD", "چین‌لینک"),
            ("LTC-USD", "لایت‌کوین"),
            ("ATOM-USD", "کازماس"),
            ("NEAR-USD", "نیر"),
            ("TRX-USD", "ترون"),
            # تومانی
            ("USDT-IRT", "تتر/تومان"),
            ("BTC-IRT", "بیت‌کوین/تومان"),
            ("ETH-IRT", "اتریوم/تومان"),
            ("PAXG-IRT", "پکس‌گلد/تومان"),
        ],
    },
    "iran_stocks": {
        "key": "iran_stocks",
        "name": "🇮🇷 بورس تهران",
        "icon": "🇮🇷",
        "description": "سهام بورس تهران",
        "source": "tsetmc",
        "tickers": [
            ("فولاد", "فولاد مبارکه"),
            ("فملی", "ملی صنایع مس"),
            ("شپنا", "پالایش نفت اصفهان"),
            ("شتران", "پالایش نفت تهران"),
            ("خودرو", "ایران خودرو"),
            ("خساپا", "سایپا"),
            ("وبملت", "بانک ملت"),
            ("وتجارت", "بانک تجارت"),
            ("همراه", "همراه اول"),
            ("اخابر", "مخابرات ایران"),
            ("شبندر", "پالایش بندرعباس"),
            ("کگل", "گل گهر"),
            ("فارس", "پتروشیمی خلیج فارس"),
            ("نوری", "پتروشیمی نوری"),
            ("شستا", "سرمایه‌گذاری تأمین"),
            ("وغدیر", "سرمایه‌گذاری غدیر"),
        ],
    },
}

# ═══════════════════════════════════════════════════════════
# صندوق‌های مهم بورس
# ═══════════════════════════════════════════════════════════
IRAN_FUNDS = {
    "عیار": "صندوق طلای عیار مفید",
    "طلا": "صندوق کالای پارسیان",
    "گنج": "صندوق سیمای کاردان",
    "کهربا": "صندوق کالای کهربا",
    "مثقال": "صندوق کالای آگاه",
    "زر": "صندوق طلای زر",
    "ناب": "صندوق طلای ناب",
    "اهرم": "صندوق اهرمی کاریزما",
    "موج": "صندوق اهرمی موج فیروزه",
    "توان": "صندوق اهرمی توان",
    "کارا": "صندوق سهامی کارا",
    "پالایش": "صندوق پالایشی یکم",
    "دارا یکم": "صندوق دارا یکم",
    "کیان": "صندوق سهامی کیان",
}


# ═══════════════════════════════════════════════════════════
# توابع پایه
# ═══════════════════════════════════════════════════════════
def get_category(category_key: str) -> dict | None:
    return MARKET_CATEGORIES.get(category_key)


def get_category_tickers(category_key: str) -> list[tuple]:
    cat = MARKET_CATEGORIES.get(category_key)
    if not cat:
        return []
    return cat.get("tickers", [])


def get_all_categories() -> dict:
    return MARKET_CATEGORIES


def get_categories_with_tickers() -> dict:
    return {k: v for k, v in MARKET_CATEGORIES.items() if v.get("tickers")}


def get_category_keys() -> list[str]:
    return list(MARKET_CATEGORIES.keys())


def get_category_name(category_key: str) -> str:
    cat = MARKET_CATEGORIES.get(category_key)
    return cat.get("name", "") if cat else ""


def get_category_source(category_key: str) -> str:
    cat = MARKET_CATEGORIES.get(category_key)
    return cat.get("source", "global") if cat else "global"


def _is_valid_stock_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    if len(symbol) < 2:
        return False
    if symbol.endswith("ح"):
        return False
    if symbol[-1].isdigit():
        return False
    if "ح" in symbol and symbol.strip().endswith("ح"):
        return False
    return True


def _load_tsetmc_cache() -> list[str]:
    if not TSETMC_CACHE.exists():
        return []
    try:
        with open(TSETMC_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_tsetmc_cache(symbols: list[str]) -> None:
    try:
        TSETMC_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(TSETMC_CACHE, "w", encoding="utf-8") as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MarketLists] خطا در ذخیره TSETMC: {e}")


def get_iran_stock_symbols() -> list[str]:
    cat = MARKET_CATEGORIES.get("iran_stocks", {})
    static = [t[0] for t in cat.get("tickers", [])]

    full_file = Path("data/tsetmc_symbols_full.json")
    full_syms = []
    if full_file.exists():
        try:
            with open(full_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    full_syms = list(data.keys())
                elif isinstance(data, list):
                    full_syms = data
        except Exception as e:
            print(f"[MarketLists] خطا در خواندن tsetmc_symbols_full: {e}")

    cached = _load_tsetmc_cache()

    all_syms = set(static + full_syms + cached)
    all_syms.update(IRAN_FUNDS.keys())
    filtered = [s for s in all_syms if _is_valid_stock_symbol(s)]

    return sorted(filtered)


def get_iran_stock_map() -> dict:
    cat = MARKET_CATEGORIES.get("iran_stocks", {})
    static_map = {t[0]: t[1] for t in cat.get("tickers", [])}

    full_file = Path("data/tsetmc_symbols_full.json")
    if full_file.exists():
        try:
            with open(full_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for sym, info in data.items():
                        if sym not in static_map:
                            if isinstance(info, dict):
                                static_map[sym] = info.get("name_fa", sym)
                            else:
                                static_map[sym] = str(info)
        except Exception as e:
            print(f"[MarketLists] خطا در خواندن map: {e}")

    for sym, name in IRAN_FUNDS.items():
        if sym not in static_map:
            static_map[sym] = name

    filtered_map = {s: n for s, n in static_map.items() if _is_valid_stock_symbol(s)}

    return filtered_map


def get_crypto_symbols() -> list[str]:
    cat = MARKET_CATEGORIES.get("crypto", {})
    return [t[0] for t in cat.get("tickers", [])]


def fetch_tsetmc_all_symbols() -> list[str]:
    cached = _load_tsetmc_cache()
    if len(cached) >= 100:
        return cached

    try:
        import requests

        url = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/%D9%81"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return cached

        data = r.json()
        instruments = data.get("instrumentSearch", [])
        symbols = []
        for inst in instruments:
            sym = inst.get("lVal18AFC", "")
            if sym:
                symbols.append(sym)

        if symbols:
            _save_tsetmc_cache(symbols)
        return symbols
    except Exception as e:
        print(f"[MarketLists] خطا در fetch TSETMC: {e}")
        return cached


def _symbol_exists_in_source(ticker: str, source: str) -> bool:
    """
    آیا این نماد توی صرافی وجود داره؟ (بدون درخواست شبکه)

    برای `tsetmc` → همیشه False (چون کریپتو نیست)
    برای بقیه → چک کردن از فایل‌های محلی صرافی
    """
    if not ticker:
        return False
    if source == "tsetmc":
        return False

    try:
        if source == "nobitex":
            from core.nobitex_fetcher import is_in_nobitex

            return is_in_nobitex(ticker)
        if source == "bitpin":
            from core.bitpin_fetcher import map_symbol_to_bitpin

            return bool(map_symbol_to_bitpin(ticker))
        if source == "wallex":
            from core.wallex_fetcher import map_symbol_to_wallex

            return bool(map_symbol_to_wallex(ticker))
        if source == "tabdeal":
            from core.tabdeal_fetcher import is_in_tabdeal

            return is_in_tabdeal(ticker)
    except Exception:
        pass
    return False


# ═══════════════════════════════════════════════════════════
# ۱۲. Top N نماد پرحجم per صرافی (نسخه ۵.۰)
# ═══════════════════════════════════════════════════════════
# ═══ چرا لازم است ═══
# پیش‌تر `MARKET_CATEGORIES["crypto"]["tickers"]` فقط ۲۰ نماد
# ثابت داشت. نتیجه: اسکن ۹۰٪ بازار ایران رو نمی‌دید.
#
# حالا از هر صرافی Top 50 پرحجم رو می‌گیریم.
# کش ۱ ساعته → بدون درخواست تکراری.

_SYMBOL_LIST_TTL = 3600  # ۱ ساعت


# ═══════════════════════════════════════════════════════════
# نمادهای ثابت — همیشه در لیست اسکن (نسخه ۵.۱)
# ═══════════════════════════════════════════════════════════
# ═══ چرا ثابت ═══
# نمادهای پرطرفدار (BTC, ETH, SOL) گاهی توی top 50 حجم
# هستن، گاهی نه. اگه توی top نباشن، کاربر تعجب می‌کنه
# چرا اسکنر BTC رو نمی‌بینه.
#
# راه‌حل: این‌ها **همیشه** اول لیستن، بقیه از top حجم میان.
_PINNED_SYMBOLS: list[tuple[str, str]] = [
    ("BTC-USD", "بیت‌کوین"),
    ("ETH-USD", "اتریوم"),
    ("SOL-USD", "سولانا"),
    ("XRP-USD", "ریپل"),
    ("BNB-USD", "بایننس کوین"),
    ("DOGE-USD", "دوج‌کوین"),
    ("ADA-USD", "کاردانو"),
    ("PAXG-USD", "پکس گلد"),
]


def get_top_symbols_by_volume(
    source: str,
    limit: int = 50,
) -> list[tuple[str, str]]:
    """
    Top N نماد پرحجم یک صرافی.

    Args:
        source: ``"nobitex"`` | ``"bitpin"`` | ``"wallex"`` | ``"tabdeal"``
        limit: حداکثر تعداد

    Returns:
        لیست ``[(ticker, name), ...]`` مرتب‌شده بر اساس حجم نزولی.
        اگه خطا داد → لیست ثابت fallback.
    """
    src = (source or "").lower()

    # ─── کش (lazy import تا circular نشه) ───
    try:
        from services.cache import data_cache

        cache_key = f"top_symbols:{src}:{limit}"
        cached = data_cache.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        data_cache = None
        cache_key = ""

    result: list[tuple[str, str]] = []

    # ═══ اول: نمادهای ثابت (pinned) ═══
    # ─── فقط اونایی که توی صرافی وجود دارن ───
    pinned: list[tuple[str, str]] = []
    for t, n in _PINNED_SYMBOLS:
        if _symbol_exists_in_source(t, src):
            pinned.append((t, n))

    # ═══ دوم: بقیه از top حجم ═══
    remaining = max(0, limit - len(pinned))

    try:
        if src == "nobitex":
            dynamic = _top_symbols_nobitex(remaining)
        elif src == "bitpin":
            dynamic = _top_symbols_bitpin(remaining)
        elif src == "wallex":
            dynamic = _top_symbols_wallex(remaining)
        elif src == "tabdeal":
            dynamic = _top_symbols_tabdeal(remaining)
        else:
            dynamic = []
    except Exception as e:
        print(f"[MarketLists] خطا در top symbols {src}: {e}")
        dynamic = []

    # ═══ ادغام (pinned اول، بدون تکراری) ═══
    seen: set[str] = {t for t, _ in pinned}
    result = list(pinned)
    for t, n in dynamic:
        if t in seen:
            continue
        seen.add(t)
        result.append((t, n))
        if len(result) >= limit:
            break

    # ─── fallback: اگه خالی بود، لیست ثابت ───
    if not result:
        result = _fallback_symbols(limit)

    # ─── کش کن ───
    if result and data_cache is not None:
        try:
            data_cache.set(cache_key, result, _SYMBOL_LIST_TTL)
        except Exception:
            pass

    return result


def _name_for(ticker: str) -> str:
    """نام فارسی نماد از contracts.SYMBOLS — با lazy import"""
    try:
        from core.contracts import SYMBOLS

        return SYMBOLS.get(ticker, ticker)
    except Exception:
        return ticker


def _top_symbols_nobitex(limit: int) -> list[tuple[str, str]]:
    """Top نمادهای نوبیتکس — بر اساس volume_24h"""
    from core.nobitex_fetcher import (
        fetch_all_nobitex_symbols,
        map_nobitex_to_symbol,
    )

    usdt_list = fetch_all_nobitex_symbols(dst_currency="usdt")[:limit]
    irt_limit = max(10, limit // 3)
    irt_list = fetch_all_nobitex_symbols(dst_currency="rls")[:irt_limit]

    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for s in usdt_list + irt_list:
        symbol_nob = s.get("symbol", "")
        ticker = map_nobitex_to_symbol(symbol_nob)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        out.append((ticker, _name_for(ticker)))

    return out[:limit]


def _top_symbols_bitpin(limit: int) -> list[tuple[str, str]]:
    """Top نمادهای بیت‌پین — بر اساس volume"""
    import requests

    from core.bitpin_fetcher import (
        BASE_URL,
        HEADERS,
        TIMEOUT,
        map_bitpin_to_symbol,
    )

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/mkt/tickers/",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[MarketLists] bitpin tickers: {e}")
        return []

    if not isinstance(data, list):
        return []

    items: list[dict] = []
    for item in data:
        sym = item.get("symbol", "")
        if not sym or not sym.upper().endswith("_USDT"):
            continue
        try:
            vol = float(item.get("volume") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        items.append({"symbol": sym, "volume": vol})

    items.sort(key=lambda x: -x["volume"])

    out: list[tuple[str, str]] = []
    for item in items[:limit]:
        ticker = map_bitpin_to_symbol(item["symbol"])
        if not ticker:
            continue
        out.append((ticker, _name_for(ticker)))

    return out


def _top_symbols_wallex(limit: int) -> list[tuple[str, str]]:
    """Top نمادهای والکس — بر اساس 24h_volume"""
    import requests

    from core.wallex_fetcher import (
        BASE_URL,
        HEADERS,
        TIMEOUT,
        map_wallex_to_symbol,
    )

    try:
        r = requests.get(
            f"{BASE_URL}/v1/markets",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[MarketLists] wallex markets: {e}")
        return []

    symbols = data.get("result", {}).get("symbols", {})
    if not isinstance(symbols, dict):
        return []

    items: list[dict] = []
    for sym, info in symbols.items():
        if not sym.upper().endswith("USDT"):
            continue
        stats = info.get("stats", {}) or {}
        try:
            vol = float(stats.get("24h_volume") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        items.append({"symbol": sym, "volume": vol})

    items.sort(key=lambda x: -x["volume"])

    out: list[tuple[str, str]] = []
    for item in items[:limit]:
        ticker = map_wallex_to_symbol(item["symbol"])
        if not ticker:
            continue
        out.append((ticker, _name_for(ticker)))

    return out


def _top_symbols_tabdeal(limit: int) -> list[tuple[str, str]]:
    """Top نمادهای تبدیل — از exchangeInfo (بدون حجم)"""
    try:
        from core.tabdeal_fetcher import _load_exchange_info  # noqa: SLF001

        data = _load_exchange_info()
    except Exception as e:
        print(f"[MarketLists] tabdeal exchangeInfo: {e}")
        return []

    if not isinstance(data, list):
        return []

    out: list[tuple[str, str]] = []
    for m in data:
        if m.get("status") != "TRADING":
            continue
        base = m.get("baseAsset", "").upper()
        quote = m.get("quoteAsset", "").upper()
        if quote != "USDT" or not base:
            continue
        ticker = f"{base}-USD"
        out.append((ticker, _name_for(ticker)))

    return out[:limit]


def _fallback_symbols(limit: int) -> list[tuple[str, str]]:
    """لیست ثابت fallback"""
    cat = MARKET_CATEGORIES.get("crypto", {})
    tickers = cat.get("tickers", [])[:limit]
    return [(t[0], t[1]) for t in tickers]


# ═══════════════════════════════════════════════════════════
# exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "MARKET_CATEGORIES",
    "get_category",
    "get_category_tickers",
    "get_all_categories",
    "get_categories_with_tickers",
    "get_category_keys",
    "get_category_name",
    "get_category_source",
    "get_iran_stock_symbols",
    "get_iran_stock_map",
    "get_crypto_symbols",
    "fetch_tsetmc_all_symbols",
    "get_top_symbols_by_volume",
]


if __name__ == "__main__":
    print("=" * 60)
    print("تست core/market_lists.py — نسخه ۵.۰")
    print("=" * 60)
    for key, cat in MARKET_CATEGORIES.items():
        count = len(cat.get("tickers", []))
        print(f"   {cat['icon']} {cat['name']:20} — {count} نماد")
    print()
    print(f"نمادهای TSETMC (cache): {len(_load_tsetmc_cache())}")
    print()
    # ─── تست top symbols ───
    print("Top 5 نوبیتکس:")
    for t, n in get_top_symbols_by_volume("nobitex", limit=5):
        print(f"   {t} — {n}")
