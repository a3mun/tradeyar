"""
core/nobitex_ws.py
WebSocket نوبیتکس (Centrifugo) — نسخه ۸.۰ (نهایی)
============================================================
🔴 چرا: REST API نوبیتکس ۷-۸ ثانیه تأخیر داره.
   WebSocket نوبیتکس قیمت رو لحظه‌ای push می‌کنه.

نسخه ۸.۰ — فاز ۱۶.۵ (نهایی):
  • کانال `public:orderbook-{SYMBOL}` (هر ۱ ثانیه پیام)
  • قیمت = `lastTradePrice` (دقیقاً همون «آخرین معامله» در پنل نوبیتکس)
  • `/10` برای IRT (نوبیتکس ریالی می‌ده)
  • logging دقیق برای دیباگ
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

NOBITEX_WS_URL = "wss://ws.nobitex.ir/connection/websocket"

# کش‌های سراسری
_nobitex_prices: dict[str, float] = {}
_nobitex_market_stats: dict[str, dict] = {}


# 🔴 کانال‌های اردربوک — سریع‌تر از market-stats (برای قیمت)
SUBSCRIBE_ORDERBOOK_CHANNELS = [
    "public:orderbook-BTCIRT",
    "public:orderbook-BTCUSDT",
    "public:orderbook-ETHIRT",
    "public:orderbook-ETHUSDT",
    "public:orderbook-USDTIRT",
    "public:orderbook-PAXGIRT",
    "public:orderbook-PAXGUSDT",
    "public:orderbook-XAUTIRT",
    "public:orderbook-XAUTUSDT",
    "public:orderbook-SOLUSDT",
    "public:orderbook-XRPUSDT",
    "public:orderbook-DOGEUSDT",
]

# 🔴 کانال‌های market-stats — برای change_pct (دقیق، ولی آهسته‌تر)
SUBSCRIBE_STATS_CHANNELS = [
    "public:market-stats-BTCIRT",
    "public:market-stats-BTCUSDT",
    "public:market-stats-ETHIRT",
    "public:market-stats-ETHUSDT",
    "public:market-stats-USDTIRT",
    "public:market-stats-PAXGIRT",
    "public:market-stats-PAXGUSDT",
    "public:market-stats-XAUTIRT",
    "public:market-stats-XAUTUSDT",
    "public:market-stats-SOLUSDT",
    "public:market-stats-XRPUSDT",
    "public:market-stats-DOGEUSDT",
]


def _nobitex_to_standard(symbol: str) -> Optional[str]:
    """BTCIRT → BTC-IRT | BTCUSDT → BTC-USD"""
    if not symbol:
        return None
    upper = symbol.upper()
    if upper.endswith("IRT"):
        return upper[:-3] + "-IRT"
    if upper.endswith("USDT"):
        return upper[:-4] + "-USD"
    return None


def _process_publication(channel: str, data: dict) -> None:
    """پردازش پیام منتشرشده از کانال (orderbook یا market-stats)"""
    try:
        if not isinstance(data, dict):
            return

        # ─── کانال orderbook → قیمت ───
        if channel.startswith("public:orderbook-"):
            symbol = channel.replace("public:orderbook-", "")
            ticker_std = _nobitex_to_standard(symbol)
            if not ticker_std:
                return

            last_price = data.get("lastTradePrice")
            if last_price is None:
                return

            try:
                price = float(last_price)
            except (TypeError, ValueError):
                return

            # 🔴 نوبیتکس `lastTradePrice` رو ریالی می‌ده؛ /10 برای IRT
            if ticker_std.endswith("-IRT"):
                price = price / 10.0

            _nobitex_prices[ticker_std] = price
            logger.debug(f"[NobitexWS] {ticker_std} = {price:,.2f} (orderbook)")
            return

        # ─── کانال market-stats → change_pct ───
        if channel.startswith("public:market-stats-"):
            symbol = channel.replace("public:market-stats-", "")
            ticker_std = _nobitex_to_standard(symbol)
            if not ticker_std:
                return

            # فقط stats رو ذخیره کن — قیمت همچنان از orderbook میاد
            _nobitex_market_stats[ticker_std] = data
            logger.debug(f"[NobitexWS] {ticker_std} stats updated")
            return

    except Exception as e:
        logger.debug(f"[NobitexWS] process error: {e!r}")


class _NobitexClientEventHandler(ClientEventHandler):
    """مدیریت رویدادهای سطح کلاینت"""

    async def on_connected(self, ctx: ConnectedContext) -> None:
        logger.info(f"[NobitexWS] connected — client={getattr(ctx, 'client', '?')}")

    async def on_disconnected(self, ctx) -> None:
        logger.warning(f"[NobitexWS] disconnected — code={getattr(ctx, 'code', '?')}")

    async def on_error(self, ctx) -> None:
        logger.warning(f"[NobitexWS] error — {getattr(ctx, 'error', ctx)}")


class _StatsHandler(SubscriptionEventHandler):
    """Handler برای کانال orderbook"""

    def __init__(self, channel: str):
        self.channel = channel

    async def on_publication(self, ctx: PublicationContext) -> None:
        try:
            data = ctx.pub.data
            _process_publication(self.channel, data)
        except Exception as e:
            logger.debug(f"[NobitexWS] handler error ({self.channel}): {e!r}")


async def _listen_nobitex():
    """حلقه‌ی اتصال با reconnect خودکار"""
    while True:
        try:
            client = Client(
                address=NOBITEX_WS_URL,
                events=_NobitexClientEventHandler(),
            )

            subscriptions = []
            all_channels = SUBSCRIBE_ORDERBOOK_CHANNELS + SUBSCRIBE_STATS_CHANNELS
            for channel in all_channels:
                handler = _StatsHandler(channel)
                sub = client.new_subscription(channel, handler)
                subscriptions.append(sub)

            await client.connect()
            logger.info(f"[NobitexWS] connected to {NOBITEX_WS_URL}")

            for sub in subscriptions:
                await sub.subscribe()
            logger.info(
                f"[NobitexWS] subscribed to {len(subscriptions)} channels "
                f"({len(SUBSCRIBE_ORDERBOOK_CHANNELS)} orderbook + "
                f"{len(SUBSCRIBE_STATS_CHANNELS)} market-stats)"
            )

            # SDK خودش ping/pong و reconnect رو مدیریت می‌کنه
            while True:
                await asyncio.sleep(30)
                if not getattr(client, "connected", True):
                    logger.warning("[NobitexWS] client disconnected — reconnecting")
                    break

        except asyncio.CancelledError:
            logger.info("[NobitexWS] listen cancelled")
            return
        except Exception as e:
            logger.warning(f"[NobitexWS] reconnect in 5s: {e!r}")
            await asyncio.sleep(5)


def start_nobitex_ws():
    """شروع WebSocket در پس‌زمینه (از lifespan صدا زده می‌شه)"""
    loop = asyncio.get_event_loop()
    loop.create_task(_listen_nobitex())
    logger.info("[NobitexWS] started")


def get_nobitex_price(ticker: str) -> Optional[float]:
    return _nobitex_prices.get(ticker.upper())


def get_nobitex_stats(ticker: str) -> Optional[dict]:
    return _nobitex_market_stats.get(ticker.upper())
