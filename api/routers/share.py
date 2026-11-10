"""
api/routers/share.py
تولید کپشن اشتراک‌گذاری برای عکس سیگنال (فاز ۱۵)
============================================================
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool

from services.notifier import _build_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/share", tags=["Share"])


class ShareRequest(BaseModel):
    ticker: str
    name: str = ""
    source: str = "nobitex"
    tf: str = "۵ دقیقه"
    signal: str = "LONG"
    direction: str = "long"
    confidence: int = 0
    strategy: str = "swing"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    price: float = 0
    sl: float | None = None
    tp: float | None = None
    rr: float | None = None
    rr_net: float | None = None
    tp_levels: dict | None = None
    traps: dict | None = None


@router.post("/caption")
async def generate_caption(req: ShareRequest):
    """
    تولید کپشن متنی برای اشتراک‌گذاری (بدون ارسال به تلگرام/بله).
    از همون منطق notifier استفاده می‌کنه تا لحن یکدست باشه.
    """
    signal_dict = req.model_dump()
    # تبدیل به فرمت مورد انتظار notifier
    signal_dict["tp_levels_json"] = (
        None  # اگه tp_levels به صورت دیکشنری پاس شده، نیازی به JSON نیست
    )

    try:
        # is_telegram=False یعنی فرمت ساده (بدون HTML) برای کپی‌کردن
        caption = await run_in_threadpool(
            _build_message, signal_dict, is_telegram=False
        )
        return {"ok": True, "caption": caption}
    except Exception as e:
        logger.error(f"[Share] خطا در تولید کپشن: {e!r}")
        return {"ok": False, "caption": ""}
