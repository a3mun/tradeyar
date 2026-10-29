"""
services/ws_manager.py
مدیریت اتصالات WebSocket + broadcast per-connection
============================================================
نسخه ۱.۱ · فاز ۱۲.۲

═══ تغییرات نسخه ۱.۱ ═══
  • بازگرداندن handle_message که در نسخه‌ی قبلی اشتباهاً حذف شده بود
  • _signal_loop از fingerprint version-aware استفاده می‌کنه
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# ثابت‌های زمان‌بندی
# ═══════════════════════════════════════════════════════════
QUOTE_INTERVAL = 1.0
ORDERBOOK_INTERVAL = 3.0
SIGNAL_INTERVAL = 30.0
HEARTBEAT_TIMEOUT = 60.0


# ═══════════════════════════════════════════════════════════
# Subscription
# ═══════════════════════════════════════════════════════════
@dataclass
class Subscription:
    """اشتراک فعلی یک اتصال"""

    ticker: str = ""
    source: str = "nobitex"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    timeframe: str = "۵ دقیقه"
    ticker_name: str = ""

    last_signal_fingerprint: str = ""
    consecutive_errors: int = 0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "source": self.source,
            "market_type": self.market_type,
            "risk_profile": self.risk_profile,
            "timeframe": self.timeframe,
            "ticker_name": self.ticker_name,
        }


# ═══════════════════════════════════════════════════════════
# Connection
# ═══════════════════════════════════════════════════════════
@dataclass
class Connection:
    """یک اتصال WebSocket زنده"""

    ws: WebSocket
    id: str
    sub: Subscription = field(default_factory=Subscription)

    quote_task: Optional[asyncio.Task] = None
    orderbook_task: Optional[asyncio.Task] = None
    signal_task: Optional[asyncio.Task] = None

    closed: bool = False
    last_pong: float = 0.0

    async def send_json(self, payload: dict) -> bool:
        """ارسال امن"""
        if self.closed:
            return False
        try:
            if self.ws.client_state != WebSocketState.CONNECTED:
                return False
            await self.ws.send_text(json.dumps(payload, ensure_ascii=False))
            return True
        except Exception as e:
            logger.debug(f"[WS] send error ({self.id}): {e!r}")
            self.closed = True
            return False

    async def cancel_tasks(self):
        """لغو همه‌ی taskها"""
        self.closed = True
        for task in (self.quote_task, self.orderbook_task, self.signal_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass


# ═══════════════════════════════════════════════════════════
# WSManager
# ═══════════════════════════════════════════════════════════
class WSManager:
    """مدیریت اتصالات WebSocket"""

    def __init__(self):
        self.connections: dict[str, Connection] = {}
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        return f"ws-{self._counter}"

    async def connect(self, ws: WebSocket) -> Connection:
        """پذیرش اتصال جدید"""
        await ws.accept(subprotocol=None)
        conn = Connection(ws=ws, id=self._new_id())
        self.connections[conn.id] = conn
        logger.info(f"[WS] اتصال جدید {conn.id} — مجموع: {len(self.connections)}")
        return conn

    async def disconnect(self, conn: Connection):
        """بستن اتصال"""
        conn.closed = True
        await conn.cancel_tasks()
        self.connections.pop(conn.id, None)
        logger.info(f"[WS] قطع {conn.id} — باقی‌مانده: {len(self.connections)}")

    # ═══════════════════════════════════════════════════════
    # Producer ها
    # ═══════════════════════════════════════════════════════

    async def start_producers(self, conn: Connection):
        """راه‌اندازی producerها"""
        await self.stop_producers(conn)
        conn.quote_task = asyncio.create_task(self._quote_loop(conn))
        conn.orderbook_task = asyncio.create_task(self._orderbook_loop(conn))
        conn.signal_task = asyncio.create_task(self._signal_loop(conn))

    async def stop_producers(self, conn: Connection):
        """توقف producerها"""
        for attr in ("quote_task", "orderbook_task", "signal_task"):
            task = getattr(conn, attr)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
                setattr(conn, attr, None)

    async def _quote_loop(self, conn: Connection):
        """قیمت لحظه‌ای — هر ۱ ثانیه"""
        from fastapi.concurrency import run_in_threadpool

        while not conn.closed:
            try:
                await asyncio.sleep(QUOTE_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue

                from services.analyzer_service import quote

                q = await run_in_threadpool(quote, conn.sub.ticker, conn.sub.source)
                if q:
                    await conn.send_json({"type": "quote", "data": q})
                    conn.sub.consecutive_errors = 0
            except asyncio.CancelledError:
                return
            except Exception as e:
                conn.sub.consecutive_errors += 1
                logger.debug(f"[WS] quote loop ({conn.id}): {e!r}")
                if conn.sub.consecutive_errors >= 3:
                    await asyncio.sleep(5.0)
                    conn.sub.consecutive_errors = 0

    async def _orderbook_loop(self, conn: Connection):
        """عمق بازار — هر ۳ ثانیه"""
        from fastapi.concurrency import run_in_threadpool

        OB_SOURCES = frozenset({"nobitex", "bitpin", "wallex", "tabdeal"})

        while not conn.closed:
            try:
                await asyncio.sleep(ORDERBOOK_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue
                if conn.sub.source not in OB_SOURCES:
                    continue

                from core.orderbook import get_orderbook, execution_cost_pct
                from core.contracts import get_fee_rate

                ob = await run_in_threadpool(
                    get_orderbook, conn.sub.ticker, conn.sub.source, 20
                )
                if ob:
                    wall = ob.get("wall") or {}
                    cost = execution_cost_pct(
                        ob["spread_pct"],
                        get_fee_rate(conn.sub.source),
                    )
                    await conn.send_json(
                        {
                            "type": "orderbook",
                            "data": {
                                "ok": True,
                                "ticker": conn.sub.ticker,
                                "source": conn.sub.source,
                                "imbalance": ob["imbalance"],
                                "spread_pct": ob["spread_pct"],
                                "pressure_fa": ob["pressure_fa"],
                                "has_bid_wall": wall.get("side") == "bid",
                                "has_ask_wall": wall.get("side") == "ask",
                                "wall": wall or None,
                                "execution_cost": cost,
                            },
                        }
                    )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug(f"[WS] orderbook loop ({conn.id}): {e!r}")

    async def _signal_loop(self, conn: Connection):
        """
        سیگنال — هر ۳۰ ثانیه.
        فقط اگه fingerprint (با version) تغییر کرده باشه، push می‌شه.
        """
        from fastapi.concurrency import run_in_threadpool

        while not conn.closed:
            try:
                await asyncio.sleep(SIGNAL_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue

                from services.analyzer_service import analyze

                data = await run_in_threadpool(
                    analyze,
                    conn.sub.ticker,
                    conn.sub.source,
                    conn.sub.timeframe,
                    conn.sub.market_type,
                    conn.sub.risk_profile,
                    conn.sub.ticker_name,
                )
                if not data:
                    continue

                fp = data.get("fingerprint", "")
                if fp and fp == conn.sub.last_signal_fingerprint:
                    continue

                conn.sub.last_signal_fingerprint = fp
                await conn.send_json({"type": "signal", "data": data})
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug(f"[WS] signal loop ({conn.id}): {e!r}")

    # ═══════════════════════════════════════════════════════
    # 🔴 این متد در نسخه‌ی قبلی جا افتاده بود — بازگردانده شد
    # ═══════════════════════════════════════════════════════
    async def handle_message(self, conn: Connection, raw: str):
        """پردازش پیام ورودی از کلاینت"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await conn.send_json({"type": "error", "message": "پیام نامعتبر (JSON)"})
            return

        mtype = msg.get("type")

        if mtype == "ping":
            conn.last_pong = asyncio.get_event_loop().time()
            await conn.send_json({"type": "pong"})
            return

        if mtype == "subscribe":
            conn.sub = Subscription(
                ticker=msg.get("ticker", ""),
                source=msg.get("source", "nobitex"),
                market_type=msg.get("market_type", "futures"),
                risk_profile=msg.get("risk_profile", "aggressive"),
                timeframe=msg.get("timeframe", "۵ دقیقه"),
                ticker_name=msg.get("ticker_name", ""),
            )
            logger.info(
                f"[WS] {conn.id} subscribe → {conn.sub.ticker} @ {conn.sub.source}"
            )
            await self.start_producers(conn)
            await conn.send_json({"type": "subscribed", "data": conn.sub.to_dict()})
            return

        if mtype == "unsubscribe":
            await self.stop_producers(conn)
            conn.sub = Subscription()
            await conn.send_json({"type": "unsubscribed"})
            return

        await conn.send_json(
            {"type": "error", "message": f"نوع پیام ناشناخته: {mtype}"}
        )


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════
ws_manager = WSManager()


__all__ = ["ws_manager", "WSManager", "Connection", "Subscription"]
