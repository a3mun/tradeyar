"""api/routers/backtest.py — راستی‌آزمایی endpoints (نسخه ۴.۱)"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlmodel import Session, select

from api.database import get_session
from api.deps import rate_limit_for
from api.models import SignalLog
from api.schemas import BacktestResponse, BacktestStats
from api.config import settings
from services.backtest_service import (
    backtest_all,
    compute_stats,
    compute_stats_by_strategy,
    get_site_stats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("", response_model=BacktestResponse)
async def backtest_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    strategy: str = "",
    limit: int = Query(default=100, ge=50, le=500),
):
    stats = await run_in_threadpool(
        compute_stats,
        tf=tf,
        source=source,
        time_filter=time_filter,
        risk_profile=risk_profile,
        limit=limit,
        strategy=strategy,
    )
    stats.setdefault("avg_rr_net", 0.0)
    stats.setdefault("trend_correct", 0)
    stats.setdefault("trend_wrong", 0)
    stats.setdefault("trend_accuracy", 0.0)
    stats.setdefault("tp_hit_rate", 0.0)
    stats.setdefault("avg_tp_level", 0.0)
    stats.setdefault("profit_factor", 0.0)
    stats.setdefault("avg_rr", 0.0)
    stats.setdefault("expectancy", 0.0)
    return BacktestResponse(stats=BacktestStats(**stats), items=[])


@router.get("/history")
async def backtest_history(
    limit: int = Query(default=100, ge=10, le=100),
    status: str = "all",
    tf: str = "",
    source: str = "",
    risk_profile: str = "",
    strategy: str = "",
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
    if strategy:
        stmt = stmt.where(SignalLog.strategy == strategy)
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
                "tf": r.tf,
                "market_type": r.market_type,
                "risk_profile": r.risk_profile,
                "strategy": r.strategy or "swing",
                "result": r.result,
                "result_time": r.result_time.isoformat() if r.result_time else None,
                "exit_price": r.exit_price,
                "expired": r.expired,
                "expired_at_price": r.expired_at_price,
                "expired_pnl_pct": r.expired_pnl_pct,
                "expired_bias": r.expired_bias,
                "tp_hit_level": r.tp_hit_level,
                "exit_reason": r.exit_reason,
            }
            for r in rows
        ],
    }


@router.post("/run")
async def backtest_run():
    try:
        result = await run_in_threadpool(backtest_all, 300)
        return {"ok": True, **result}
    except Exception as e:
        logger.exception("[Backtest/manual] خطا")
        return {"ok": False, "error": str(e), "checked": 0, "updated": 0, "errors": 1}


@router.delete("/reset")
async def backtest_reset(request: Request, session: Session = Depends(get_session)):
    admin_key = (settings.ADMIN_API_KEY or "").strip()
    if not admin_key:
        raise HTTPException(status_code=503, detail="کلید ادمین تنظیم نشده")
    provided = request.headers.get("X-API-Key", "").strip()
    if not provided:
        raise HTTPException(status_code=401, detail="X-API-Key لازم است")
    if provided != admin_key:
        raise HTTPException(status_code=403, detail="کلید معتبر نیست")
    rows = session.exec(select(SignalLog)).all()
    count = len(rows)
    for r in rows:
        session.delete(r)
    session.commit()
    return {"ok": True, "deleted": count}


@router.get("/by-strategy")
async def backtest_stats_by_strategy(
    time_filter: str = Query(default="all"),
    risk_profile: str = Query(default=""),
    tf: str = Query(default=""),
    source: str = Query(default=""),
    limit: int = Query(default=100, ge=50, le=500),
):
    data = await run_in_threadpool(
        compute_stats_by_strategy,
        tf=tf,
        source=source,
        time_filter=time_filter,
        risk_profile=risk_profile,
        limit=limit,
    )
    return {"ok": True, "items": data}


@router.get("/site-stats")
async def backtest_site_stats():
    """آمار نمایشی سایت — با override ادمین."""
    data = await run_in_threadpool(get_site_stats)
    return {"ok": True, **data}


class RecordRequest(BaseModel):
    ticker: str
    source: str = "nobitex"
    timeframe: str = "۵ دقیقه"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    ticker_name: str = ""


@router.post("/record")
async def backtest_record(req: RecordRequest):
    from services.analyzer_service import analyze

    result = await run_in_threadpool(
        analyze,
        ticker=req.ticker,
        source=req.source,
        tf_name=req.timeframe,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        ticker_name=req.ticker_name or req.ticker,
        include_extras=False,
        skip_record=False,
    )
    if result is None:
        return {"ok": False, "error": "تحلیل ناموفق بود"}
    return {
        "ok": True,
        "ticker": req.ticker,
        "signal": result.get("signal", ""),
        "confidence": result.get("confidence", 0),
    }
