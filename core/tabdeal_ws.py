"""
core/tabdeal_ws.py
WebSocket تبدیل — قیمت لحظه‌ای و ساخت کندل (فاز ۱۶.۴)
"""

import asyncio
import json
import logging
from typing import Optional

import websockets

logger = logging.getLogger(__name__)

TABDEAL_WS = "wss://api1.tabdeal.org/stream/"

# کش سراسری
_tabdeal_prices: dict[str, float] = {}
_tabdeal_depths: dict[str, dict] = {}

# ═══════════════════════════════════════════════════════════
# لیست نمادهای پرمعامله برای subscribe (مثل FIXED_SYMBOLS)
# ═══════════════════════════════════════════════════════════
_TABDEAL_SUBSCRIBE_SYMBOLS = [
    # 🔴 فاز ۱۶.۶ — تتر (خیلی مهم، پر معامله‌ترین نماد)
    "usdtirt",
    "usdtusdt",  # معادل USDT-USD
    # بقیه نمادها
    "btcirt",
    "btcusdt",
    "ethirt",
    "ethusdt",
    "paxgirt",
    "paxgusdt",
    "xautirt",
    "xautusdt",
    "solusdt",
    "solirt",
    "xrpusdt",
    "xrpirt",
    "dogeusdt",
    "dogeirt",
    "bnbusdt",
    "bnbirt",
    "adausdt",
    "adairt",
    "tonusdt",
    "tonirt",
    "trxusdt",
    "trxirt",
    "ltcusdt",
    "ltcirt",
    "linkusdt",
    "linkirt",
    "shibusdt",
    "shibirt",
    "dotusdt",
    "dotirt",
]


def _tabdeal_to_standard(symbol: str) -> Optional[str]:
    """
    تبدیل نماد تبدیل به فرمت استاندارد ما
    BTCIRT → BTC-IRT
    BTCUSDT → BTC-USD
    """
    if not symbol:
        return None
    upper = symbol.upper()
    if upper.endswith("IRT"):
        return upper[:-3] + "-IRT"
    if upper.endswith("USDT"):
        return upper[:-4] + "-USD"
    return None


async def _listen_tabdeal():
    """اتصال دائمی به WebSocket تبدیل با reconnect خودکار"""
    while True:
        try:
            async with websockets.connect(
                TABDEAL_WS,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                # subscribe به depth
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": [f"{s}@depth@2000ms" for s in _TABDEAL_SUBSCRIBE_SYMBOLS],
                    "id": 1,
                }
                await ws.send(json.dumps(subscribe_msg))
                logger.info(
                    f"[TabdealWS] subscribed to {len(_TABDEAL_SUBSCRIBE_SYMBOLS)} symbols"
                )

                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        stream = data.get("stream", "")
                        payload = data.get("data", {})

                        if "@depth" in stream:
                            symbol = stream.split("@")[0].upper()  # btcirt → BTCIRT
                            bids = payload.get("b", [])
                            asks = payload.get("a", [])

                            if bids and asks:
                                best_bid = float(bids[0][0])
                                best_ask = float(asks[0][0])
                                mid = (best_bid + best_ask) / 2
                                spread_pct = (
                                    ((best_ask - best_bid) / mid * 100) if mid else 0.0
                                )

                                bid_vol = sum(float(b[1]) for b in bids)
                                ask_vol = sum(float(a[1]) for a in asks)
                                total_vol = bid_vol + ask_vol

                                _tabdeal_prices[symbol] = mid
                                _tabdeal_depths[symbol] = {
                                    "price": mid,
                                    "best_bid": best_bid,
                                    "best_ask": best_ask,
                                    "spread_pct": spread_pct,
                                    "bid_volume": bid_vol,
                                    "ask_volume": ask_vol,
                                    "total_volume": total_vol,
                                }
                                # 🔴 بلاک candle_builder حذف شد (فاز ۱۶.۶)

                    except Exception as e:
                        logger.debug(f"[TabdealWS] parse error: {e}")

        except Exception as e:
            logger.warning(f"[TabdealWS] connection error: {e} — reconnect in 5s")
            await asyncio.sleep(5)


def start_tabdeal_ws():
    """شروع WebSocket در پس‌زمینه (از lifespan صدا زده می‌شه)"""
    loop = asyncio.get_event_loop()
    loop.create_task(_listen_tabdeal())
    logger.info("[TabdealWS] started")


def get_tabdeal_price(ticker: str) -> Optional[dict]:
    """قیمت لحظه‌ای از کش WebSocket"""
    symbol = ticker.upper().replace("-", "").replace("_", "")
    return _tabdeal_depths.get(symbol)
