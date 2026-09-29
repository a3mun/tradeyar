"""
core/abantether_fetcher.py
اتصال به API آبان‌تتر — قیمت لحظه‌ای و Order Book
نسخه ۲.۰ (فاز ۵)
============================================================
تغییرات نسخه ۲.۰:
  - اضافه شدن is_in_abantether برای sources.py
  - fetch_abantether_for_ticker حفظ شده
  - پاک‌سازی کدهای اضافی
  - نمایش بهتر spread

API عمومی آبان‌تتر:
  - https://api.abantether.com/api/v1/manager/otc/ticker
  - https://api.abantether.com/api/v1/feecalculator/coin-info

⚠️ توجه: آبان‌تتر OHLCV (تاریخچه کندل) عمومی نداره.
   فقط قیمت لحظه‌ای داره. برای OHLCV از نوبیتکس یا yfinance استفاده می‌شه.
"""

from typing import Optional

import requests

from .utils import safe_num

# ═══════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════
ABANTETHER_BASE = "https://api.abantether.com"
ABANTETHER_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════
# نمادهای آبان‌تتر
# ═══════════════════════════════════════════════════════════
ABANTETHER_SYMBOLS = {
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "SOL-USD": "SOL",
    "XRP-USD": "XRP",
    "BNB-USD": "BNB",
    "ADA-USD": "ADA",
    "DOGE-USD": "DOGE",
    "TON-USD": "TON",
    "AVAX-USD": "AVAX",
    "DOT-USD": "DOT",
    "MATIC-USD": "MATIC",
    "LINK-USD": "LINK",
    "LTC-USD": "LTC",
    "ATOM-USD": "ATOM",
    "NEAR-USD": "NEAR",
    "TRX-USD": "TRX",
    "SHIB-USD": "SHIB",
    "UNI-USD": "UNI",
    "ETC-USD": "ETC",
    "BCH-USD": "BCH",
    "FIL-USD": "FIL",
    "AAVE-USD": "AAVE",
    "APT-USD": "APT",
    "SUI-USD": "SUI",
    "ARB-USD": "ARB",
    "OP-USD": "OP",
    "PAXG-USD": "PAXG",
    "XAUT-USD": "XAUT",
}


# ═══════════════════════════════════════════════════════════
# ابزار
# ═══════════════════════════════════════════════════════════
def _get(url: str, params: dict = None) -> Optional[dict]:
    """درخواست GET امن"""
    try:
        r = requests.get(
            url, params=params, headers=HEADERS, timeout=ABANTETHER_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[Abantether] Timeout: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"[Abantether] HTTP {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[Abantether] Request: {e}")
    except ValueError as e:
        print(f"[Abantether] JSON: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# نگاشت نماد
# ═══════════════════════════════════════════════════════════
def map_symbol_to_abantether(ticker: str) -> Optional[str]:
    """BTC-USD → BTC"""
    if not ticker:
        return None
    return ABANTETHER_SYMBOLS.get(ticker)


def is_in_abantether(ticker: str) -> bool:
    """بررسی سریع برای sources.py"""
    return map_symbol_to_abantether(ticker) is not None


def get_abantether_symbols() -> list[str]:
    """لیست نمادهای پشتیبانی‌شده"""
    return list(ABANTETHER_SYMBOLS.keys())


# ═══════════════════════════════════════════════════════════
# ۱. Ticker (قیمت لحظه‌ای)
# ═══════════════════════════════════════════════════════════
def _parse_ticker_info(coin: str, info: dict) -> dict:
    """پارس یه آیتم ticker"""
    buy_price = safe_num(info.get("buy_price"))
    sell_price = safe_num(info.get("sell_price"))

    if buy_price > 0 and sell_price > 0:
        spread = buy_price - sell_price
        spread_pct = (spread / sell_price) * 100 if sell_price > 0 else 0.0
        last_price = (buy_price + sell_price) / 2
    else:
        spread = 0.0
        spread_pct = 0.0
        last_price = buy_price or sell_price

    return {
        "coin": coin,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "last_price": last_price,
        "spread": spread,
        "spread_pct": spread_pct,
        "buy_max": safe_num(info.get("buy_max")),
        "sell_max": safe_num(info.get("sell_max")),
        "active": bool(info.get("active", False)),
    }


def fetch_abantether_ticker(coin: str = None) -> Optional[dict]:
    """
    دریافت قیمت لحظه‌ای.

    Args:
        coin: نماد ارز (BTC) — اگه None باشه، همه ارزها
    """
    url = f"{ABANTETHER_BASE}/api/v1/manager/otc/ticker"
    params = {"coin": coin} if coin else None

    data = _get(url, params)

    if not data:
        return None

    try:
        markets = data.get("data", {}).get("markets", {})
        if not markets:
            return None

        # اگه coin مشخص شده، فقط همون رو
        if coin:
            for key, info in markets.items():
                if info.get("symbol") == coin:
                    return _parse_ticker_info(coin, info)
            return None

        # همه رو برگردون
        result = {}
        for key, info in markets.items():
            sym = info.get("symbol")
            if sym:
                result[sym] = _parse_ticker_info(sym, info)
        return result

    except (KeyError, TypeError) as e:
        print(f"[Abantether] parse ticker: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۲. Coin Info (کارمزد و حدود معامله)
# ═══════════════════════════════════════════════════════════
def fetch_abantether_coin_info(symbol: str, side: str = "sell") -> Optional[dict]:
    """
    اطلاعات خرید/فروش با کارمزد.

    Args:
        symbol: BTC
        side: "buy" یا "sell"
    """
    url = f"{ABANTETHER_BASE}/api/v1/feecalculator/coin-info"
    params = {"symbol": symbol, "side": side}

    data = _get(url, params)

    if not data:
        return None

    try:
        info = data.get("data", {})
        if not info:
            return None

        return {
            "symbol": info.get("symbol", symbol),
            "persian_name": info.get("persian_name", ""),
            "exchange_fee": safe_num(info.get("exchange_fee")),
            "usdt_min_trade": safe_num(info.get("usdt_min_trade")),
            "usdt_max_trade": safe_num(info.get("usdt_max_trade")),
            "irt_min_trade": safe_num(info.get("irt_min_trade")),
            "irt_max_trade": safe_num(info.get("irt_max_trade")),
        }
    except (KeyError, TypeError) as e:
        print(f"[Abantether] parse coin info: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۳. تابع اصلی برای نماد داخلی
# ═══════════════════════════════════════════════════════════
def fetch_abantether_for_ticker(ticker: str) -> Optional[dict]:
    """
    دریافت قیمت لحظه‌ای برای نماد داخلی (BTC-USD → BTC).
    """
    coin = map_symbol_to_abantether(ticker)
    if not coin:
        print(f"[Abantether] نماد {ticker} پشتیبانی نمی‌شه")
        return None
    return fetch_abantether_ticker(coin)


# ═══════════════════════════════════════════════════════════
# ۴. قیمت لحظه‌ای (فقط عدد)
# ═══════════════════════════════════════════════════════════
def fetch_abantether_live_price(ticker: str) -> Optional[float]:
    """قیمت لحظه‌ای فقط به‌صورت عدد"""
    data = fetch_abantether_for_ticker(ticker)
    if data:
        return data.get("last_price")
    return None


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست core/abantether_fetcher.py — نسخه ۲.۰")
    print("=" * 60)
    print()

    print("۱) تعداد نمادها:")
    print(f"   {len(ABANTETHER_SYMBOLS)} نماد")
    print()

    print("۲) is_in_abantether:")
    for t in ["BTC-USD", "PAXG-USD", "USDT-IRT", "GC=F", "فولاد"]:
        print(f"   {t:12} → {is_in_abantether(t)}")
    print()

    print("۳) Ticker — BTC:")
    ticker = fetch_abantether_ticker("BTC")
    if ticker:
        print(f"   خرید: {ticker['buy_price']:,.0f} تومان")
        print(f"   فروش: {ticker['sell_price']:,.0f} تومان")
        print(f"   Spread: {ticker['spread_pct']:.3f}%")
        print(f"   فعال: {ticker['active']}")
    else:
        print("   ❌ خطا")
    print()

    print("۴) fetch_abantether_for_ticker:")
    for t in ["BTC-USD", "ETH-USD", "PAXG-USD"]:
        d = fetch_abantether_for_ticker(t)
        if d:
            print(f"   {t:12} → {d['last_price']:,.0f}")
        else:
            print(f"   {t:12} → ❌")
    print()

    print("۵) Coin Info — BTC:")
    info = fetch_abantether_coin_info("BTC")
    if info:
        print(f"   نام: {info['persian_name']}")
        print(f"   کارمزد: {info['exchange_fee']}")
    else:
        print("   ❌ خطا")
    print()

    print("[OK] تست کامل شد.")
