"""
core/data_fetcher.py
لایه‌ی دریافت داده — نسخه ۵.۰ (فاز ۵)
============================================================
بازنویسی کامل با استفاده از:
  - core.sources برای سوییچ خودکار
  - core.contracts برای enumها
  - core.nobitex_fetcher برای نوبیتکس
  - yfinance برای بازارهای جهانی

تغییرات:
  - fetch_history_by_source با USDT-IRT پشتیبانی می‌کنه
  - resolve_symbol_and_source برای سوییچ خودکار
  - حذف تکراری‌های get_default_symbol_for_source
  - fetch_iran_prices حفظ شده (AlanChand + TGJU)
  - search_symbol فقط برای global (نوبیتکس جستجو داره جدا)
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

from .contracts import DataSource
from .sources import (
    get_default_symbol_for_source,
    is_symbol_available_in_source,
    resolve_source,
    resolve_symbol_and_source,
)
from .utils import (
    normalize_df_columns,
    parse_number,
    safe_num,
    to_english_digits,
)

# ═══════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════
ALANCHAND_URL = "https://alanchand.com/"
TGJU_URL = "https://www.tgju.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

TIMEOUT = 20
RETRIES = 2


# ═══════════════════════════════════════════════════════════
# قیمت‌های ایران (AlanChand + TGJU)
# ═══════════════════════════════════════════════════════════
def fetch_html(url: str, timeout: int = TIMEOUT, retries: int = RETRIES):
    """دریافت HTML امن با retry"""
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            if attempt == retries:
                print(f"[Fetcher] خطا در {url}: {e}")
                return None
    return None


def extract_alanchand(html: str) -> dict:
    """استخراج قیمت‌ها از AlanChand"""
    if not html:
        return {}

    results = {}
    try:
        soup = BeautifulSoup(html, "html.parser")
        name_map = {
            "گرم طلای 18": "geram18",
            "گرم طلای ۱۸": "geram18",
            "آبشده": "mesghal",
            "مثقال": "mesghal",
            "سکه امامی": "sekee",
            "انس طلا": "ons",
        }

        for card in soup.find_all(class_="goldCard"):
            card_text = to_english_digits(card.get_text(" ", strip=True))
            for name, key in name_map.items():
                if name in card_text and key not in results:
                    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(تومان|\$)", card_text)
                    if m:
                        price = parse_number(m.group(1))
                        if price:
                            results[key] = price
                    else:
                        nums = re.findall(r"[\d,]{4,}", card_text)
                        candidates = [parse_number(n) for n in nums]
                        candidates = [c for c in candidates if c and c > 100]
                        if candidates:
                            results[key] = max(candidates)
                    break

        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                first = to_english_digits(cells[0].get_text(strip=True))
                if "دلار آمریکا" in first and "dollar" not in results:
                    sell = parse_number(cells[2].get_text(strip=True))
                    if sell:
                        results["dollar"] = sell
                    break
    except Exception as e:
        print(f"[Fetcher] AlanChand: {e}")

    return results


def extract_tgju(html: str) -> dict:
    """استخراج قیمت‌ها از TGJU"""
    if not html:
        return {}

    results = {}
    try:
        soup = BeautifulSoup(html, "html.parser")
        key_map = {
            "geram18": "geram18",
            "mesghal": "mesghal",
            "sekee": "sekee",
            "price_dollar_rl": "dollar",
            "ons": "ons",
        }

        for row in soup.find_all("tr", attrs={"data-market-row": True}):
            raw_key = row.get("data-market-row", "").strip()
            if raw_key not in key_map:
                continue
            key = key_map[raw_key]
            if key in results:
                continue

            nf_cells = row.find_all("td", class_="nf")
            if not nf_cells:
                continue

            price = parse_number(nf_cells[0].get_text(strip=True))
            if price:
                # TGJU ریال می‌ده — تبدیل به تومان
                if key != "ons":
                    price = price / 10
                results[key] = price
    except Exception as e:
        print(f"[Fetcher] TGJU: {e}")

    return results


def fetch_iran_prices() -> dict:
    """دریافت قیمت‌های لحظه‌ای ایران (AlanChand → TGJU)"""
    result = {
        "prices": {},
        "source": "None",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }

    html = fetch_html(ALANCHAND_URL)
    if html:
        prices = extract_alanchand(html)
        if len(prices) >= 3:
            result["prices"] = prices
            result["source"] = "AlanChand"
            return result

    html = fetch_html(TGJU_URL)
    if html:
        prices = extract_tgju(html)
        if len(prices) >= 3:
            result["prices"] = prices
            result["source"] = "TGJU"
            return result

    return result


# ═══════════════════════════════════════════════════════════
# yfinance — OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_history_yfinance(ticker: str, interval: str, period: str):
    """دریافت OHLCV از yfinance"""
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as e:
        print(f"[Fetcher] yfinance {ticker}: {e}")
        return None

    if df is None or df.empty:
        return None

    df = normalize_df_columns(df)

    needed = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in needed):
        return None

    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()
    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)

    if len(df) < 20:
        return None

    return df


# ═══════════════════════════════════════════════════════════
# نقطه ورود اصلی — fetch_history_by_source
# ═══════════════════════════════════════════════════════════
def fetch_history_by_source(
    ticker: str,
    interval: str,
    period: str,
    source: str = "global",
):
    """
    دریافت OHLCV بر اساس منبع.

    Args:
        ticker: نماد داخلی
        interval: 1m/5m/15m/30m/1h/1d
        period: 1d/5d/1mo/3mo/6mo
        source: global/nobitex/abantether/tsetmc
    """
    if not ticker:
        return None

    # ═══ جهانی ═══
    if source == DataSource.GLOBAL.value:
        return fetch_history_yfinance(ticker, interval, period)

    # ═══ نوبیتکس ═══
    if source == DataSource.NOBITEX.value:
        try:
            from .nobitex_fetcher import fetch_nobitex_for_ticker

            df = fetch_nobitex_for_ticker(ticker, interval, period)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[Fetcher] nobitex {ticker}: {e}")
        # fallback به yfinance
        return fetch_history_yfinance(ticker, interval, period)

    # ═══ آبان‌تتر (OHLCV نداره — fallback به yfinance) ═══
    if source == DataSource.ABANTETHER.value:
        return fetch_history_yfinance(ticker, interval, period)

    # ═══ TSETMC (بورس تهران) ═══
    if source == DataSource.TSETMC.value:
        try:
            from .tsetmc_fetcher import fetch_tsetmc_for_symbol

            df = fetch_tsetmc_for_symbol(ticker)
            if df is not None and not df.empty:
                # TSETMC روزانه‌ست — برای TF های پایین‌تر از روزانه fallback
                if interval == "1d":
                    return df
                # برای TF پایین‌تر، fallback به yfinance
                return fetch_history_yfinance(ticker, interval, period)
        except Exception as e:
            print(f"[Fetcher] tsetmc {ticker}: {e}")
        return None

    # پیش‌فرض
    return fetch_history_yfinance(ticker, interval, period)


# ═══════════════════════════════════════════════════════════
# fetch_history — سازگاری با کدهای قدیمی
# ═══════════════════════════════════════════════════════════
def fetch_history(ticker: str, interval: str, period: str):
    """سازگاری با کدهای قدیمی — معادل global"""
    return fetch_history_yfinance(ticker, interval, period)


# ═══════════════════════════════════════════════════════════
# fetch_all_history (برای تیکر/صفحه اصلی)
# ═══════════════════════════════════════════════════════════
def fetch_all_history(symbols: dict, timeframes: list) -> dict:
    """دریافت موازی OHLCV همه نمادها (برای global)"""
    results = {ticker: {} for ticker in symbols}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for ticker in symbols:
            for interval, period, tf_name in timeframes:
                future = executor.submit(
                    fetch_history_yfinance, ticker, interval, period
                )
                futures[future] = (ticker, tf_name)

        for future in as_completed(futures):
            ticker, tf_name = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results[ticker][tf_name] = df
            except Exception as e:
                print(f"[Fetcher] {ticker} {tf_name}: {e}")

    return results


# ═══════════════════════════════════════════════════════════
# جستجوی نماد (فقط جهانی)
# ═══════════════════════════════════════════════════════════
def search_symbol(query: str) -> Optional[str]:
    """
    جستجوی نماد در yfinance.
    (نوبیتکس جستجوی جداگانه داره)
    """
    if not query:
        return None

    query = query.upper().strip()
    candidates = [query]

    # فارکس
    if len(query) == 6 and query.isalpha():
        candidates.append(f"{query}=X")
        candidates.append(f"{query[:3]}/{query[3:]}")

    # کریپتو
    crypto_list = [
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "DOGE",
        "ADA",
        "BNB",
        "TON",
        "TRX",
        "USDT",
        "USDC",
        "MATIC",
        "DOT",
        "AVAX",
        "LINK",
        "UNI",
        "ATOM",
        "LTC",
        "BCH",
        "XLM",
    ]
    if query in crypto_list:
        candidates.insert(0, f"{query}-USD")

    # شاخص‌ها
    index_map = {
        "SPX": "^GSPC",
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
        "VIX": "^VIX",
        "DXY": "DX-Y.NYB",
    }
    if query in index_map:
        candidates.insert(0, index_map[query])

    # نفت
    if query in ("WTI", "OIL"):
        candidates.insert(0, "CL=F")
    if query in ("BRENT", "BZ"):
        candidates.insert(0, "BZ=F")

    # طلا و نقره
    if query in ("XAUUSD", "GOLD"):
        candidates.insert(0, "GC=F")
    if query in ("XAGUSD", "SILVER"):
        candidates.insert(0, "SI=F")

    for cand in candidates:
        try:
            df = yf.download(
                cand,
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            if df is not None and not df.empty:
                return cand
        except Exception:
            continue

    return None


# ═══════════════════════════════════════════════════════════
# همبستگی (برای تحلیل طلا)
# ═══════════════════════════════════════════════════════════
def fetch_correlation(t1: str, t2: str, period: str = "1mo", interval: str = "1d"):
    """محاسبه همبستگی بین دو نماد"""
    try:
        df1 = yf.download(
            t1,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        df2 = yf.download(
            t2,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )

        if df1 is None or df2 is None or df1.empty or df2.empty:
            return None

        df1 = normalize_df_columns(df1)
        df2 = normalize_df_columns(df2)

        if "close" not in df1.columns or "close" not in df2.columns:
            return None

        s1 = df1["close"].squeeze()
        s2 = df2["close"].squeeze()
        m = pd.concat([s1, s2], axis=1).dropna()

        if len(m) < 10:
            return None

        corr = m.iloc[:, 0].corr(m.iloc[:, 1])
        return float(corr) if pd.notna(corr) else None
    except Exception as e:
        print(f"[Fetcher] correlation: {e}")
        return None


def fetch_all_correlations(correlation_symbols: dict) -> dict:
    """محاسبه موازی همبستگی طلا با نمادهای دیگه"""
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_correlation, "GC=F", ticker): ticker
            for ticker in correlation_symbols
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception:
                results[ticker] = None
    return results


# ═══════════════════════════════════════════════════════════
# نسبت طلا به نقره
# ═══════════════════════════════════════════════════════════
def fetch_gold_silver_ratio():
    """نسبت طلا به نقره"""
    try:
        g = yf.download(
            "GC=F",
            period="1mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        s = yf.download(
            "SI=F",
            period="1mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )

        if g is None or s is None or g.empty or s.empty:
            return None

        g = normalize_df_columns(g)
        s = normalize_df_columns(s)

        if "close" not in g.columns or "close" not in s.columns:
            return None

        gold_price = safe_num(g["close"].iloc[-1])
        silver_price = safe_num(s["close"].iloc[-1])

        if silver_price > 0:
            return gold_price / silver_price
    except Exception as e:
        print(f"[Fetcher] GSR: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# exports سازگاری
# ═══════════════════════════════════════════════════════════
__all__ = [
    "fetch_iran_prices",
    "fetch_history",
    "fetch_history_yfinance",
    "fetch_history_by_source",
    "fetch_all_history",
    "fetch_correlation",
    "fetch_all_correlations",
    "fetch_gold_silver_ratio",
    "search_symbol",
    "get_default_symbol_for_source",
    "is_symbol_available_in_source",
    "resolve_source",
    "resolve_symbol_and_source",
]


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("تست core/data_fetcher.py — نسخه ۵.۰")
    print("=" * 70)
    print()

    print("۱) قیمت‌های ایران:")
    iran = fetch_iran_prices()
    print(f"   منبع: {iran['source']}")
    print(f"   تعداد: {len(iran['prices'])}")
    print()

    print("۲) OHLCV طلا (global):")
    df = fetch_history_by_source("GC=F", "5m", "5d", "global")
    if df is not None:
        print(f"   تعداد: {len(df)}")
        print(f"   آخرین: ${safe_num(df['close'].iloc[-1]):,.2f}")
    else:
        print("   ❌ خطا")
    print()

    print("۳) OHLCV BTC (nobitex):")
    df2 = fetch_history_by_source("BTC-USD", "1h", "5d", "nobitex")
    if df2 is not None:
        print(f"   تعداد: {len(df2)}")
        print(f"   آخرین: ${safe_num(df2['close'].iloc[-1]):,.2f}")
    else:
        print("   ❌ خطا")
    print()

    print("۴) OHLCV USDT-IRT (nobitex):")
    df3 = fetch_history_by_source("USDT-IRT", "1h", "5d", "nobitex")
    if df3 is not None:
        print(f"   تعداد: {len(df3)}")
        print(f"   آخرین: {safe_num(df3['close'].iloc[-1]):,.0f}")
    else:
        print("   ❌ خطا (این طبیعیه اگه نوبیتکس OHLCV برای USDTIRT نداشته باشه)")
    print()

    print("۵) سوییچ خودکار:")
    cases = [
        ("USDT-IRT", "global"),
        ("GC=F", "nobitex"),
        ("BTC-USD", "nobitex"),
        ("فولاد", "global"),
    ]
    for ticker, src in cases:
        ft, fs, msg = resolve_symbol_and_source(ticker, src)
        icon = "🔄" if msg else "✅"
        print(f"   {icon} {ticker:15} از {src:10} → {fs}")
    print()

    print("۶) نسبت طلا به نقره:")
    gsr = fetch_gold_silver_ratio()
    if gsr:
        print(f"   GSR = {gsr:.2f}")
    else:
        print("   ❌ خطا")
    print()

    print("[OK] تست کامل شد.")
