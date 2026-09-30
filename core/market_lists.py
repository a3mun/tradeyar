"""
core/market_lists.py
لیست نمادهای هر بازار — نسخه ۴.۰
============================================================
تغییرات نسخه ۴.۰:
  - اضافه fetch_tsetmc_all_symbols (دریافت ۵۰۰+ نماد از API)
  - کش فایل برای نمادهای TSETMC
  - اضافه نمادهای بیشتر به iran_stocks
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
        ],
    },
    "forex": {
        "key": "forex",
        "name": "💱 فارکس",
        "icon": "💱",
        "description": "جفت‌ارزها",
        "source": "global",
        "tickers": [
            ("EURUSD=X", "یورو/دلار"),
            ("GBPUSD=X", "پوند/دلار"),
            ("USDJPY=X", "دلار/ین"),
            ("AUDUSD=X", "استرالیا/دلار"),
            ("USDCAD=X", "دلار/کانادا"),
            ("USDCHF=X", "دلار/فرانک"),
            ("NZDUSD=X", "نیوزلند/دلار"),
            ("EURGBP=X", "یورو/پوند"),
            ("EURJPY=X", "یورو/ین"),
            ("GBPJPY=X", "پوند/ین"),
            ("XAUUSD=X", "طلا/دلار"),
            ("XAGUSD=X", "نقره/دلار"),
        ],
    },
    "us_stocks": {
        "key": "us_stocks",
        "name": "📈 سهام آمریکا",
        "icon": "📈",
        "description": "سهام‌های برتر آمریکا",
        "source": "global",
        "tickers": [
            ("AAPL", "اپل"),
            ("TSLA", "تسلا"),
            ("NVDA", "انویدیا"),
            ("MSFT", "مایکروسافت"),
            ("GOOGL", "گوگل"),
            ("AMZN", "آمازون"),
            ("META", "متا"),
            ("NFLX", "نتفلیکس"),
            ("AMD", "AMD"),
            ("INTC", "اینتل"),
            ("JPM", "جی‌پی مورگان"),
            ("V", "ویزا"),
            ("DIS", "دیزنی"),
            ("BA", "بوئینگ"),
            ("XOM", "اکسون‌موبیل"),
            ("KO", "کوکاکولا"),
            ("PEP", "پپسی"),
            ("WMT", "وال‌مارت"),
            ("JNJ", "جانسون"),
            ("PG", "پروکتر"),
            ("CVX", "شورون"),
            ("HD", "هوم دیپو"),
            ("MA", "مسترکارت"),
            ("BAC", "بانک آو امریکا"),
        ],
    },
    "commodities": {
        "key": "commodities",
        "name": "🥇 کالا",
        "icon": "🥇",
        "description": "طلا، نقره، نفت",
        "source": "global",
        "tickers": [
            ("GC=F", "طلا (آتی)"),
            ("SI=F", "نقره"),
            ("BZ=F", "نفت برنت"),
            ("CL=F", "نفت WTI"),
            ("NG=F", "گاز طبیعی"),
            ("HG=F", "مس"),
            ("PL=F", "پلاتین"),
            ("PA=F", "پالادیوم"),
            ("ZC=F", "ذرت"),
            ("ZW=F", "گندم"),
            ("ZS=F", "سویا"),
            ("KC=F", "قهوه"),
        ],
    },
    "indices": {
        "key": "indices",
        "name": "📊 شاخص‌ها",
        "icon": "📊",
        "description": "شاخص‌های جهانی",
        "source": "global",
        "tickers": [
            ("^GSPC", "S&P 500"),
            ("^IXIC", "نزدک"),
            ("^DJI", "داو جونز"),
            ("^VIX", "VIX (ترس)"),
            ("^FTSE", "FTSE 100"),
            ("^GDAXI", "DAX آلمان"),
            ("^N225", "نیکی ۲۲۵"),
            ("^HSI", "هنگ‌سنگ"),
            ("DX-Y.NYB", "شاخص دلار"),
            ("^TNX", "بازده ۱۰ ساله"),
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
            ("وپارس", "بانک پارسیان"),
            ("تاپیکو", "تأمین نفت و گاز"),
            ("شاوان", "پالایش لاوان"),
            ("اپال", "پالایش لاوان"),
            ("فخوز", "فولاد خوزستان"),
            ("فولاد", "فولاد مبارکه"),
            ("کچاد", "چادرملو"),
            ("کگل", "گل گهر"),
            ("بوعلی", "پتروشیمی بوعلی"),
            ("شاراک", "پتروشیمی شازند"),
            ("شغدیر", "پتروشیمی غدیر"),
            ("شیراز", "پتروشیمی شیراز"),
            ("پارس", "پتروشیمی پارس"),
            ("زاگرس", "پتروشیمی زاگرس"),
            ("شبصیر", "پتروشیمی بندر امام"),
            ("وپاسار", "بانک پاسارگاد"),
            ("وپست", "پست بانک"),
            ("وصندوق", "سرمایه‌گذاری صندوق بازنشستگی"),
            ("وبصادر", "بانک صادرات"),
            ("وسپه", "سرمایه‌گذاری سپه"),
            ("وغدیر", "سرمایه‌گذاری غدیر"),
            ("خگستر", "گسترش سرمایه‌گذاری ایران خودرو"),
            ("خپارس", "پارس خودرو"),
            ("خزامیا", "زامیاد"),
            ("خساپا", "سایپا"),
            ("همراه", "همراه اول"),
            ("اخابر", "مخابرات"),
            ("رتکو", "کنترل خوردگی تک"),
            ("شبریز", "پالایش تبریز"),
            ("شپاس", "پالایش پاسارگاد"),
            ("شتران", "پالایش تهران"),
            ("شفن", "پتروشیمی فن‌آوران"),
            ("شفارا", "پتروشیمی فارابی"),
            ("شگویا", "پتروشیمی گویا"),
            ("شهسا", "هسته‌سازان"),
            ("سیمرغ", "داروسازی سیمرغ"),
            ("دارو", "کارخانجات داروپخش"),
            ("تیپیکو", "سرمایه‌گذاری دارویی تأمین"),
            ("وکغدیر", "کوچک صنایع"),
            ("ونیکی", "سرمایه‌گذاری ملی"),
        ],
    },
}


# ═══════════════════════════════════════════════════════════
# توابع
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
    """
    چک کن نماد مفیده یا نه.

    حذف می‌کنه:
    - حق تقدم‌ها (به «ح» ختم می‌شن)
    - اوراق (به عدد ختم می‌شن)
    - نمادهای کوتاه (کمتر از ۲ حرف)
    """
    if not symbol:
        return False
    if len(symbol) < 2:
        return False
    # ختم به «ح» = حق تقدم
    if symbol.endswith("ح"):
        return False
    # ختم به عدد = اوراق
    if symbol[-1].isdigit():
        return False
    # «ح» در آخر با فاصله
    if "ح" in symbol and symbol.strip().endswith("ح"):
        return False
    return True


def get_iran_stock_symbols() -> list[str]:
    """لیست کل نمادهای بورس تهران — فیلترشده"""
    cat = MARKET_CATEGORIES.get("iran_stocks", {})
    static = [t[0] for t in cat.get("tickers", [])]

    # ═══ فایل جدید ═══
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

    # ═══ cache قدیمی ═══
    cached = _load_tsetmc_cache()

    # ═══ ادغام + فیلتر ═══
    all_syms = set(static + full_syms + cached)
    filtered = [s for s in all_syms if _is_valid_stock_symbol(s)]

    return sorted(filtered)


def get_iran_stock_map() -> dict:
    """نگاشت نماد → نام فارسی — فیلترشده"""
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

    # ═══ فیلتر ═══
    filtered_map = {s: n for s, n in static_map.items() if _is_valid_stock_symbol(s)}

    return filtered_map


def get_crypto_symbols() -> list[str]:
    cat = MARKET_CATEGORIES.get("crypto", {})
    return [t[0] for t in cat.get("tickers", [])]


# ═══════════════════════════════════════════════════════════
# کش TSETMC (فایل)
# ═══════════════════════════════════════════════════════════
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


def fetch_tsetmc_all_symbols() -> list[str]:
    """
    دریافت لیست کامل نمادهای بورس تهران از API.
    (اگه قبلاً cache شده، همون رو برمی‌گردونه)
    """
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
]


if __name__ == "__main__":
    print("=" * 60)
    print("تست core/market_lists.py — نسخه ۴.۰")
    print("=" * 60)
    print()
    for key, cat in MARKET_CATEGORIES.items():
        count = len(cat.get("tickers", []))
        print(f"   {cat['icon']} {cat['name']:20} — {count} نماد")
    print()
    print(f"نمادهای TSETMC (cache): {len(_load_tsetmc_cache())}")
    print()
