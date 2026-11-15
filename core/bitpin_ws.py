"""
core/bitpin_ws.py
WebSocket بیت‌پین (Centrifugo) — نسخه ۱.۰
============================================================
🔴 چرا: REST API بیت‌پین تاخیر داره.
   WebSocket بیت‌پین قیمت رو لحظه‌ای push می‌کنه.

نسخه ۱.۰ — فاز ۱۶.۵:
  • کانال `market:{SYMBOL}` — قیمت + تغییر ۲۴ ساعته
  • `currency_price_update` با هر معامله (سریع)
  • `candle_update` هر ۱۰ ثانیه (برای کندل، اگر لازم شد)
  • SDK رسمی Centrifugo (`centrifuge-python==0.7.0`)
"""

import asyncio
import logging
from typing import Optional

from centrifuge import (
    Client,
    ClientEventHandler,
    ConnectedContext,
    SubscriptionEventHandler,
    PublicationContext,
)

# 🔴 تنظیم logging — فقط اگر قبلاً تنظیم نشده باشه
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)

BITPIN_WS_URL = "wss://centrifugo.bitpin.ir/connection/websocket"

# کش‌های سراسری
_bitpin_prices: dict[str, float] = {}
_bitpin_market_stats: dict[str, dict] = {}

# 🔴 نمادها (فرمت بیت‌پین: BTC_IRT، BTC_USDT)
# این‌ها رو از core.bitpin_fetcher.map_symbol_to_bitpin می‌گیریم

SUBSCRIBE_SYMBOLS = [
    "BTC_IRT",
    "BTC_USDT",
    "ETH_IRT",
    "ETH_USDT",
    "USDT_IRT",
    "PAXG_IRT",
    "PAXG_USDT",
    "XAUT_IRT",
    "XAUT_USDT",
    "SOL_USDT",
    "XRP_USDT",
    "DOGE_USDT",
]

# 🔴 هر نماد در دو کانال: market (قیمت + change) و matches (هر معامله)
SUBSCRIBE_CHANNELS = [f"market:{s}" for s in SUBSCRIBE_SYMBOLS] + [
    f"matches:{s}" for s in SUBSCRIBE_SYMBOLS
]


def _bitpin_to_standard(symbol: str) -> Optional[str]:
    """BTC_IRT → BTC-IRT | BTC_USDT → BTC-USD"""
    if not symbol:
        return None
    upper = symbol.upper()
    if upper.endswith("_IRT"):
        return upper[:-4] + "-IRT"
    if upper.endswith("_USDT"):
        return upper[:-5] + "-USD"
    return None


def _process_publication(channel: str, data: dict) -> None:
    """پردازش پیام منتشرشده از کانال (market یا matches)"""
    try:
        if not isinstance(data, dict):
            return

        event = data.get("event")

        # ─── candle_update (از market:) — قیمت از آخرین کندل ───
        if event == "candle_update":
            candles = data.get("candles") or []
            if not candles:
                return

            last = candles[-1]
            close_str = last.get("close")
            if close_str is None:
                return

            try:
                price = float(close_str)
            except (TypeError, ValueError):
                return

            if price <= 0:
                return

            symbol = data.get("market", {}).get("code", "") or data.get("symbol", "")
            ticker_std = _bitpin_to_standard(symbol)
            if not ticker_std:
                return

            _bitpin_prices[ticker_std] = price
            logger.debug(f"[BitpinWS] {ticker_std} = {price:,.2f} (candle)")
            return

        # ─── currency_price_update (از market:) ───
        if event == "currency_price_update":
            symbol = data.get("symbol", "")
            ticker_std = _bitpin_to_standard(symbol)
            if not ticker_std:
                return

            price_str = data.get("price")
            if price_str is None:
                return

            try:
                price = float(price_str)
            except (TypeError, ValueError):
                return

            if price <= 0:
                return

            _bitpin_prices[ticker_std] = price
            _bitpin_market_stats[ticker_std] = data
            logger.debug(f"[BitpinWS] {ticker_std} = {price:,.2f} (market)")
            return

        # ─── matches_update (از matches:) ───
        if event == "matches_update":
            symbol = data.get("symbol", "")
            ticker_std = _bitpin_to_standard(symbol)
            if not ticker_std:
                return

            matches = data.get("matches") or []
            if not matches:
                return

            last = matches[-1]
            price_str = last.get("price")
            if price_str is None:
                return

            try:
                price = float(price_str)
            except (TypeError, ValueError):
                return

            if price <= 0:
                return

            _bitpin_prices[ticker_std] = price
            logger.debug(f"[BitpinWS] {ticker_std} = {price:,.2f} (match)")
            return

    except Exception as e:
        logger.debug(f"[BitpinWS] process error: {e!r}")


class _BitpinClientEventHandler(ClientEventHandler):
    """مدیریت رویدادهای سطح کلاینت"""

    async def on_connected(self, ctx: ConnectedContext) -> None:
        logger.info(f"[BitpinWS] connected — client={getattr(ctx, 'client', '?')}")

    async def on_disconnected(self, ctx) -> None:
        logger.warning(f"[BitpinWS] disconnected — code={getattr(ctx, 'code', '?')}")

    async def on_error(self, ctx) -> None:
        logger.warning(f"[BitpinWS] error — {getattr(ctx, 'error', ctx)}")


class _MarketHandler(SubscriptionEventHandler):
    """Handler برای کانال market:SYMBOL"""

    def __init__(self, channel: str):
        self.channel = channel

    async def on_publication(self, ctx: PublicationContext) -> None:
        try:
            data = ctx.pub.data
            _process_publication(self.channel, data)
        except Exception as e:
            logger.debug(f"[BitpinWS] handler error ({self.channel}): {e!r}")


async def _listen_bitpin():
    """حلقه‌ی اتصال با reconnect خودکار"""
    while True:
        try:
            client = Client(
                address=BITPIN_WS_URL,
                events=_BitpinClientEventHandler(),
            )

            subscriptions = []
            for channel in SUBSCRIBE_CHANNELS:
                handler = _MarketHandler(channel)
                sub = client.new_subscription(channel, handler)
                subscriptions.append(sub)

            await client.connect()
            logger.info(f"[BitpinWS] connected to {BITPIN_WS_URL}")

            for sub in subscriptions:
                await sub.subscribe()
            logger.info(f"[BitpinWS] subscribed to {len(subscriptions)} channels")

            # SDK خودش ping/pong و reconnect رو مدیریت می‌کنه
            while True:
                await asyncio.sleep(30)
                if not getattr(client, "connected", True):
                    logger.warning("[BitpinWS] client disconnected — reconnecting")
                    break

        except asyncio.CancelledError:
            logger.info("[BitpinWS] listen cancelled")
            return
        except Exception as e:
            logger.warning(f"[BitpinWS] reconnect in 5s: {e!r}")
            await asyncio.sleep(5)


def start_bitpin_ws():
    """شروع WebSocket در پس‌زمینه (از lifespan صدا زده می‌شه)"""
    loop = asyncio.get_event_loop()
    loop.create_task(_listen_bitpin())
    logger.info("[BitpinWS] started")


def get_bitpin_price(ticker: str) -> Optional[float]:
    return _bitpin_prices.get(ticker.upper())


def get_bitpin_stats(ticker: str) -> Optional[dict]:
    return _bitpin_market_stats.get(ticker.upper())
