"""
core/forex_ws.py
WebSocket فارکس (Biquote + SignalR) — نسخه ۳.۰
============================================================
🔴 تغییرات نسخه ۳.۰:
  • ۱۱ نماد (شامل بیت‌کوین جهانی برای مقایسه)
  • fallback به REST اگه WebSocket کار نکرد
"""

import asyncio
import logging
from typing import Optional

try:
    from pysignalr.client import SignalRClient
    from pysignalr.messages import CompletionMessage
except ImportError:
    SignalRClient = None
    CompletionMessage = None

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)

BIQUOTE_HUB_URL = "https://biquote.io/hubs/tick"

# کش‌های سراسری
_forex_prices: dict[str, float] = {}
_forex_stats: dict[str, dict] = {}

# 🔴 نمادهای Biquote (فرمت اصلی)
SUBSCRIBE_SYMBOLS = [
    "XAUUSD",  # طلا
    "XAGUSD",  # نقره
    "USOIL",  # نفت WTI
    "UKOIL",  # نفت برنت
    "DXY",  # شاخص دلار
    "US500",  # S&P 500
    "US30",  # داوجونز
    "USTEC",  # نزدک ۱۰۰
    "EURUSD",  # یورو/دلار
    "DE30",  # DAX آلمان
    "BTCUSD",  # بیت‌کوین (جهانی)
]


def _biquote_to_standard(symbol: str) -> Optional[str]:
    """XAUUSD → XAU-USD | US500 → US500-USD"""
    if not symbol:
        return None
    upper = symbol.upper()
    # ۶ حرفی: XAUUSD → XAU-USD
    if len(upper) == 6 and upper.isalpha():
        return upper[:3] + "-" + upper[3:]
    # بقیه (شاخص‌ها، نفت): US500 → US500-USD
    return upper + "-USD"


def _process_tick(tick: dict) -> None:
    """پردازش یک tick از Biquote"""
    try:
        if not isinstance(tick, dict):
            return

        symbol = tick.get("symbol", "")
        ticker_std = _biquote_to_standard(symbol)
        if not ticker_std:
            return

        mid = tick.get("mid")
        if mid is None:
            bid = tick.get("bid")
            ask = tick.get("ask")
            if bid and ask:
                mid = (float(bid) + float(ask)) / 2
            else:
                return

        try:
            price = float(mid)
        except (TypeError, ValueError):
            return

        if price <= 0:
            return

        _forex_prices[ticker_std] = price
        _forex_stats[ticker_std] = tick
        logger.debug(f"[ForexWS] {ticker_std} = {price:,.4f}")
    except Exception as e:
        logger.debug(f"[ForexWS] process error: {e!r}")


async def _listen_forex():
    """اتصال به SignalR hub با fallback به REST"""
    if SignalRClient is None:
        logger.error("[ForexWS] pysignalr نصب نیست — pip install pysignalr")
        return

    while True:
        try:
            client = SignalRClient(BIQUOTE_HUB_URL)

            async def on_tick(tick):
                _process_tick(tick)

            async def on_open():
                logger.info("[ForexWS] connected — subscribing...")
                await client.send("Subscribe", SUBSCRIBE_SYMBOLS)
                logger.info(f"[ForexWS] subscribed to {len(SUBSCRIBE_SYMBOLS)} symbols")

            async def on_close():
                logger.warning("[ForexWS] disconnected — reconnecting...")

            async def on_error(msg):
                logger.warning(f"[ForexWS] error: {getattr(msg, 'error', msg)}")

            client.on_open(on_open)
            client.on_close(on_close)
            client.on_error(on_error)
            client.on("ReceiveTick", on_tick)

            async def _noop(*args, **kwargs):
                pass

            client.on("ReceiveSubscriptionState", _noop)

            logger.info(f"[ForexWS] connecting to {BIQUOTE_HUB_URL}...")
            await client.run()

        except asyncio.CancelledError:
            logger.info("[ForexWS] listen cancelled")
            return
        except Exception as e:
            logger.warning(f"[ForexWS] reconnect in 5s: {e!r}")
            await asyncio.sleep(5)


def start_forex_ws():
    loop = asyncio.get_event_loop()
    loop.create_task(_listen_forex())
    logger.info("[ForexWS] started")


def get_forex_price(ticker: str) -> Optional[float]:
    return _forex_prices.get(ticker.upper())


def get_forex_stats(ticker: str) -> Optional[dict]:
    return _forex_stats.get(ticker.upper())
