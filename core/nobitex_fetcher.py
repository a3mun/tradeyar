"""
core/nobitex_fetcher.py
اتصال به API نوبیتکس — قیمت لحظه‌ای، OHLCV، Order Book، لیست خودکار نمادها
نسخه ۳.۰ (نهایی)
================================================
API عمومی نوبیتکس (بدون نیاز به توکن):
  - https://apiv2.nobitex.ir/market/stats?dstCurrency=usdt
  - https://apiv2.nobitex.ir/market/udf/history?symbol=BTCUSDT&resolution=5&from=...&to=...
  - https://apiv2.nobitex.ir/v2/orderbook/{symbol}

نکات مهم:
  - نوبیتکس ترجیحاً با dstCurrency=usdt کار می‌کنه (تتری)
  - فیلد dayChange در API درصد هست (نه واحد پول)
  - volumeDst = حجم به تتر، volumeSrc = حجم به ارز پایه
  - bestBuy و bestSell مستقیم از API میان (نیازی به Order Book نیست)
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
# نمادهای نوبیتکس (گسترش‌یافته)
# ═══════════════════════════════════════════════════════════
NOBITEX_SYMBOLS = {
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
    "GRAM-USD": "GRAMUSDT",
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
}


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
            timeout=NOBITEX_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[Nobitex] Timeout: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"[Nobitex] HTTP Error {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[Nobitex] Request Error: {e}")
    except ValueError as e:
        print(f"[Nobitex] JSON Error: {e}")
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


def _period_to_seconds(period: str) -> int:
    mapping = {
        "1d": 86400,
        "5d": 5 * 86400,
        "1mo": 30 * 86400,
        "3mo": 90 * 86400,
        "6mo": 180 * 86400,
        "1y": 365 * 86400,
    }
    return mapping.get(period, 30 * 86400)


# ═══════════════════════════════════════════════════════════
# ۱. آمار بازار
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_stats(
    src_currency: str = "btc",
    dst_currency: str = "usdt",
) -> Optional[dict]:
    """دریافت آمار کامل بازار از نوبیتکس"""
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
            "high_24h": safe_num(info.get("dayHigh")),
            "low_24h": safe_num(info.get("dayLow")),
            "open_24h": safe_num(info.get("dayOpen")),
            "close_24h": safe_num(info.get("dayClose")),
            "volume_src": safe_num(info.get("volumeSrc")),
            "volume_dst": safe_num(info.get("volumeDst")),
            "mark_price": safe_num(info.get("mark")),
            "is_closed": bool(info.get("isClosed", False)),
        }
    except (KeyError, TypeError) as e:
        print(f"[Nobitex] Error parsing stats: {e}")
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
    """دریافت OHLCV از نوبیتکس"""
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

        df = pd.DataFrame({
            "open": [safe_num(x) for x in opens],
            "high": [safe_num(x) for x in highs],
            "low": [safe_num(x) for x in lows],
            "close": [safe_num(x) for x in closes],
            "volume": [safe_num(x) for x in volumes],
        }, index=pd.to_datetime(timestamps, unit="s", utc=True))

        df.index.name = "time"
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)]

        if df.empty:
            return None

        return df

    except (KeyError, TypeError, ValueError) as e:
        print(f"[Nobitex] Error parsing OHLCV: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# ۳. نگاشت نماد
# ═══════════════════════════════════════════════════════════
def map_symbol_to_nobitex(ticker: str) -> Optional[str]:
    """تبدیل نماد داخلی به نماد نوبیتکس"""
    if ticker in NOBITEX_SYMBOLS:
        return NOBITEX_SYMBOLS[ticker]

    # تبدیل خودکار
    if ticker.endswith("-USD"):
        base = ticker.replace("-USD", "").upper()
        candidate = f"{base}USDT"

        try:
            stats = fetch_nobitex_stats(base.lower(), "usdt")
            if stats and stats.get("price", 0) > 0:
                NOBITEX_SYMBOLS[ticker] = candidate
                return candidate
        except Exception:
            pass

    return None


# ═══════════════════════════════════════════════════════════
# ۴. OHLCV برای نماد ما
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_for_ticker(
    ticker: str,
    interval: str,
    period: str,
) -> Optional[pd.DataFrame]:
    """دریافت OHLCV برای نماد داخلی ما"""
    nobitex_symbol = map_symbol_to_nobitex(ticker)
    if not nobitex_symbol:
        if ticker.endswith("-USD"):
            base = ticker.replace("-USD", "").upper()
            nobitex_symbol = f"{base}USDT"
        else:
            print(f"[Nobitex] نماد {ticker} پشتیبانی نمی‌شه")
            return None

    resolution = TIMEFRAME_MAP.get(interval)
    if not resolution:
        print(f"[Nobitex] تایم‌فریم {interval} پشتیبانی نمی‌شه")
        return None

    period_seconds = _period_to_seconds(period)
    to_ts = int(datetime.now(timezone.utc).timestamp())
    from_ts = to_ts - period_seconds

    return fetch_nobitex_history(nobitex_symbol, resolution, from_ts, to_ts)


# ═══════════════════════════════════════════════════════════
# ۵. لیست کامل نمادها
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

            result.append({
                "symbol": symbol,
                "base": base,
                "quote": quote,
                "price": price,
                "best_buy": safe_num(info.get("bestBuy")),
                "best_sell": safe_num(info.get("bestSell")),
                "volume_24h": safe_num(info.get("volumeDst")),
                "volume_base": safe_num(info.get("volumeSrc")),
                "trades_24h": 0,
                "change_24h": safe_num(info.get("dayChange")),
                "high_24h": safe_num(info.get("dayHigh")),
                "low_24h": safe_num(info.get("dayLow")),
            })

        result.sort(key=lambda x: x["volume_24h"], reverse=True)
        return result

    except (KeyError, TypeError) as e:
        print(f"[Nobitex] Error fetching all symbols: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# ۶. فیلتر نقدینگی
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
# ۷. Order Book
# ═══════════════════════════════════════════════════════════
def fetch_nobitex_orderbook(symbol: str) -> Optional[dict]:
    """دریافت Order Book از نوبیتکس"""
    url = f"{NOBITEX_BASE}/v2/orderbook/{symbol}"
    data = _get(url)

    if not data or data.get("status") != "ok":
        return None

    try:
        bids = data.get("bids", []) or []
        asks = data.get("asks", []) or []

        bid_prices = [safe_num(b[0]) for b in bids if b and len(b) >= 1]
        ask_prices = [safe_num(a[0]) for a in asks if a and len(a) >= 1]

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

        return {
            "last_price": last_price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_pct": spread_pct,
            "bids": bids[:10],
            "asks": asks[:10],
        }
    except (IndexError, KeyError, TypeError) as e:
        print(f"[Nobitex] Error parsing orderbook: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("تست core/nobitex_fetcher.py (نسخه ۳.۰)")
    print("=" * 70)
    print()

    print("۱) آمار بازار — BTC/USDT:")
    stats = fetch_nobitex_stats("btc", "usdt")
    if stats:
        print(f"   قیمت: ${stats['price']:,.2f}")
        print(f"   Spread: {stats['spread_pct']:.4f}%")
        print(f"   تغییر ۲۴س: {stats['change_24h']:+.2f}%")
        print(f"   حجم به تتر: {stats['volume_dst']:,.2f} USDT")
    else:
        print("   ❌ خطا")
    print()

    print("۲) OHLCV — BTC-USD 1h 5d:")
    df = fetch_nobitex_for_ticker("BTC-USD", "1h", "5d")
    if df is not None and not df.empty:
        print(f"   تعداد کندل: {len(df)}")
        print(f"   آخرین قیمت: ${df['close'].iloc[-1]:,.2f}")
    else:
        print("   ❌ خطا")
    print()

    print("۳) لیست کامل نمادها:")
    all_syms = fetch_all_nobitex_symbols("usdt")
    if all_syms:
        print(f"   ✅ تعداد کل: {len(all_syms)}")
        for s in all_syms[:5]:
            print(f"   {s['symbol']:12} | ${s['price']:>12,.4f} | حجم: {s['volume_24h']:>15,.0f} USDT")
    else:
        print("   ❌ خطا")
    print()

    print("۴) فیلتر نقدینگی:")
    liquid = filter_liquid_symbols(all_syms, min_volume=10000, max_count=50)
    print(f"   ✅ تعداد بعد از فیلتر: {len(liquid)}")
    print()

    print("۵) Order Book — BTCUSDT:")
    ob = fetch_nobitex_orderbook("BTCUSDT")
    if ob:
        print(f"   آخرین قیمت: ${ob['last_price']:,.2f}")
        print(f"   Spread: {ob['spread_pct']:.4f}%")
    else:
        print("   ❌ خطا")
    print()

    print("[OK] تست کامل شد.")