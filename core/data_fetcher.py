"""
core/data_fetcher.py
دریافت داده از AlanChand، TGJU و yfinance
نسخه ۳.۰ — با search_symbol کش‌شده و ThreadPool
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

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

SYMBOLS = {
    "GC=F": "طلا",
    "SI=F": "نقره",
    "BTC-USD": "بیت‌کوین",
    "BZ=F": "نفت برنت",
}

CORRELATION_SYMBOLS = {
    "DX-Y.NYB": "شاخص دلار",
    "^TNX": "بازده ۱۰ ساله",
    "^VIX": "شاخص ترس",
    "BZ=F": "نفت برنت",
}

TIMEFRAMES = [
    ("1m", "1d", "۱ دقیقه"),      # ← جدید
    ("5m", "5d", "۵ دقیقه"),
    ("15m", "5d", "۱۵ دقیقه"),
    ("30m", "1mo", "۳۰ دقیقه"),
    ("1h", "3mo", "۱ ساعت"),
    ("1d", "6mo", "روزانه"),
]

PRICE_ITEMS = [
    ("geram18", "طلای ۱۸"),
    ("mesghal", "مثقال"),
    ("sekee", "سکه امامی"),
    ("dollar", "دلار"),
    ("ons", "انس جهانی"),
]


# ═══════════════════════════════════════════════════════════
# fetch امن با retry
# ═══════════════════════════════════════════════════════════
def fetch_html(url: str, timeout: int = TIMEOUT, retries: int = RETRIES):
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


# ═══════════════════════════════════════════════════════════
# استخراج از AlanChand
# ═══════════════════════════════════════════════════════════
def extract_alanchand(html: str) -> dict:
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
        print(f"[Fetcher] خطا در AlanChand: {e}")

    return results


# ═══════════════════════════════════════════════════════════
# استخراج از TGJU
# ═══════════════════════════════════════════════════════════
def extract_tgju(html: str) -> dict:
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
                if key != "ons":
                    price = price / 10
                results[key] = price
    except Exception as e:
        print(f"[Fetcher] خطا در TGJU: {e}")

    return results


# ═══════════════════════════════════════════════════════════
# دریافت قیمت‌های ایران (AlanChand → TGJU)
# ═══════════════════════════════════════════════════════════
def fetch_iran_prices() -> dict:
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
# دریافت داده تاریخی yfinance
# ═══════════════════════════════════════════════════════════
def fetch_history(ticker: str, interval: str, period: str):
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
        print(f"[Fetcher] خطا در yfinance {ticker}: {e}")
        return None

    if df is None or df.empty:
        return None

    df = normalize_df_columns(df)

    needed = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in needed):
        return None

    keep_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep_cols].copy()
    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)

    if len(df) < 20:
        return None

    return df


def fetch_all_history() -> dict:
    results = {ticker: {} for ticker in SYMBOLS}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for ticker in SYMBOLS:
            for interval, period, tf_name in TIMEFRAMES:
                future = executor.submit(fetch_history, ticker, interval, period)
                futures[future] = (ticker, tf_name)

        for future in as_completed(futures):
            ticker, tf_name = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results[ticker][tf_name] = df
            except Exception as e:
                print(f"[Fetcher] خطا در {ticker} {tf_name}: {e}")

    return results


# ═══════════════════════════════════════════════════════════
# همبستگی
# ═══════════════════════════════════════════════════════════
def fetch_correlation(t1: str, t2: str, period: str = "1mo", interval: str = "1d"):
    try:
        df1 = yf.download(t1, period=period, interval=interval,
                          progress=False, auto_adjust=True, threads=False)
        df2 = yf.download(t2, period=period, interval=interval,
                          progress=False, auto_adjust=True, threads=False)

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
        print(f"[Fetcher] خطا در correlation: {e}")
        return None


def fetch_all_correlations() -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_correlation, "GC=F", ticker): ticker
            for ticker in CORRELATION_SYMBOLS
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
    try:
        g = yf.download("GC=F", period="1mo", interval="1d",
                        progress=False, auto_adjust=True, threads=False)
        s = yf.download("SI=F", period="1mo", interval="1d",
                        progress=False, auto_adjust=True, threads=False)

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
        print(f"[Fetcher] خطا در GSR: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# جستجوی نماد — کش ۱ ساعته برای سرعت
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def search_symbol(query: str) -> str | None:
    """
    جستجوی نماد با چند روش:
    1. تلاش با نماد خام
    2. تلاش با پسوندهای مختلف (فارکس، کریپتو، سهام، شاخص)
    
    Args:
        query: مثلاً "AAPL" یا "EURUSD" یا "BTC"
    
    Returns:
        نماد معتبر یا None
    """
    if not query:
        return None

    query = query.upper().strip()

    candidates = [query]

    # فارکس: مثلاً EURUSD → EURUSD=X
    if len(query) == 6 and query.isalpha():
        candidates.append(f"{query}=X")
        candidates.append(f"{query[:3]}/{query[3:]}")

    # کریپتو
    crypto_list = [
        "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "BNB",
        "TON", "TRX", "USDT", "USDC", "MATIC", "DOT", "AVAX",
        "LINK", "UNI", "ATOM", "LTC", "BCH", "XLM",
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

    # تلاش برای هر کاندید
    for cand in candidates:
        try:
            df = yf.download(
                cand, period="5d", interval="1d",
                progress=False, auto_adjust=True, threads=False,
            )
            if df is not None and not df.empty:
                return cand
        except Exception:
            continue

    return None


# ═══════════════════════════════════════════════════════════
# تست سریع
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("تست core/data_fetcher.py")
    print("=" * 55)
    print()

    print("۱) دریافت قیمت‌های لحظه‌ای ایران...")
    iran = fetch_iran_prices()
    print(f"   منبع: {iran['source']}")
    print(f"   زمان: {iran['timestamp']}")
    for key, name in PRICE_ITEMS:
        price = iran["prices"].get(key)
        if price is not None:
            print(f"   {name}: {price:,.0f}")
        else:
            print(f"   {name}: —")
    print()

    print("۲) دریافت داده تاریخی طلا (۵ دقیقه)...")
    df = fetch_history("GC=F", "5m", "5d")
    if df is not None:
        print(f"   تعداد کندل: {len(df)}")
        print(f"   آخرین قیمت: ${safe_num(df['close'].iloc[-1]):,.2f}")
    else:
        print("   خطا")
    print()

    print("۳) نسبت طلا به نقره...")
    gsr = fetch_gold_silver_ratio()
    print(f"   GSR: {gsr:.2f}" if gsr else "   خطا")
    print()

    print("۴) همبستگی طلا با شاخص دلار...")
    corr = fetch_correlation("GC=F", "DX-Y.NYB")
    print(f"   Correlation: {corr:+.3f}" if corr else "   خطا")
    print()

    print("۵) تست جستجوی نماد...")
    for q in ["AAPL", "EURUSD", "BTC", "TSLA", "GOLD", "BRENT"]:
        result = search_symbol(q)
        print(f"   {q} → {result}")
    print()

    print("[OK] تست کامل شد.")

    # ═══════════════════════════════════════════════════════════
# دریافت OHLCV بر اساس منبع انتخابی
# ═══════════════════════════════════════════════════════════
def fetch_history_by_source(
    ticker: str,
    interval: str,
    period: str,
    source: str = "global",
) -> "pd.DataFrame | None":
    """
    دریافت OHLCV بر اساس منبع انتخابی کاربر.
    
    Args:
        ticker: نماد (مثلاً BTC-USD)
        interval: تایم‌فریم (5m, 15m, 30m, 1h, 1d)
        period: دوره (5d, 1mo, 3mo, 6mo)
        source: منبع دیتا:
            - "global": yfinance (پیش‌فرض)
            - "nobitex": نوبیتکس (فقط کریپتو)
            - "abantether": آبان‌تتر (فقط قیمت لحظه‌ای — OHLCV نداره)
    
    Returns:
        DataFrame OHLCV یا None
    """
    if source == "global":
        return fetch_history(ticker, interval, period)
    
    if source == "nobitex":
        # نوبیتکس فقط کریپتو داره
        try:
            from .nobitex_fetcher import fetch_nobitex_for_ticker
            df = fetch_nobitex_for_ticker(ticker, interval, period)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[Fetcher] خطا در نوبیتکس {ticker}: {e}")
        # fallback به yfinance
        return fetch_history(ticker, interval, period)
    
    if source == "abantether":
        # آبان‌تتر OHLCV نداره — از yfinance استفاده می‌کنیم
        # ولی قیمت لحظه‌ای رو از آبان‌تتر می‌گیریم (در تابع دیگه)
        return fetch_history(ticker, interval, period)
    
    # پیش‌فرض
    return fetch_history(ticker, interval, period)

    # ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای از منبع انتخابی
# ═══════════════════════════════════════════════════════════
def fetch_live_price_by_source(ticker: str, source: str = "global") -> "dict | None":
    """
    دریافت قیمت لحظه‌ای بر اساس منبع انتخابی.
    
    Args:
        ticker: نماد (مثلاً BTC-USD)
        source: "global" / "nobitex" / "abantether"
    
    Returns:
        {"price": float, "buy": float, "sell": float, "spread_pct": float} یا None
    """
    if source == "nobitex":
        try:
            from .nobitex_fetcher import fetch_nobitex_for_ticker
            # از Order Book استفاده می‌کنیم
            from .nobitex_fetcher import map_symbol_to_nobitex, fetch_nobitex_orderbook
            sym = map_symbol_to_nobitex(ticker)
            if sym:
                ob = fetch_nobitex_orderbook(sym)
                if ob:
                    return {
                        "price": ob["last_price"],
                        "buy": ob["best_bid"],
                        "sell": ob["best_ask"],
                        "spread_pct": ob["spread_pct"],
                    }
        except Exception as e:
            print(f"[Fetcher] خطا در قیمت نوبیتکس: {e}")
        return None
    
    if source == "abantether":
        try:
            from .abantether_fetcher import fetch_abantether_for_ticker
            info = fetch_abantether_for_ticker(ticker)
            if info:
                return {
                    "price": info["last_price"],
                    "buy": info["buy_price"],
                    "sell": info["sell_price"],
                    "spread_pct": info["spread_pct"],
                }
        except Exception as e:
            print(f"[Fetcher] خطا در قیمت آبان‌تتر: {e}")
        return None
    
    return None