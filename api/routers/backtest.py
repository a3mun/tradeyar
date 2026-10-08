"""
api/routers/backtest.py
راستی‌آزمایی — endpoints
============================================================
نسخه ۲.۰: فیلتر risk_profile + by-profile endpoint
"""

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from api.database import get_session
from api.models import SignalLog
from api.schemas import BacktestResponse, BacktestStats
from services.backtest_service import (
    backtest_all,
    compute_stats,
    compute_stats_by_tf,
    compute_stats_by_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("", response_model=BacktestResponse)
async def backtest_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
):
    stats = compute_stats(
        tf=tf,
        source=source,
        time_filter=time_filter,
        risk_profile=risk_profile,
    )
    stats.setdefault("avg_rr_net", 0.0)
    stats.setdefault("trend_correct", 0)
    stats.setdefault("trend_wrong", 0)
    stats.setdefault("trend_accuracy", 0.0)
    stats.setdefault("expired_win", 0)
    stats.setdefault("expired_loss", 0)
    stats.setdefault("expired_flat", 0)
    return BacktestResponse(stats=BacktestStats(**stats), items=[])


@router.get("/history")
async def backtest_history(
    limit: int = 50,
    status: str = "all",
    tf: str = "",
    source: str = "",
    risk_profile: str = "",
    session: Session = Depends(get_session),
):
    stmt = select(SignalLog)
    if status == "pending":
        stmt = stmt.where(SignalLog.result.is_(None)).where(SignalLog.expired == False)
    elif status == "win":
        stmt = stmt.where(SignalLog.result == "win")
    elif status == "loss":
        stmt = stmt.where(SignalLog.result == "loss")
    elif status == "expired":
        stmt = stmt.where(SignalLog.expired == True)

    if tf:
        stmt = stmt.where(SignalLog.tf == tf)
    if source:
        stmt = stmt.where(SignalLog.source == source)
    if risk_profile:
        stmt = stmt.where(SignalLog.risk_profile == risk_profile)

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
                "rr_net": r.rr_net,
                "fee_pct": r.fee_pct,
                "fee_ratio": r.fee_ratio,
                "breakeven_pct": r.breakeven_pct,
                "is_worthwhile": r.is_worthwhile,
                "timeframe_viable": r.timeframe_viable,
                "rr_decay_pct": r.rr_decay_pct,
                "tf": r.tf,
                "market_type": r.market_type,
                "risk_profile": r.risk_profile,
                "result": r.result,
                "result_time": r.result_time.isoformat() if r.result_time else None,
                "exit_price": r.exit_price,
                "expired": r.expired,
                "expired_at_price": r.expired_at_price,
                "expired_pnl_pct": r.expired_pnl_pct,
                "expired_bias": r.expired_bias,
                "had_trap": r.had_trap,
                "trap_type": r.trap_type,
                "orderbook_available": r.orderbook_available,
                "trade_side_irt": r.trade_side_irt,
                "trend_correct": getattr(r, "trend_correct", None),
                # 🔴 فاز ۸.۲
                "is_weak": getattr(r, "is_weak", False),
            }
            for r in rows
        ],
    }


@router.post("/run")
async def backtest_run():
    result = backtest_all()
    return {"ok": True, **result}


@router.delete("/reset")
async def backtest_reset(session: Session = Depends(get_session)):
    rows = session.exec(select(SignalLog)).all()
    count = len(rows)
    for r in rows:
        session.delete(r)
    session.commit()
    return {"ok": True, "deleted": count}


@router.get("/by-tf")
async def backtest_stats_by_tf(
    time_filter: str = Query(default="all"),
    risk_profile: str = Query(default=""),
):
    data = compute_stats_by_tf(
        time_filter=time_filter,
        risk_profile=risk_profile,
    )
    return {"ok": True, "items": data}


@router.get("/by-profile")
async def backtest_stats_by_profile(
    time_filter: str = Query(default="all"),
):
    data = compute_stats_by_profile(time_filter=time_filter)
    return {"ok": True, "items": data}


# ═══════════════════════════════════════════════════════════
# POST /backtest/record — ثبت سیگنال از اسکنر (فاز ۸)
# ═══════════════════════════════════════════════════════════
class RecordRequest(BaseModel):
    """بدنه درخواست POST /backtest/record"""

    ticker: str
    source: str = "nobitex"
    timeframe: str = "۵ دقیقه"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    ticker_name: str = ""


@router.post("/record")
async def backtest_record(req: RecordRequest):
    """
    ثبت یک سیگنال از اسکنر برای راستی‌آزمایی.

    ⚠️ چرا این endpoint:
        Scanner.tsx برای دکمه‌ی «راستی‌آزمایی» به /backtest/record
        درخواست می‌زند. تابع analyze خودش signal_recorder را
        صدا می‌زند (dedup دارد).

    فرانت انتظار ``{ok: true}`` دارد.
    """
    from services.analyzer_service import analyze

    # ─── اجرای تحلیل + ثبت خودکار ───
    # signal_recorder خودکار داخل analyze() ثبت می‌کند
    result = analyze(
        ticker=req.ticker,
        source=req.source,
        tf_name=req.timeframe,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        ticker_name=req.ticker_name or req.ticker,
        include_extras=False,
        skip_record=False,  # ← ثبت انجام بشه
    )

    if result is None:
        return {"ok": False, "error": "تحلیل ناموفق بود"}

    return {
        "ok": True,
        "ticker": req.ticker,
        "signal": result.get("signal", ""),
        "confidence": result.get("confidence", 0),
    }
