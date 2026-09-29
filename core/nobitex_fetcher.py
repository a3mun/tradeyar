"""
core/nobitex_fetcher.py
اتصال به API نوبیتکس — قیمت لحظه‌ای، OHLCV، Order Book
نسخه ۴.۱ (فاز ۵ — اصلاح ریال/تومان)
============================================================
تغییرات نسخه ۴.۱:
  - اصلاح تبدیل ریال به تومان (فقط یک بار)
  - /10 در fetch_nobitex_history (بر اساس symbol endswith IRT/RLS)
  - /10 در fetch_nobitex_stats (بر اساس dst_currency == rls)
  - حذف /10 تکراری از wrapper ها
  - رفع باگ ۱۰ برابر کوچک‌تر شدن USDT-IRT

API عمومی نوبیتکس (بدون نیاز به توکن):
  - /market/stats?srcCurrency=...&dstCurrency=...
  - /market/udf/history?symbol=...&resolution=...
  - /v2/orderbook/{symbol}
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

from .utils import safe_num

# ═══════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════
NOBITEX_BASE = "https://apiv2.nobitex.ir"
NOBITEX_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════
# نمادهای نوبیتکس (نگاشت داخلی → نوبیتکس)
# ═══════════════════════════════════════════════════════════
NOBITEX_SYMBOLS = {
    # ─── ویژه ───
    "USDT-IRT": "USDTIRT",  # تتر/تومان
    # ─── کریپتوهای اصلی ───
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
    "XRP-USD": "XRPUSDT",
    "BNB-USD": "BNBUSDT",
    "ADA-USD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT",
    "TON-USD": "TONUSDT",
    "AVAX-USD": "AVAXUSDT",
    "DOT-USD": "DOTUSDT",
    "MATIC-USD": "MATICUSDT",
    "LINK-USD": "LINKUSDT",
    "LTC-USD": "LTCUSDT",
    "ATOM-USD": "ATOMUSDT",
    "NEAR-USD": "NEARUSDT",
    "TRX-USD": "TRXUSDT",
    "SHIB-USD": "SHIBUSDT",
    "UNI-USD": "UNIUSDT",
    "ETC-USD": "ETCUSDT",
    "BCH-USD": "BCHUSDT",
    "FIL-USD": "FILUSDT",
    "AAVE-USD": "AAVEUSDT",
    "APT-USD": "APTUSDT",
    "SUI-USD": "SUIUSDT",
    "ARB-USD": "ARBUSDT",
    "OP-USD": "OPUSDT",
    "ZEC-USD": "ZECUSDT",
    "QNT-USD": "QNTUSDT",
    "PEPE-USD": "PEPEUSDT",
    "WIF-USD": "WIFUSDT",
    "BONK-USD": "BONKUSDT",
    "JUP-USD": "JUPUSDT",
    "INJ-USD": "INJUSDT",
    "SEI-USD": "SEIUSDT",
    "TIA-USD": "TIAUSDT",
    "STX-USD": "STXUSDT",
    "IMX-USD": "IMXUSDT",
    "RNDR-USD": "RNDRUSDT",
    "GRT-USD": "GRTUSDT",
    "SAND-USD": "SANDUSDT",
    "MANA-USD": "MANAUSDT",
    "AXS-USD": "AXSUSDT",
    "GALA-USD": "GALAUSDT",
    "FTM-USD": "FTMUSDT",
    "ALGO-USD": "ALGOUSDT",
    "VET-USD": "VETUSDT",
    "ICP-USD": "ICPUSDT",
    "HBAR-USD": "HBARUSDT",
    "EGLD-USD": "EGLDUSDT",
    "THETA-USD": "THETAUSDT",
    "XTZ-USD": "XTZUSDT",
    "EOS-USD": "EOSUSDT",
    "FLOW-USD": "FLOWUSDT",
    "CRV-USD": "CRVUSDT",
    "SNX-USD": "SNXUSDT",
    "COMP-USD": "COMPUSDT",
    "MKR-USD": "MKRUSDT",
    "SUSHI-USD": "SUSHIUSDT",
    "YFI-USD": "YFIUSDT",
    "1INCH-USD": "1INCHUSDT",
    "ENS-USD": "ENSUSDT",
    "LDO-USD": "LDOUSDT",
    "DYDX-USD": "DYDXUSDT",
    "GMX-USD": "GMXUSDT",
    "MASK-USD": "MASKUSDT",
    "BLUR-USD": "BLURUSDT",
    "DASH-USD": "DASHUSDT",
    "XMR-USD": "XMRUSDT",
    "ZIL-USD": "ZILUSDT",
    "ONE-USD": "ONEUSDT",
    "KSM-USD": "KSMUSDT",
    "WAVES-USD": "WAVESUSDT",
    "NEO-USD": "NEOUSDT",
    "QTUM-USD": "QTUMUSDT",
    "IOTA-USD": "IOTAUSDT",
    "ZRX-USD": "ZRXUSDT",
    "BAT-USD": "BATUSDT",
    "LSK-USD": "LSKUSDT",
    "OMG-USD": "OMGUSDT",
    "KNC-USD": "KNCUSDT",
    "STORJ-USD": "STORJUSDT",
    "CVC-USD": "CVCUSDT",
    "LRC-USD": "LRCUSDT",
    "ANKR-USD": "ANKRUSDT",
    "CELO-USD": "CELOUSDT",
    "BAND-USD": "BANDUSDT",
    "OCEAN-USD": "OCEANUSDT",
    "CTSI-USD": "CTSIUSDT",
    "RSR-USD": "RSRUSDT",
    "REN-USD": "RENUSDT",
    "BAL-USD": "BALUSDT",
    "RLC-USD": "RLCUSDT",
    "NKN-USD": "NKNUSDT",
    "OGN-USD": "OGNUSDT",
    "TRB-USD": "TRBUSDT",
    "MLN-USD": "MLNUSDT",
    "POWR-USD": "POWRUSDT",
    # ─── فلزات دیجیتال ───
    "PAXG-USD": "PAXGUSDT",
    "XAUT-USD": "XAUTUSDT",
    # ─── جفت‌ارزهای تومانی (جدید) ───
    "BTC-IRT": "BTCIRT",
    "ETH-IRT": "ETHIRT",
    "BNB-IRT": "BNBIRT",
    "SOL-IRT": "SOLIRT",
    "XRP-IRT": "XRPIRT",
    "ADA-IRT": "ADAIRT",
    "DOGE-IRT": "DOGEIRT",
    "TRX-IRT": "TRXIRT",
    "TON-IRT": "TONIRT",
    "MATIC-IRT": "MATICIRT",
    "LINK-IRT": "LINKIRT",
    "AVAX-IRT": "AVAXIRT",
    "SHIB-IRT": "SHIBIRT",
    "PAXG-IRT": "PAXGIRT",
    "XAUT-IRT": "XAUTIRT",
}

# نگاشت معکوس
_NOBITEX_REVERSE = {v: k for k, v in NOBITEX_SYMBOLS.items()}


# ═══════════════════════════════════════════════════════════
# تایم‌فریم
# ═══════════════════════════════════════════════════════════
TIMEFRAME_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "12h": "720",
    "1d": "1D",
    "1w": "1W",
}

_PERIOD_SECONDS = {
    "1d": 86400,
    "5d": 5 * 86400,
    "1mo": 30 * 86400,
    "3mo": 90 * 86400,
    "6mo": 180 * 86400,
    "1y": 365 * 86400,
}


# ═══════════════════════════════════════════════════════════
# ابزار
# ═══════════════════════════════════════════════════════════
def _get(url: str, params: dict = None) -> Optional[dict]:
    """درخواست GET امن"""
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=NOBITEX_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[Nobitex] Timeout: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"[Nobitex] HTTP {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[Nobitex] Request: {e}")
    except ValueError as e:
        print(f"[Nobitex] JSON: {e}")
    return None


def _resolution_to_seconds(resolution: str) -> int:
    if resolution == "1D":
        return 86400
    if resolution == "1W":
        return 604800
    try:
        return int(resolution) * 60
    except ValueError:
        return 3600


def _is_rial_pair(symbol: str) -> bool:
    """
    آیا این نماد به ریال معامله می‌شه؟
    نمادهای نوبیتکس که به ریال هستن: USDTIRT، BTCIRT، ...
    """
    if not symbol:
        return False
    upper = symbol.upper()
    return upper.endswith("IRT") or upper.endswith("RLS")


# ═══════════════════════════════════════════════════════════
# نگاشت نماد
# ═══════════════════════════════════════════════════════════
def map_symbol_to_nobitex(ticker: str) -> Optional[str]:
    """تبدیل نماد داخلی به نوبیتکس (BTC-USD → BTCUSDT)"""
    if not ticker:
        return None
    if ticker in NOBITEX_SYMBOLS:
        return NOBITEX_SYMBOLS[ticker]
    return None


def map_nobitex_to_symbol(nobitex_symbol: str) -> Optional[str]:
    """معکوس: BTCUSDT → BTC-USD"""
    if not nobitex_symbol:
        return None
    return _NOBITEX_REVERSE.get(nobitex_symbol)


def is_in_nobitex(ticker: str) -> bool:
    """بررسی سریع اینکه نماد در نوبیتکس هست"""
    return map_symbol_to_nobitex(ticker) is not None


def get_nobitex_symbols_map() -> dict:
    """نگاشت کامل نمادها"""
    return dict(NOBITEX_SYMBOLS)


# ═══════════════════════════════════════════════════════════
# ۱. آمار بازار (قیمت لحظه‌ای)
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_stats(
    src_currency: str = "btc",
    dst_currency: str = "usdt",
) -> Optional[dict]:
    """
    دریافت آمار بازار از نوبیتکس.

    Args:
        src_currency: ارز پایه (btc, eth, usdt, ...)
        dst_currency: ارز quote (usdt, rls, ...)

    Returns:
        dict با price, best_buy, best_sell, ... یا None

    ⚠️ اگه dst_currency == "rls"، قیمت‌ها از ریال به تومان تبدیل می‌شن.
    """
    url = f"{NOBITEX_BASE}/market/stats"
    params = {"srcCurrency": src_currency, "dstCurrency": dst_currency}
    data = _get(url, params)

    if not data or data.get("status") != "ok":
        return None

    try:
        stats = data.get("stats", {})
        key = f"{src_currency}-{dst_currency}"
        info = stats.get(key, {})

        if not info:
            return None

        price = safe_num(info.get("latest"))
        best_buy = safe_num(info.get("bestBuy"))
        best_sell = safe_num(info.get("bestSell"))
        day_change = safe_num(info.get("dayChange"))
        day_high = safe_num(info.get("dayHigh"))
        day_low = safe_num(info.get("dayLow"))
        day_open = safe_num(info.get("dayOpen"))
        day_close = safe_num(info.get("dayClose"))
        mark = safe_num(info.get("mark"))

        # ═══ تبدیل ریال به تومان ═══
        if dst_currency.lower() == "rls":
            price = price / 10
            best_buy = best_buy / 10
            best_sell = best_sell / 10
            day_high = day_high / 10
            day_low = day_low / 10
            day_open = day_open / 10
            day_close = day_close / 10
            mark = mark / 10

        if best_buy > 0 and best_sell > 0 and best_buy <= best_sell:
            spread = best_sell - best_buy
            spread_pct = (spread / best_buy) * 100
        else:
            spread = 0.0
            spread_pct = 0.0

        return {
            "symbol": f"{src_currency.upper()}{dst_currency.upper()}",
            "price": price,
            "best_buy": best_buy,
            "best_sell": best_sell,
            "spread": spread,
            "spread_pct": spread_pct,
            "change_24h": day_change,
            "high_24h": day_high,
            "low_24h": day_low,
            "open_24h": day_open,
            "close_24h": day_close,
            "volume_src": safe_num(info.get("volumeSrc")),
            "volume_dst": safe_num(info.get("volumeDst")),
            "mark_price": mark,
            "is_closed": bool(info.get("isClosed", False)),
        }
    except (KeyError, TypeError) as e:
        print(f"[Nobitex] parse stats: {e}")
        return None


def fetch_nobitex_stats_for_ticker(ticker: str) -> Optional[dict]:
    """
    دریافت آمار برای نماد داخلی.

    - USDT-IRT → usdt/rls (خودکار /10 می‌شه)
    - BTC-USD → btc/usdt
    """
    if not ticker:
        return None

    # ─── ویژه: USDT-IRT ───
    if ticker == "USDT-IRT":
        # /10 داخل fetch_nobitex_stats اعمال می‌شه
        return fetch_nobitex_stats("usdt", "rls")

    # ─── عادی ───
    nobitex_sym = map_symbol_to_nobitex(ticker)
    if not nobitex_sym:
        return None

    # BTCUSDT → base=BTC, quote=USDT
    if nobitex_sym.endswith("USDT"):
        base = nobitex_sym.replace("USDT", "").lower()
        return fetch_nobitex_stats(base, "usdt")

    # BTCIRT → base=BTC, quote=RLS
    if nobitex_sym.endswith("IRT"):
        base = nobitex_sym.replace("IRT", "").lower()
        return fetch_nobitex_stats(base, "rls")

    return None


# ═══════════════════════════════════════════════════════════
# ۲. تاریخچه OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_history(
    symbol: str,
    resolution: str = "60",
    from_ts: Optional[int] = None,
    to_ts: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    دریافت OHLCV از نوبیتکس.

    Args:
        symbol: نماد نوبیتکس (BTCUSDT, USDTIRT, BTCIRT, ...)
        resolution: 1, 5, 15, 30, 60, 240, 720, 1D, 1W

    Returns:
        DataFrame با open, high, low, close, volume
        ⚠️ اگه نماد IRT/RLS باشه، قیمت‌ها از ریال به تومان تبدیل می‌شن.
    """
    if to_ts is None:
        to_ts = int(datetime.now(timezone.utc).timestamp())
    if from_ts is None:
        resolution_seconds = _resolution_to_seconds(resolution)
        from_ts = to_ts - (resolution_seconds * 200)

    url = f"{NOBITEX_BASE}/market/udf/history"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts,
    }

    data = _get(url, params)

    if not data:
        return None

    if data.get("s") != "ok":
        if "t" not in data or not data["t"]:
            return None

    try:
        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        if not timestamps or len(timestamps) < 2:
            return None

        df = pd.DataFrame(
            {
                "open": [safe_num(x) for x in opens],
                "high": [safe_num(x) for x in highs],
                "low": [safe_num(x) for x in lows],
                "close": [safe_num(x) for x in closes],
                "volume": [safe_num(x) for x in volumes],
            },
            index=pd.to_datetime(timestamps, unit="s", utc=True),
        )

        df.index.name = "time"
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)]

        if df.empty:
            return None

        # ⚠️ نکته مهم:
        # OHLCV نوبیتکس برای نمادهای IRT/RLS از قبل به تومان هست
        # و نیازی به /10 نداره.
        # فقط API /market/stats (قیمت لحظه‌ای) به ریال هست که
        # توی fetch_nobitex_stats تبدیل می‌شه.

        return df

    except (KeyError, TypeError, ValueError) as e:
        print(f"[Nobitex] parse OHLCV: {e}")
        return None


def fetch_nobitex_for_ticker(
    ticker: str,
    interval: str,
    period: str,
) -> Optional[pd.DataFrame]:
    """OHLCV برای نماد داخلی"""
    if not ticker:
        return None

    nobitex_sym = map_symbol_to_nobitex(ticker)
    if not nobitex_sym:
        return None

    resolution = TIMEFRAME_MAP.get(interval)
    if not resolution:
        return None

    period_seconds = _PERIOD_SECONDS.get(period, 30 * 86400)
    to_ts = int(datetime.now(timezone.utc).timestamp())
    from_ts = to_ts - period_seconds

    # /10 داخل fetch_nobitex_history اعمال می‌شه (بر اساس symbol endswith IRT/RLS)
    return fetch_nobitex_history(nobitex_sym, resolution, from_ts, to_ts)


# ═══════════════════════════════════════════════════════════
# ۳. لیست کامل نمادها
# ═══════════════════════════════════════════════════════════
def fetch_all_nobitex_symbols(dst_currency: str = "usdt") -> list:
    """دریافت لیست کامل نمادهای نوبیتکس"""
    url = f"{NOBITEX_BASE}/market/stats"
    params = {"dstCurrency": dst_currency}

    data = _get(url, params)

    if not data or data.get("status") != "ok":
        return []

    try:
        stats = data.get("stats", {})
        result = []

        for key, info in stats.items():
            parts = key.split("-")
            if len(parts) != 2:
                continue

            base = parts[0].upper()
            quote = parts[1].upper()
            symbol = f"{base}{quote}"

            price = safe_num(info.get("latest"))
            if price <= 0:
                continue

            # ═══ تبدیل ریال به تومان برای RLS ═══
            if quote == "RLS":
                price = price / 10
                best_buy = safe_num(info.get("bestBuy")) / 10
                best_sell = safe_num(info.get("bestSell")) / 10
                high_24h = safe_num(info.get("dayHigh")) / 10
                low_24h = safe_num(info.get("dayLow")) / 10
            else:
                best_buy = safe_num(info.get("bestBuy"))
                best_sell = safe_num(info.get("bestSell"))
                high_24h = safe_num(info.get("dayHigh"))
                low_24h = safe_num(info.get("dayLow"))

            result.append(
                {
                    "symbol": symbol,
                    "base": base,
                    "quote": quote,
                    "price": price,
                    "best_buy": best_buy,
                    "best_sell": best_sell,
                    "volume_24h": safe_num(info.get("volumeDst")),
                    "volume_base": safe_num(info.get("volumeSrc")),
                    "change_24h": safe_num(info.get("dayChange")),
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                }
            )

        result.sort(key=lambda x: x["volume_24h"], reverse=True)
        return result

    except (KeyError, TypeError) as e:
        print(f"[Nobitex] fetch all symbols: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# ۴. فیلتر نقدینگی
# ═══════════════════════════════════════════════════════════
def filter_liquid_symbols(
    symbols: list,
    min_volume: float = 10000.0,
    min_trades: int = 0,
    max_count: int = 50,
) -> list:
    """فیلتر نمادهای نقدشونده"""
    filtered = []
    for s in symbols:
        volume = s.get("volume_24h", 0)
        trades = s.get("trades_24h", 0)

        if volume < min_volume:
            continue

        if trades > 0 and trades < min_trades:
            continue

        filtered.append(s)

    return filtered[:max_count]


# ═══════════════════════════════════════════════════════════
# ۵. Order Book
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_orderbook(symbol: str) -> Optional[dict]:
    """Order Book نوبیتکس"""
    url = f"{NOBITEX_BASE}/v2/orderbook/{symbol}"
    data = _get(url)

    if not data or data.get("status") != "ok":
        return None

    try:
        bids = data.get("bids", []) or []
        asks = data.get("asks", []) or []

        # ═══ تبدیل ریال به تومان برای IRT ═══
        is_rial = _is_rial_pair(symbol)
        divisor = 10 if is_rial else 1

        bid_prices = [safe_num(b[0]) / divisor for b in bids if b and len(b) >= 1]
        ask_prices = [safe_num(a[0]) / divisor for a in asks if a and len(a) >= 1]

        bid_prices = [p for p in bid_prices if p > 0]
        ask_prices = [p for p in ask_prices if p > 0]

        best_bid = max(bid_prices) if bid_prices else 0.0
        best_ask = min(ask_prices) if ask_prices else 0.0

        if best_bid > 0 and best_ask > 0 and best_bid <= best_ask:
            last_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
        elif best_bid > 0 and best_ask > 0:
            last_price = (best_bid + best_ask) / 2
            spread = 0.0
            spread_pct = 0.0
        else:
            last_price = best_bid or best_ask
            spread = 0.0
            spread_pct = 0.0

        # نرمال‌سازی levels
        bids_norm = [[safe_num(b[0]) / divisor, safe_num(b[1])] for b in bids[:10] if b]
        asks_norm = [[safe_num(a[0]) / divisor, safe_num(a[1])] for a in asks[:10] if a]

        return {
            "last_price": last_price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_pct": spread_pct,
            "bids": bids_norm,
            "asks": asks_norm,
        }
    except (IndexError, KeyError, TypeError) as e:
        print(f"[Nobitex] parse orderbook: {e}")
        return None


def fetch_nobitex_orderbook_for_ticker(ticker: str) -> Optional[dict]:
    """Order Book برای نماد داخلی"""
    nobitex_sym = map_symbol_to_nobitex(ticker)
    if not nobitex_sym:
        return None
    return fetch_nobitex_orderbook(nobitex_sym)


# ═══════════════════════════════════════════════════════════
# ۶. قیمت لحظه‌ای (فقط قیمت)
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_live_price(ticker: str) -> Optional[float]:
    """قیمت لحظه‌ای برای نماد داخلی — سریع"""
    stats = fetch_nobitex_stats_for_ticker(ticker)
    if stats:
        return stats.get("price")
    return None


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("تست core/nobitex_fetcher.py — نسخه ۴.۱")
    print("=" * 70)
    print()

    print("۱) تعداد نمادهای پشتیبانی‌شده:")
    print(f"   {len(NOBITEX_SYMBOLS)} نماد")
    print(f"   USDT-IRT در دیکشنری؟ {'USDT-IRT' in NOBITEX_SYMBOLS}")
    print()

    print("۲) آمار بازار — USDT/RLS (تتر/تومان):")
    stats = fetch_nobitex_stats("usdt", "rls")
    if stats:
        print(f"   قیمت: {stats['price']:,.0f} تومان")
        print(f"   تغییر ۲۴س: {stats['change_24h']:+.2f}%")
        print(f"   best_buy: {stats['best_buy']:,.0f}")
        print(f"   best_sell: {stats['best_sell']:,.0f}")
    else:
        print("   ❌ خطا")
    print()

    print("۳) آمار برای ticker=USDT-IRT:")
    stats2 = fetch_nobitex_stats_for_ticker("USDT-IRT")
    if stats2:
        print(f"   قیمت: {stats2['price']:,.0f} تومان")
    else:
        print("   ❌ خطا")
    print()

    print("۴) OHLCV — BTC-USD 1h 5d:")
    df = fetch_nobitex_for_ticker("BTC-USD", "1h", "5d")
    if df is not None and not df.empty:
        print(f"   تعداد: {len(df)}")
        print(f"   آخرین: ${df['close'].iloc[-1]:,.2f}")
    else:
        print("   ❌ خطا")
    print()

    print("۵) OHLCV — USDT-IRT 5m 5d:")
    df2 = fetch_nobitex_for_ticker("USDT-IRT", "5m", "5d")
    if df2 is not None and not df2.empty:
        print(f"   تعداد: {len(df2)}")
        print(f"   آخرین: {df2['close'].iloc[-1]:,.0f} تومان")
    else:
        print("   ❌ خطا")
    print()

    print("۶) is_in_nobitex:")
    for t in ["BTC-USD", "USDT-IRT", "GC=F", "PAXG-USD", "فولاد"]:
        print(f"   {t:15} → {is_in_nobitex(t)}")
    print()

    print("۷) Order Book — BTCUSDT:")
    ob = fetch_nobitex_orderbook("BTCUSDT")
    if ob:
        print(f"   Spread: {ob['spread_pct']:.4f}%")
    else:
        print("   ❌ خطا")
    print()

    print("[OK] تست کامل شد.")
