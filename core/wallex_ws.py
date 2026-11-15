"""
core/wallex_ws.py
WebSocket والکس (Centrifugo) — نسخه ۱.۰
============================================================
🔴 چرا: REST API والکس تاخیر داره.
   WebSocket والکس قیمت رو لحظه‌ای push می‌کنه.

نسخه ۱.۰ — فاز ۱۶.۵:
  • کانال `public:all@price` — قیمت + change_24h همه بازارها
  • SDK رسمی Centrifugo (`centrifuge-python==0.7.0`)
  • پشتیبانی از همه نمادها (TMN و USDT)
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

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)

WALLEX_WS_URL = "wss://api.wallex.ir/connection/websocket"

# کش‌های سراسری
_wallex_prices: dict[str, float] = {}
_wallex_market_stats: dict[str, dict] = {}

# کانال عمومی قیمت همه بازارها
PRICE_CHANNEL = "public:all@price"


def _wallex_to_standard(symbol: str) -> Optional[str]:
    """BTCTMN → BTC-IRT | BTCUSDT → BTC-USD"""
    if not symbol:
        return None
    upper = symbol.upper()
    if upper.endswith("TMN"):
        return upper[:-3] + "-IRT"
    if upper.endswith("USDT"):
        return upper[:-4] + "-USD"
    return None


def _process_publication(channel: str, data: dict) -> None:
    """پردازش پیام منتشرشده از کانال (public:all@price)"""
    try:
        if channel != PRICE_CHANNEL:
            return

        if not isinstance(data, dict):
            return

        symbol = data.get("symbol", "")
        ticker_std = _wallex_to_standard(symbol)
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

        _wallex_prices[ticker_std] = price
        _wallex_market_stats[ticker_std] = data
        logger.debug(f"[WallexWS] {ticker_std} = {price:,.2f}")
    except Exception as e:
        logger.debug(f"[WallexWS] process error: {e!r}")


class _WallexClientEventHandler(ClientEventHandler):
    async def on_connected(self, ctx: ConnectedContext) -> None:
        logger.info(f"[WallexWS] connected — client={getattr(ctx, 'client', '?')}")

    async def on_disconnected(self, ctx) -> None:
        logger.warning(f"[WallexWS] disconnected — code={getattr(ctx, 'code', '?')}")

    async def on_error(self, ctx) -> None:
        logger.warning(f"[WallexWS] error — {getattr(ctx, 'error', ctx)}")


class _PriceHandler(SubscriptionEventHandler):
    def __init__(self, channel: str):
        self.channel = channel

    async def on_publication(self, ctx: PublicationContext) -> None:
        try:
            data = ctx.pub.data
            _process_publication(self.channel, data)
        except Exception as e:
            logger.debug(f"[WallexWS] handler error ({self.channel}): {e!r}")


async def _listen_wallex():
    while True:
        try:
            client = Client(
                address=WALLEX_WS_URL,
                events=_WallexClientEventHandler(),
            )

            handler = _PriceHandler(PRICE_CHANNEL)
            sub = client.new_subscription(PRICE_CHANNEL, handler)

            await client.connect()
            logger.info(f"[WallexWS] connected to {WALLEX_WS_URL}")

            await sub.subscribe()
            logger.info(f"[WallexWS] subscribed to {PRICE_CHANNEL}")

            while True:
                await asyncio.sleep(30)
                if not getattr(client, "connected", True):
                    logger.warning("[WallexWS] client disconnected — reconnecting")
                    break

        except asyncio.CancelledError:
            logger.info("[WallexWS] listen cancelled")
            return
        except Exception as e:
            logger.warning(f"[WallexWS] reconnect in 5s: {e!r}")
            await asyncio.sleep(5)


def start_wallex_ws():
    loop = asyncio.get_event_loop()
    loop.create_task(_listen_wallex())
    logger.info("[WallexWS] started")


def get_wallex_price(ticker: str) -> Optional[float]:
    return _wallex_prices.get(ticker.upper())


def get_wallex_stats(ticker: str) -> Optional[dict]:
    return _wallex_market_stats.get(ticker.upper())