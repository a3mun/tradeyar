"""
api/routers/backtest.py
راستی‌آزمایی — endpoints
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from api.database import get_session
from api.models import SignalLog
from api.schemas import BacktestResponse, BacktestStats
from services.backtest_service import backtest_all, compute_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["Backtest"])


# ═══════════════════════════════════════════════════════════
# GET /backtest — آمار
# ═══════════════════════════════════════════════════════════
@router.get("", response_model=BacktestResponse)
async def backtest_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
):
    stats = compute_stats(tf=tf, source=source, time_filter=time_filter)
    return BacktestResponse(
        stats=BacktestStats(**stats),
        items=[],
    )


# ═══════════════════════════════════════════════════════════
# GET /backtest/history — لیست سیگنال‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/history")
async def backtest_history(
    limit: int = 50,
    status: str = "all",  # all/pending/win/loss/expired
    tf: str = "",
    source: str = "",
    session: Session = Depends(get_session),
):
    stmt = select(SignalLog)
    if status == "pending":
        stmt = stmt.where(SignalLog.result.is_(None)).where(
            SignalLog.expired == False
        )  # noqa
    elif status == "win":
        stmt = stmt.where(SignalLog.result == "win")
    elif status == "loss":
        stmt = stmt.where(SignalLog.result == "loss")
    elif status == "expired":
        stmt = stmt.where(SignalLog.expired == True)  # noqa

    if tf:
        stmt = stmt.where(SignalLog.tf == tf)
    if source:
        stmt = stmt.where(SignalLog.source == source)

    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    rows = session.exec(stmt).all()

    return {
        "ok": True,
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "ticker": r.ticker,
                "name": r.name,
                "source": r.source,
                "signal": r.signal,
                "direction": r.direction,
                "confidence": r.confidence,
                "price": r.price,
                "sl": r.sl,
                "tp": r.tp,
                "rr": r.rr,
                "tf": r.tf,
                "market_type": r.market_type,
                "result": r.result,
                "result_time": r.result_time.isoformat() if r.result_time else None,
                "exit_price": r.exit_price,
                "expired": r.expired,
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════
# POST /backtest/run — بررسی دستی
# ═══════════════════════════════════════════════════════════
@router.post("/run")
async def backtest_run():
    """اجرای دستی راستی‌آزمایی"""
    result = backtest_all()
    return {"ok": True, **result}


# ═══════════════════════════════════════════════════════════
# DELETE /backtest/reset — ریست
# ═══════════════════════════════════════════════════════════
@router.delete("/reset")
async def backtest_reset(session: Session = Depends(get_session)):
    """حذف همه سیگنال‌ها"""
    rows = session.exec(select(SignalLog)).all()
    count = len(rows)
    for r in rows:
        session.delete(r)
    session.commit()
    return {"ok": True, "deleted": count}
