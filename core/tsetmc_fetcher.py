"""
core/tsetmc_fetcher.py
اتصال به API بورس تهران (TSETMC) — نسخه ۳.۰ (فاز ۵)
============================================================
بازنویسی کامل:
  - حذف کدهای مرده (بعد از return)
  - حذف توابع تکراری انتهای فایل
  - یکپارچه با market_lists (get_iran_stock_symbols)
  - اضافه شدن is_in_tsetmc برای sources.py
  - کش داخلی insCode (برای جلوگیری از جستجوی تکراری)
  - تست بهتر

منابع API:
  - https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{query}
  - https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{insCode}/0
  - https://cdn.tsetmc.com/api/MarketData/GetMarketOverview/1

⚠️ TSETMC فقط از IP ایران در دسترسه
"""

from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from .market_lists import get_iran_stock_map, get_iran_stock_symbols
from .tz import TEHRAN, ensure_utc_index
from .utils import safe_num

TSETMC_BASE = "https://cdn.tsetmc.com/api"
TSETMC_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════
# کش داخلی insCode (برای سرعت)
# ═══════════════════════════════════════════════════════════
_INS_CODE_CACHE: dict[str, str] = {}


# ═══════════════════════════════════════════════════════════
# ابزار
# ═══════════════════════════════════════════════════════════
def _get(url: str) -> Optional[dict]:
    """درخواست GET امن"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TSETMC_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[TSETMC] Timeout: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"[TSETMC] HTTP {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[TSETMC] Request: {e}")
    except ValueError as e:
        print(f"[TSETMC] JSON: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# چک سریع (برای sources.py)
# ═══════════════════════════════════════════════════════════
def is_in_tsetmc(ticker: str) -> bool:
    """بررسی سریع اینکه نماد بورس تهران هست یا نه"""
    if not ticker:
        return False
    return ticker in get_iran_stock_symbols()


def get_tsetmc_symbols() -> list[str]:
    """لیست نمادهای بورس تهران (از market_lists)"""
    return get_iran_stock_symbols()


def get_tsetmc_symbol_map() -> dict:
    """dict نماد → نام فارسی"""
    return get_iran_stock_map()


# ═══════════════════════════════════════════════════════════
# ۱. جستجوی نماد
# ═══════════════════════════════════════════════════════════
def search_tsetmc_symbol(query: str) -> Optional[dict]:
    """
    جستجوی نماد در بورس تهران.

    Args:
        query: نام یا نماد (مثلاً "فولاد" یا "فملی")

    Returns:
        dict با insCode, symbol, name, isin یا None
    """
    if not query:
        return None

    # چک کش
    if query in _INS_CODE_CACHE:
        cached = _INS_CODE_CACHE[query]
        return {
            "insCode": cached,
            "symbol": query,
            "name": get_iran_stock_map().get(query, query),
            "isin": "",
            "cached": True,
        }

    url = f"{TSETMC_BASE}/Instrument/GetInstrumentSearch/{query}"
    data = _get(url)

    if not data:
        return None

    try:
        instruments = data.get("instrumentSearch", [])
        if not instruments:
            return None

        # بهترین تطابق: exact match
        best = None
        for inst in instruments:
            sym = inst.get("lVal18AFC", "")
            if sym == query:
                best = inst
                break

        if best is None:
            best = instruments[0]

        ins_code = str(best.get("insCode", ""))
        if ins_code:
            _INS_CODE_CACHE[query] = ins_code

        return {
            "insCode": ins_code,
            "symbol": best.get("lVal18AFC", ""),
            "name": best.get("lVal30", ""),
            "isin": best.get("isin", ""),
            "cached": False,
        }
    except (KeyError, TypeError, IndexError) as e:
        print(f"[TSETMC] parse search: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۲. دریافت OHLCV روزانه
# ═══════════════════════════════════════════════════════════
def fetch_tsetmc_ohlcv(ins_code: str, days: int = 200) -> Optional[pd.DataFrame]:
    """
    دریافت OHLCV روزانه از TSETMC.

    Args:
        ins_code: کد نماد (مثلاً "46348559193224090")
        days: تعداد روزهای آخر

    Returns:
        DataFrame با open, high, low, close, volume
    """
    if not ins_code:
        return None

    # API جدید
    url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
    data = _get(url)

    # fallback: API قدیمی
    if not data:
        url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceDaily/{ins_code}"
        data = _get(url)

    if not data:
        return None

    try:
        prices = data.get("closingPriceDaily", []) or data.get(
            "closingPriceDailyList", []
        )

        if not prices:
            return None

        rows = []
        for p in prices:
            try:
                rows.append(
                    {
                        "date": p.get("dEven"),
                        "open": safe_num(p.get("priceFirst")),
                        "high": safe_num(p.get("priceMax")),
                        "low": safe_num(p.get("priceMin")),
                        "close": safe_num(p.get("pClosing")),
                        "volume": safe_num(p.get("qTotTran5J")),
                    }
                )
            except (KeyError, TypeError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows)

        # تبدیل date (YYYYMMDD) به datetime
        df["date"] = pd.to_datetime(
            df["date"].astype(str), format="%Y%m%d", errors="coerce"
        )
        df = df.dropna(subset=["date"])
        df = df.set_index("date")
        df = df.sort_index()

        # فیلتر کندل‌های صفر (روزهای تعطیل/بدون معامله)
        df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)]

        # ═══ ایندکس زمانی ═══
        # TSETMC فقط تاریخ تقویمی می‌دهد (بدون ساعت). آن را نیمه‌شب
        # به وقت تهران در نظر می‌گیریم و به UTC تبدیل می‌کنیم تا با
        # بقیه‌ی منابع و با timestampهای UTC دیتابیس قابل مقایسه باشد.
        # نتیجه: تاریخ 2026-10-03 → 2026-10-02T20:30:00Z
        df = ensure_utc_index(df, assume_tz=TEHRAN)
        if df is None or df.empty:
            return None

        # آخرین N روز
        df = df.tail(days)

        return df

    except (KeyError, TypeError) as e:
        print(f"[TSETMC] parse OHLCV: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۳. خلاصه بازار (شاخص کل)
# ═══════════════════════════════════════════════════════════
def fetch_tsetmc_market_overview() -> Optional[dict]:
    """خلاصه بازار بورس تهران"""
    url = f"{TSETMC_BASE}/MarketData/GetMarketOverview/1"
    data = _get(url)

    if not data:
        return None

    try:
        overview = data.get("marketOverview", {})
        if not overview:
            return None

        return {
            "index": safe_num(overview.get("indexLastValue")),
            "change": safe_num(overview.get("indexChange")),
            "change_pct": safe_num(overview.get("indexChangePercent")),
            "volume": safe_num(overview.get("qTotTran5J")),
            "value": safe_num(overview.get("qTotCap")),
        }
    except (KeyError, TypeError) as e:
        print(f"[TSETMC] parse overview: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۴. تابع اصلی (جستجو + OHLCV)
# ═══════════════════════════════════════════════════════════
def fetch_tsetmc_for_symbol(symbol: str, days: int = 200) -> Optional[pd.DataFrame]:
    """
    دریافت OHLCV برای یک نماد بورس تهران.

    Args:
        symbol: نام یا نماد (مثلاً "فولاد")
        days: تعداد روزهای آخر

    Returns:
        DataFrame OHLCV یا None
    """
    if not symbol:
        return None

    search_result = search_tsetmc_symbol(symbol)
    if not search_result:
        print(f"[TSETMC] نماد {symbol} پیدا نشد (شاید IP ایران نیست)")
        return None

    ins_code = search_result["insCode"]
    return fetch_tsetmc_ohlcv(ins_code, days=days)


# ═══════════════════════════════════════════════════════════
# ۵. تابع ترکیبی برای اسکنر (فقط نمادهای بازار)
# ═══════════════════════════════════════════════════════════
def fetch_tsetmc_top_symbols(top_n: int = 10) -> list[dict]:
    """
    دریافت top نمادهای بورس تهران.
    (در آینده می‌تونه از MarketWatch API استفاده کنه)
    """
    all_syms = get_iran_stock_symbols()
    return [
        {"symbol": s, "name": get_iran_stock_map().get(s, s)} for s in all_syms[:top_n]
    ]


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("تست core/tsetmc_fetcher.py — نسخه ۳.۰")
    print("=" * 65)
    print()

    print("۱) تعداد نمادهای بورس تهران:")
    print(f"   {len(get_tsetmc_symbols())} نماد")
    print()

    print("۲) is_in_tsetmc:")
    for t in ["فولاد", "فملی", "BTC-USD", "GC=F"]:
        print(f"   {t:12} → {is_in_tsetmc(t)}")
    print()

    print("۳) جستجوی «فولاد»:")
    result = search_tsetmc_symbol("فولاد")
    if result:
        print(f"   insCode: {result['insCode']}")
        print(f"   نماد: {result['symbol']}")
        print(f"   نام: {result['name']}")
    else:
        print("   ❌ خطا (شاید IP ایران نیست)")
    print()

    if result:
        print("۴) OHLCV «فولاد» (۳۰ روز آخر):")
        df = fetch_tsetmc_ohlcv(result["insCode"], days=30)
        if df is not None and not df.empty:
            print(f"   تعداد: {len(df)}")
            print(f"   آخرین: {df['close'].iloc[-1]:,.0f} ریال")
            print(f"   بازه: {df.index[0].date()} → {df.index[-1].date()}")
        else:
            print("   ❌ خطا")
    print()

    print("۵) خلاصه بازار:")
    overview = fetch_tsetmc_market_overview()
    if overview:
        print(f"   شاخص کل: {overview['index']:,.0f}")
        print(f"   تغییر: {overview['change']:+,.0f} ({overview['change_pct']:+.2f}%)")
    else:
        print("   ❌ خطا")
    print()

    print("[OK] تست کامل شد.")


def fetch_tsetmc_live_quote(symbol: str) -> Optional[dict]:
    """
    قیمت زنده لحظه‌ای از TSETMC.

    ⚠️ چرا لازم است:
        ``fetch_tsetmc_ohlcv`` فقط کندل‌های **بسته‌شده** رو میده.
        یعنی توی ساعات معاملات، آخرین کندل = **دیروز**.
        برای قیمت زنده باید از endpoint جدا استفاده کنیم.

    Returns:
        dict با price, change_pct, price_yesterday, price_min, price_max
        یا None
    """
    if not symbol:
        return None

    search = search_tsetmc_symbol(symbol)
    if not search:
        return None

    ins_code = search["insCode"]
    url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    data = _get(url)

    if not data:
        return None

    try:
        info = data.get("closingPriceInfo") or {}
        if not info:
            return None

        price = safe_num(info.get("pDrCotVal"))  # آخرین معامله
        price_yesterday = safe_num(info.get("priceYesterday"))
        price_first = safe_num(info.get("priceFirst"))
        price_min = safe_num(info.get("priceMin"))
        price_max = safe_num(info.get("priceMax"))
        closing = safe_num(info.get("pClosing"))

        # ─── اگه معامله‌ای نشده، از pClosing استفاده کن ───
        if not price or price <= 0:
            price = closing or price_yesterday

        if not price or price <= 0:
            return None

        # ─── تغییر نسبت به قیمت دیروز ───
        change_pct = 0.0
        if price_yesterday and price_yesterday > 0:
            change_pct = (price - price_yesterday) / price_yesterday * 100

        return {
            "ticker": symbol,
            "price": float(price),
            "change_pct": round(change_pct, 2),
            "source": "tsetmc",
            "price_yesterday": float(price_yesterday) if price_yesterday else None,
            "price_min": float(price_min) if price_min else None,
            "price_max": float(price_max) if price_max else None,
            "closing": float(closing) if closing else None,
        }
    except (KeyError, TypeError) as e:
        print(f"[TSETMC] live quote parse: {e}")
        return None
