"""
services/ws_manager.py
مدیریت اتصالات WebSocket + broadcast per-connection
============================================================
نسخه ۲.۱ · فاز ۱۶.۵

🔴 تغییرات نسخه ۲.۱:
  • لاگ INFO برای هر fetch و push (برای دیباگ)
  • try/except بهتر برای خطاها
  • حذف `_updated_at` از داده ارسالی به کلاینت
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# ثابت‌های زمان‌بندی
# ═══════════════════════════════════════════════════════════
SHARED_QUOTE_INTERVAL = 1.0  # هر ۱ ثانیه — قیمت (مشترک)
SHARED_ORDERBOOK_INTERVAL = 3.0  # هر ۳ ثانیه — عمق بازار (مشترک)
SIGNAL_INTERVAL = 30.0  # هر ۳۰ ثانیه — سیگنال (per-connection)
CLIENT_PUSH_INTERVAL = 0.5  # هر ۰.۵ ثانیه — ارسال به کلاینت
HEARTBEAT_TIMEOUT = 60.0

# ═══════════════════════════════════════════════════════════
# 🔴 کش مشترک (global) — بین همه‌ی اتصالات
# ═══════════════════════════════════════════════════════════
_shared_quotes: dict[str, dict] = {}
_shared_orderbooks: dict[str, dict] = {}
_shared_quote_loop_task: Optional[asyncio.Task] = None
_shared_orderbook_loop_task: Optional[asyncio.Task] = None


# ═══════════════════════════════════════════════════════════
# Subscription
# ═══════════════════════════════════════════════════════════
@dataclass
class Subscription:
    ticker: str = ""
    source: str = "nobitex"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    timeframe: str = "۵ دقیقه"
    ticker_name: str = ""
    strategy: str = "swing"  # 🔴 فاز ۱۶.۵ — هم‌خوان با TFTable

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
            "strategy": self.strategy,  # 🔴
        }

    @property
    def key(self) -> str:
        return f"{self.ticker}:{self.source}"


# ═══════════════════════════════════════════════════════════
# Connection
# ═══════════════════════════════════════════════════════════
@dataclass
class Connection:
    ws: WebSocket
    id: str
    sub: Subscription = field(default_factory=Subscription)

    quote_task: Optional[asyncio.Task] = None
    orderbook_task: Optional[asyncio.Task] = None
    signal_task: Optional[asyncio.Task] = None

    closed: bool = False
    last_pong: float = 0.0

    async def send_json(self, payload: dict) -> bool:
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
    def __init__(self):
        self.connections: dict[str, Connection] = {}
        self._counter = 0
        self._loop_started = False

    def _new_id(self) -> str:
        self._counter += 1
        return f"ws-{self._counter}"

    async def connect(self, ws: WebSocket) -> Connection:
        global _shared_quote_loop_task, _shared_orderbook_loop_task

        await ws.accept(subprotocol=None)
        conn = Connection(ws=ws, id=self._new_id())
        self.connections[conn.id] = conn
        logger.info(f"[WS] اتصال جدید {conn.id} — مجموع: {len(self.connections)}")

        if not self._loop_started:
            _shared_quote_loop_task = asyncio.create_task(self._shared_quote_loop())
            _shared_orderbook_loop_task = asyncio.create_task(
                self._shared_orderbook_loop()
            )
            self._loop_started = True
            logger.info("[WS/shared] shared loops started (quote + orderbook)")

        return conn

    async def disconnect(self, conn: Connection):
        conn.closed = True
        await conn.cancel_tasks()
        self.connections.pop(conn.id, None)
        logger.info(f"[WS] قطع {conn.id} — باقی‌مانده: {len(self.connections)}")

    # ═══════════════════════════════════════════════════════
    # Producer های مشترک (Global)
    # ═══════════════════════════════════════════════════════
    async def _shared_quote_loop(self):
        from fastapi.concurrency import run_in_threadpool
        from services.analyzer_service import quote

        logger.info("[WS/shared] quote loop started")
        while True:
            try:
                await asyncio.sleep(SHARED_QUOTE_INTERVAL)

                # جمع‌آوری جفت‌های فعال
                active_keys: set[str] = set()
                key_info: dict[str, tuple[str, str]] = {}
                for conn in list(self.connections.values()):
                    if conn.closed or not conn.sub.ticker:
                        continue
                    key = conn.sub.key
                    active_keys.add(key)
                    key_info[key] = (conn.sub.ticker, conn.sub.source)

                # fetch
                for key in active_keys:
                    ticker, source = key_info[key]
                    try:
                        q = await run_in_threadpool(quote, ticker, source)
                        if q:
                            _shared_quotes[key] = {**q, "_updated_at": time.time()}
                            logger.debug(f"[WS/shared] quote {key} = {q.get('price')}")
                        else:
                            logger.debug(f"[WS/shared] quote {key} → None")
                    except Exception as e:
                        logger.warning(f"[WS/shared] quote {key} error: {e!r}")

                # پاک‌سازی
                now = time.time()
                stale = [
                    k
                    for k, v in _shared_quotes.items()
                    if now - v.get("_updated_at", 0) > 60 and k not in active_keys
                ]
                for k in stale:
                    _shared_quotes.pop(k, None)

            except asyncio.CancelledError:
                logger.info("[WS/shared] quote loop cancelled")
                return
            except Exception as e:
                logger.warning(f"[WS/shared] quote loop error: {e!r}")
                await asyncio.sleep(5)

    async def _shared_orderbook_loop(self):
        from fastapi.concurrency import run_in_threadpool
        from core.orderbook import get_orderbook, execution_cost_pct
        from core.contracts import get_fee_rate

        OB_SOURCES = frozenset({"nobitex", "bitpin", "wallex", "tabdeal"})

        logger.info("[WS/shared] orderbook loop started")
        while True:
            try:
                await asyncio.sleep(SHARED_ORDERBOOK_INTERVAL)

                active_keys: set[str] = set()
                key_info: dict[str, tuple[str, str]] = {}
                for conn in list(self.connections.values()):
                    if conn.closed or not conn.sub.ticker:
                        continue
                    if conn.sub.source not in OB_SOURCES:
                        continue
                    key = conn.sub.key
                    active_keys.add(key)
                    key_info[key] = (conn.sub.ticker, conn.sub.source)

                for key in active_keys:
                    ticker, source = key_info[key]
                    try:
                        ob = await run_in_threadpool(get_orderbook, ticker, source, 20)
                        if ob:
                            wall = ob.get("wall") or {}
                            cost = execution_cost_pct(
                                ob["spread_pct"],
                                get_fee_rate(source),
                            )
                            _shared_orderbooks[key] = {
                                "ok": True,
                                "ticker": ticker,
                                "source": source,
                                "imbalance": ob["imbalance"],
                                "spread_pct": ob["spread_pct"],
                                "pressure_fa": ob["pressure_fa"],
                                "has_bid_wall": wall.get("side") == "bid",
                                "has_ask_wall": wall.get("side") == "ask",
                                "wall": wall or None,
                                "execution_cost": cost,
                                "_updated_at": time.time(),
                            }
                    except Exception as e:
                        logger.debug(f"[WS/shared] orderbook {key}: {e!r}")

                now = time.time()
                stale = [
                    k
                    for k, v in _shared_orderbooks.items()
                    if now - v.get("_updated_at", 0) > 60 and k not in active_keys
                ]
                for k in stale:
                    _shared_orderbooks.pop(k, None)

            except asyncio.CancelledError:
                logger.info("[WS/shared] orderbook loop cancelled")
                return
            except Exception as e:
                logger.warning(f"[WS/shared] orderbook loop error: {e!r}")
                await asyncio.sleep(5)

    # ═══════════════════════════════════════════════════════
    # Producer های per-connection
    # ═══════════════════════════════════════════════════════
    async def start_producers(self, conn: Connection):
        await self.stop_producers(conn)
        conn.quote_task = asyncio.create_task(self._quote_pusher(conn))
        conn.orderbook_task = asyncio.create_task(self._orderbook_pusher(conn))
        conn.signal_task = asyncio.create_task(self._signal_loop(conn))

    async def stop_producers(self, conn: Connection):
        for attr in ("quote_task", "orderbook_task", "signal_task"):
            task = getattr(conn, attr)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
                setattr(conn, attr, None)

    async def _quote_pusher(self, conn: Connection):
        while not conn.closed:
            try:
                await asyncio.sleep(CLIENT_PUSH_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue
                q = _shared_quotes.get(conn.sub.key)
                if q:
                    data = {k: v for k, v in q.items() if not k.startswith("_")}
                    await conn.send_json({"type": "quote", "data": data})
                logger.debug(
                    f"[WS] quote push → {conn.id} {conn.sub.key} = {data.get('price')}"
                )

            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug(f"[WS] quote push ({conn.id}): {e!r}")

    async def _orderbook_pusher(self, conn: Connection):
        while not conn.closed:
            try:
                await asyncio.sleep(CLIENT_PUSH_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue
                ob = _shared_orderbooks.get(conn.sub.key)
                if ob:
                    data = {k: v for k, v in ob.items() if not k.startswith("_")}
                    await conn.send_json({"type": "orderbook", "data": data})
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug(f"[WS] orderbook push ({conn.id}): {e!r}")

    async def _signal_loop(self, conn: Connection):
        from fastapi.concurrency import run_in_threadpool

        while not conn.closed:
            try:
                await asyncio.sleep(SIGNAL_INTERVAL)
                if conn.closed or not conn.sub.ticker:
                    continue

                from services.analyzer_service import analyze

                # 🔴 فاز ۱۶.۵ — پاس دادن strategy به analyze
                # دلیل: بدون این، بک‌اند همیشه با "swing" پیش‌فرض تحلیل می‌کنه
                # ولی TFTable با strategy جاری → دو cache key متفاوت → تناقض
                data = await run_in_threadpool(
                    analyze,
                    conn.sub.ticker,
                    conn.sub.source,
                    conn.sub.timeframe,
                    conn.sub.market_type,
                    conn.sub.risk_profile,
                    conn.sub.ticker_name,
                    True,  # include_extras
                    True,  # use_cache
                    False,  # skip_record
                    conn.sub.strategy,  # 🔴 این خط جدید
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
    # پردازش پیام ورودی
    # ═══════════════════════════════════════════════════════
    async def handle_message(self, conn: Connection, raw: str):
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
                strategy=msg.get("strategy", "swing"),  # 🔴 فاز ۱۶.۵
            )
            logger.info(
                f"[WS] {conn.id} subscribe → {conn.sub.ticker} @ {conn.sub.source} "
                f"({conn.sub.strategy})"
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


__all__ = [
    "ws_manager",
    "WSManager",
    "Connection",
    "Subscription",
    "_shared_quotes",
    "_shared_orderbooks",
]
