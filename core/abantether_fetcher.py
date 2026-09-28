"""
core/abantether_fetcher.py
اتصال به API آبان‌تتر — قیمت لحظه‌ای و Order Book
نسخه ۱.۰
================================================
API عمومی آبان‌تتر:
  - https://api.abantether.com/api/v1/feecalculator/coin-info?side=sell&symbol=BTC
  - https://api.abantether.com/api/v1/manager/otc/ticker
  - wss://ws.abantether.com/public (وب‌سوکت)

⚠️ توجه: API آبان‌تتر OHLCV (تاریخچه کندل) عمومی نداره.
   فقط قیمت لحظه‌ای و Order Book داره.
   برای OHLCV از نوبیتکس یا yfinance استفاده می‌کنیم.
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
# نگاشت نماد داخلی → نماد آبان‌تتر (فقط کریپتو)
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
}


# ═══════════════════════════════════════════════════════════
# ابزار کمکی
# ═══════════════════════════════════════════════════════════
def _get(url: str, params: dict = None) -> Optional[dict]:
    """درخواست GET امن با error handling"""
    try:
        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=ABANTETHER_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[Abantether] Timeout: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"[Abantether] HTTP Error {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[Abantether] Request Error: {e}")
    except ValueError as e:
        print(f"[Abantether] JSON Error: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# ۱. قیمت لحظه‌ای (Ticker)
# ═══════════════════════════════════════════════════════════
def fetch_abantether_ticker(coin: str = None) -> Optional[dict]:
    """
    دریافت قیمت لحظه‌ای از آبان‌تتر.
    
    Args:
        coin: نماد ارز (مثلاً BTC) — اگه None باشه، همه ارزها رو می‌گیره
    
    Returns:
        {
            "coin": "BTC",
            "buy_price": float,       # قیمت خرید (کاربر می‌خره)
            "sell_price": float,      # قیمت فروش (کاربر می‌فروشه)
            "spread": float,          # اختلاف خرید/فروش
            "spread_pct": float,      # درصد spread
            "buy_max": float,         # حداکثر خرید
            "sell_max": float,        # حداکثر فروش
            "active": bool,           # فعال یا نه
        }
        یا None
    """
    url = f"{ABANTETHER_BASE}/api/v1/manager/otc/ticker"
    params = {"coin": coin} if coin else None
    
    data = _get(url, params)
    
    if not data:
        return None
    
    try:
        # پاسخ آبان‌تتر ساختار {"data": {"markets": {...}}} داره
        markets = data.get("data", {}).get("markets", {})
        
        if not markets:
            # اگه coin مشخص شده و پیدا نشد
            return None
        
        # اگه coin مشخص شده، فقط همون رو برگردون
        if coin:
            # کلیدها مثل BTCIRT، ETHIRT، BTCUSDT، ...
            # بگرد دنبال کلیدی که با coin شروع بشه
            for key, info in markets.items():
                if info.get("symbol") == coin:
                    return _parse_ticker_info(coin, info)
            return None
        
        # اگه coin مشخص نشده، همه رو برگردون
        result = {}
        for key, info in markets.items():
            sym = info.get("symbol")
            if sym:
                result[sym] = _parse_ticker_info(sym, info)
        return result
    
    except (KeyError, TypeError) as e:
        print(f"[Abantether] Error parsing ticker: {e}")
        return None


def _parse_ticker_info(coin: str, info: dict) -> dict:
    """پارس یه آیتم ticker"""
    buy_price = safe_num(info.get("buy_price"))
    sell_price = safe_num(info.get("sell_price"))
    
    if buy_price > 0 and sell_price > 0:
        # spread = اختلاف بین خرید و فروش
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


# ═══════════════════════════════════════════════════════════
# ۲. قیمت خرید/فروش (Fee Calculator)
# ═══════════════════════════════════════════════════════════
def fetch_abantether_coin_info(symbol: str, side: str = "sell") -> Optional[dict]:
    """
    دریافت اطلاعات خرید/فروش از آبان‌تتر (با کارمزد).
    
    Args:
        symbol: نماد ارز (مثلاً BTC)
        side: "buy" یا "sell"
    
    Returns:
        {
            "symbol": "BTC",
            "persian_name": "بیت‌کوین",
            "exchange_fee": float,     # کارمزد صرافی
            "usdt_min_trade": float,   # حداقل معامله تتر
            "usdt_max_trade": float,   # حداکثر معامله تتر
            "irt_min_trade": float,    # حداقل معامله تومان
            "irt_max_trade": float,    # حداکثر معامله تومان
        }
        یا None
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
        print(f"[Abantether] Error parsing coin info: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۳. نگاشت نماد
# ═══════════════════════════════════════════════════════════
def map_symbol_to_abantether(ticker: str) -> Optional[str]:
    """
    تبدیل نماد داخلی ما به نماد آبان‌تتر.
    
    Args:
        ticker: نماد داخلی (مثلاً BTC-USD)
    
    Returns:
        نماد آبان‌تتر (BTC) یا None
    """
    return ABANTETHER_SYMBOLS.get(ticker)


# ═══════════════════════════════════════════════════════════
# ۴. تابع اصلی: دریافت قیمت لحظه‌ای برای نماد ما
# ═══════════════════════════════════════════════════════════
def fetch_abantether_for_ticker(ticker: str) -> Optional[dict]:
    """
    دریافت قیمت لحظه‌ای برای نماد داخلی ما (BTC-USD → BTC).
    
    Args:
        ticker: نماد داخلی (مثلاً BTC-USD)
    
    Returns:
        اطلاعات ticker یا None
    """
    coin = map_symbol_to_abantether(ticker)
    if not coin:
        print(f"[Abantether] نماد {ticker} پشتیبانی نمی‌شه")
        return None
    
    return fetch_abantether_ticker(coin)


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست core/abantether_fetcher.py")
    print("=" * 60)
    print()
    
    # ─── تست Ticker برای یه نماد ───
    print("۱) Ticker — BTC:")
    ticker = fetch_abantether_ticker("BTC")
    if ticker:
        print(f"   خرید: {ticker['buy_price']:,.0f} تومان")
        print(f"   فروش: {ticker['sell_price']:,.0f} تومان")
        print(f"   Spread: {ticker['spread_pct']:.3f}%")
        print(f"   فعال: {ticker['active']}")
    else:
        print("   ❌ خطا")
    print()
    
    # ─── تست Ticker برای همه ───
    print("۲) Ticker — همه ارزها:")
    all_tickers = fetch_abantether_ticker()
    if all_tickers:
        print(f"   تعداد: {len(all_tickers)}")
        for sym in list(all_tickers.keys())[:5]:
            print(f"   {sym}: {all_tickers[sym]['last_price']:,.0f}")
    else:
        print("   ❌ خطا")
    print()
    
    # ─── تست Coin Info ───
    print("۳) Coin Info — BTC:")
    info = fetch_abantether_coin_info("BTC")
    if info:
        print(f"   نام: {info['persian_name']}")
        print(f"   کارمزد: {info['exchange_fee']}")
        print(f"   حداکثر تومان: {info['irt_max_trade']:,.0f}")
    else:
        print("   ❌ خطا")
    print()
    
    # ─── تست نمادهای مختلف ───
    print("۴) تست چند نماد:")
    for ticker in ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F"]:
        sym = map_symbol_to_abantether(ticker)
        print(f"   {ticker} → {sym if sym else '❌ پشتیبانی نمی‌شه'}")
    print()
    
    print("[OK] تست کامل شد.")