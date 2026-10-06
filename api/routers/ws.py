"""
api/routers/ws.py
WebSocket endpoint — /api/ws/live
============================================================
نسخه ۱.۰ · فاز ۷

═══ پروتکل ═══

Client → Server:
    {"type": "subscribe", "ticker": "BTC-USD", "source": "nobitex",
     "market_type": "futures", "risk_profile": "aggressive",
     "timeframe": "۵ دقیقه", "ticker_name": "بیت‌کوین"}
    {"type": "unsubscribe"}
    {"type": "ping"}

Server → Client:
    {"type": "quote", "data": {"price": 4152.0, "change_pct": 0.24, ...}}
    {"type": "orderbook", "data": {...}}
    {"type": "signal", "data": {...}}
    {"type": "subscribed", "data": {...}}
    {"type": "unsubscribed"}
    {"type": "pong"}
    {"type": "error", "message": "..."}

═══ نرخ ارسال ═══

    quote     → هر ۱ ثانیه
    orderbook → هر ۳ ثانیه
    signal    → هر ۳۰ ثانیه (فقط اگه fingerprint تغییر کرد)

═══ مقاومت در برابر خطا ═══

  • کلاینت قطع بشه → producerها خودکار kill می‌شن
  • صرافی جواب نده → skip اون دور
  • JSON نامعتبر → پیام error، ادامه می‌ده
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/live")
async def ws_live(ws: WebSocket):
    """
    اتصال WebSocket زنده.

    ═══ مثال کلاینت (JS) ═══

        const ws = new WebSocket("ws://localhost:8000/api/ws/live");
        ws.onopen = () => {
          ws.send(JSON.stringify({
            type: "subscribe",
            ticker: "BTC-USD",
            source: "nobitex",
            market_type: "futures",
            risk_profile: "aggressive",
            timeframe: "۵ دقیقه",
            ticker_name: "بیت‌کوین"
          }));
        };
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data);
          // msg.type: quote | orderbook | signal | ...
        };

    ═══ نکات ═══

    • به محض اتصال، هیچ داده‌ای فرستاده نمی‌شه. باید ``subscribe`` بزنی.
    • تغییر نماد → فقط یه ``subscribe`` جدید بفرست، producerها
      خودکار ری‌استارت می‌شن.
    • heartbeat: هر ۳۰ ثانیه ``ping`` بفرست.
    """
    conn = await ws_manager.connect(ws)

    try:
        while True:
            raw = await ws.receive_text()
            await ws_manager.handle_message(conn, raw)
    except WebSocketDisconnect:
        logger.debug(f"[WS] کلاینت {conn.id} خودش قطع کرد")
    except Exception as e:
        logger.warning(f"[WS] خطا در {conn.id}: {e!r}")
    finally:
        await ws_manager.disconnect(conn)
