"""
api/routers/backtest.py
راستی‌آزمایی — endpoints
============================================================
نسخه ۳.۲ · فاز ۱۰.۱۰
🔴 تغییرات:
  • + خروجی exit_reason و trend_predicted_at_entry در تاریخچه
  • اصلاح منطق ریست (حذف با X-API-Key)
"""

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
    compute_stats_by_tf,
    compute_stats_by_profile,
    compute_stats_by_quality,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["Backtest"])


# ═══════════════════════════════════════════════════════════
# GET /backtest — آمار کلی
# ═══════════════════════════════════════════════════════════
@router.get("", response_model=BacktestResponse)
async def backtest_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = Query(default=100, ge=50, le=500),
):
    """آمار کلی راستی‌آزمایی"""
    stats = await run_in_threadpool(
        compute_stats,
        tf=tf,
        source=source,
        time_filter=time_filter,
        risk_profile=risk_profile,
        limit=limit,
    )

    # پر کردن فیلدهای نبوده با مقادیر پیش‌فرض
    stats.setdefault("avg_rr_net", 0.0)
    stats.setdefault("trend_correct", 0)
    stats.setdefault("trend_wrong", 0)
    stats.setdefault("trend_accuracy", 0.0)

    return BacktestResponse(stats=BacktestStats(**stats), items=[])


# ═══════════════════════════════════════════════════════════
# GET /backtest/history — تاریخچه
# ═══════════════════════════════════════════════════════════
@router.get("/history")
async def backtest_history(
    limit: int = 50,
    status: str = "all",
    tf: str = "",
    source: str = "",
    risk_profile: str = "",
    session: Session = Depends(get_session),
):
    """تاریخچه‌ی سیگنال‌ها"""
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
                "trend_correct": r.trend_correct,
                "is_weak": r.is_weak,
                # 🔴 فیلدهای جدید فاز ۱۰.۱۰
                "exit_reason": r.exit_reason,
                "trend_predicted_at_entry": r.trend_predicted_at_entry,
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════
# POST /backtest/run — اجرای دستی
# ═══════════════════════════════════════════════════════════
@router.post("/run")
async def backtest_run():
    """اجرای دستی راستی‌آزمایی."""
    logger.info("[Backtest/manual] اجرای دستی راستی‌آزمایی توسط کاربر")

    try:
        result = await run_in_threadpool(backtest_all, 200)
        logger.info(
            f"[Backtest/manual] ✅ انجام شد — "
            f"checked={result.get('checked', 0)}, "
            f"updated={result.get('updated', 0)}, "
            f"errors={result.get('errors', 0)}"
        )
        return {"ok": True, **result}
    except Exception as e:
        logger.exception("[Backtest/manual] خطا")
        return {
            "ok": False,
            "error": str(e),
            "checked": 0,
            "updated": 0,
            "expired": 0,
            "win": 0,
            "loss": 0,
            "errors": 1,
        }


# ═══════════════════════════════════════════════════════════
# DELETE /backtest/reset — پاک‌سازی (نیاز به admin key)
# ═══════════════════════════════════════════════════════════
@router.delete("/reset")
async def backtest_reset(
    request: Request,
    session: Session = Depends(get_session),
):
    """پاک کردن همه‌ی سیگنال‌ها — نیاز به X-API-Key."""
    audit_log = logging.getLogger("api.deps")

    admin_key = (settings.ADMIN_API_KEY or "").strip()
    if not admin_key:
        audit_log.error("[Admin] ADMIN_API_KEY تنظیم نشده — درخواست رد شد")
        raise HTTPException(
            status_code=503,
            detail="سرویس موقتاً در دسترس نیست (کلید ادمین تنظیم نشده)",
        )

    provided = request.headers.get("X-API-Key", "").strip()
    if not provided:
        audit_log.warning("[Admin] درخواست reset بدون X-API-Key")
        raise HTTPException(status_code=401, detail="X-API-Key لازم است")

    if provided != admin_key:
        audit_log.warning(f"[Admin] کلید اشتباه در reset: {provided[:4]}...")
        raise HTTPException(status_code=403, detail="کلید معتبر نیست")

    audit_log.info(
        f"[Admin] درخواست reset تأیید شد (ip={request.client.host if request.client else '?'})"
    )

    rows = session.exec(select(SignalLog)).all()
    count = len(rows)
    for r in rows:
        session.delete(r)
    session.commit()

    audit_log.info(f"[Admin] {count} سیگنال حذف شد")
    return {"ok": True, "deleted": count}


# ═══════════════════════════════════════════════════════════
# GET /backtest/by-tf — به تفکیک TF
# ═══════════════════════════════════════════════════════════
@router.get("/by-tf")
async def backtest_stats_by_tf(
    time_filter: str = Query(default="all"),
    risk_profile: str = Query(default=""),
    limit: int = Query(default=100, ge=50, le=500),
):
    data = await run_in_threadpool(
        compute_stats_by_tf,
        time_filter=time_filter,
        risk_profile=risk_profile,
        limit=limit,
    )
    return {"ok": True, "items": data}


# ═══════════════════════════════════════════════════════════
# GET /backtest/by-profile — به تفکیک پروفایل
# ═══════════════════════════════════════════════════════════
@router.get("/by-profile")
async def backtest_stats_by_profile(
    time_filter: str = Query(default="all"),
):
    data = await run_in_threadpool(
        compute_stats_by_profile,
        time_filter=time_filter,
    )
    return {"ok": True, "items": data}


# ═══════════════════════════════════════════════════════════
# GET /backtest/by-quality — به تفکیک کیفیت
# ═══════════════════════════════════════════════════════════
@router.get("/by-quality")
async def backtest_stats_by_quality(
    request: Request,
    tf: str = Query(default=""),
    source: str = Query(default=""),
    time_filter: str = Query(default="all"),
    risk_profile: str = Query(default=""),
    limit: int = Query(default=100, ge=50, le=500),
):
    """آمار به تفکیک کیفیت سیگنال (confidence tier)."""
    rate_limit_for(request, "backtest_quality", limit=30, window_sec=60)

    data = await run_in_threadpool(
        compute_stats_by_quality,
        tf=tf,
        source=source,
        time_filter=time_filter,
        risk_profile=risk_profile,
        limit=limit,
    )
    return {"ok": True, "items": data}


# ═══════════════════════════════════════════════════════════
# POST /backtest/record — ثبت سیگنال از اسکنر
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
    """ثبت یک سیگنال از اسکنر برای راستی‌آزمایی."""
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
