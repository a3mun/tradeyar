"""
api/routers/admin_ws.py
WebSocket برای اطلاع‌رسانی به ادمین (درخواست پرداخت / تیکت جدید)
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from api.auth import decode_token, normalize_phone, is_admin_phone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin WS"])

# لیست اتصالات فعال ادمین‌ها
_active_admins: list[WebSocket] = []


@router.websocket("/ws/notifications")
async def admin_ws(websocket: WebSocket, token: str = Query(default="")):
    """اتصال ادمین به WebSocket — فقط ادمین‌های مجاز"""
    # بررسی توکن
    try:
        payload = decode_token(token)
        phone = normalize_phone(payload.get("sub", ""))
        if not is_admin_phone(phone):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _active_admins.append(websocket)
    logger.info(f"[Admin WS] ادمین وصل شد — مجموع: {len(_active_admins)}")

    try:
        while True:
            # فقط زنده نگه‌داشتن اتصال (ping/pong از سمت فرانت)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _active_admins:
            _active_admins.remove(websocket)
        logger.info(f"[Admin WS] ادمین قطع شد — باقی‌مانده: {len(_active_admins)}")


async def notify_admins(message: dict) -> None:
    """ارسال نوتیف به همه ادمین‌های متصل"""
    dead: list[WebSocket] = []
    for ws in _active_admins:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _active_admins:
            _active_admins.remove(ws)
