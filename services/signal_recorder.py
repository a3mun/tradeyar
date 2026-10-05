"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس — با جلوگیری از تکرار
============================================================
اصلاح باگ ۵ (نسخه ۱.۴)
------------------------------------------------------------
۱) منبع در چک تکراری لحاظ نمی‌شد
   پیش از این، شرط فقط (ticker, tf, signal) در ۲۴ ساعت بود:

       stmt = (select(SignalLog)
               .where(SignalLog.ticker == ticker)
               .where(SignalLog.tf == tf_name)
               .where(SignalLog.signal == signal)
               .where(SignalLog.timestamp >= cutoff))

   نتیجه: سیگنال BTC-USD LONG روی «۵ دقیقه» که از **نوبیتکس** ثبت شده
   بود، ثبت همان سیگنال از **بیت‌پین** را بلوکه می‌کرد.
   یعنی آمار بک‌تست بیت‌پین/والکس همیشه خالی می‌ماند.
   همین مشکل برای market_type و risk_profile هم بود.

۲) race condition
   چک تکراری یک SELECT و بعد INSERT است. دو تحلیل هم‌زمان می‌توانند
   هر دو SELECT خالی ببینند و هر دو درج کنند.

   حالا INSERT به‌صورت ``INSERT ... ON CONFLICT DO NOTHING`` روی
   ستون یکتای ``dedup_key`` اجرا می‌شود. مزیت مهم این رویکرد:
   نخ بازنده **rollback نمی‌کند**، پس کار نخ‌های دیگر در همان
   session/transaction از بین نمی‌رود.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine, is_sqlite
from api.models import SignalLog
from core.contracts import Signal as SigEnum
import json

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """زمان فعلی UTC با timezone"""
    return datetime.now(timezone.utc)


def _dedup_key(
    ticker: str,
    tf_name: str,
    signal: str,
    source: str,
    market_type: str,
    risk_profile: str,
    bucket: str,
) -> str:
    """
    کلید یکتای «سیگنال منطقاً یکسان».

    Args:
        bucket: بازه‌ی ۲۴ ساعته (YYYYMMDD) — سیگنال روز بعد مجاز است
                ولی تکراری همان بازه بلوکه می‌شود.

    قالب: ``ticker|tf|signal|source|market_type|risk_profile|bucket``
    """
    return "|".join(
        [ticker, tf_name, signal, source, market_type, risk_profile, bucket]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
    """
    درج با نادیده‌گرفتن تعارض روی ``dedup_key``.

    Returns:
        True اگر ردیف درج شد، False اگر تعارض بود (تکراری).
    """
    if is_sqlite:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(SignalLog).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
    else:
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(SignalLog).values(**values)
            stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
        except ImportError:  # pragma: no cover
            stmt = insert(SignalLog).values(**values)

    result = session.execute(stmt)
    session.commit()
    return bool(result.rowcount)


def record_signal(
    ticker: str,
    name: str,
    signal: str,
    price: float,
    tf_name: str,
    source: str = "nobitex",
    market_type: str = "futures",
    risk_profile: str = "aggressive",
    sl_tp: dict | None = None,
    direction: str = "neutral",
    confidence: int = 0,
    consensus: str = "neutral",
    regime: str = "range",
    rr: float | None = None,
    traps: dict | None = None,
    # ═══ جدید (نسخه ۲.۰) ═══
    rr_net: float | None = None,
    fee_pct: float | None = None,
    fee_ratio: float | None = None,
    breakeven_pct: float | None = None,
    is_worthwhile: bool | None = None,
    timeframe_viable: bool | None = None,
    rr_decay_pct: float | None = None,
    execution_cost: dict | None = None,
    orderbook_available: bool = False,
    trade_side_irt: bool = False,
) -> bool:
    """
    ثبت سیگنال در دیتابیس.

    Returns:
        True اگر ثبت شد، False اگر تکراری/نامعتبر بود.
    """
    # ═══ اعتبارسنجی ═══
    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    now = _utcnow()
    bucket = (now - timedelta(hours=24)).strftime("%Y%m%d")
    dedup = _dedup_key(
        ticker, tf_name, signal, source, market_type, risk_profile, bucket
    )

    # ═══ استخراج SL/TP ═══
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_tp_type: Optional[str] = None
    if sl_tp:
        sl = sl_tp.get("sl")
        tp = sl_tp.get("tp")
        sl_tp_type = sl_tp.get("type")

    # ═══ استخراج تله فعال ═══
    active_trap: Optional[str] = None
    if traps:
        for key, val in traps.items():
            # محافظت: val ممکن است dict نباشد
            if isinstance(val, dict) and val.get("active"):
                active_trap = key
                break

    values = {
        # ─── قبلی‌ها ───
        "ticker": ticker,
        "name": name,
        "source": source,
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "consensus": consensus,
        "regime": regime,
        "price": float(price),
        "sl": float(sl) if sl else None,
        "tp": float(tp) if tp else None,
        "sl_tp_type": sl_tp_type,
        "rr": float(rr) if rr else None,
        "tf": tf_name,
        "market_type": market_type,
        "risk_profile": risk_profile,
        "had_trap": bool(active_trap),
        "trap_type": active_trap,
        "dedup_key": dedup,
        "timestamp": now,
        # ─── جدید نسخه ۲.۰ ───
        "rr_net": float(rr_net) if rr_net is not None else None,
        "fee_pct": float(fee_pct) if fee_pct is not None else None,
        "fee_ratio": float(fee_ratio) if fee_ratio is not None else None,
        "breakeven_pct": float(breakeven_pct) if breakeven_pct is not None else None,
        "is_worthwhile": is_worthwhile,
        "timeframe_viable": timeframe_viable,
        "rr_decay_pct": float(rr_decay_pct) if rr_decay_pct is not None else None,
        "execution_cost_json": json.dumps(execution_cost) if execution_cost else None,
        "orderbook_available": bool(orderbook_available),
        "trade_side_irt": bool(trade_side_irt),
    }

    try:
        with Session(engine) as session:
            # ═══ ۱. چک سریع تکراری (صرفه‌جویی در INSERT) ═══
            # 🔴 باگ ۵: source، market_type و risk_profile اضافه شدند
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(SignalLog.id)
                .where(SignalLog.ticker == ticker)
                .where(SignalLog.tf == tf_name)
                .where(SignalLog.signal == signal)
                .where(SignalLog.source == source)
                .where(SignalLog.market_type == market_type)
                .where(SignalLog.risk_profile == risk_profile)
                .where(SignalLog.timestamp >= cutoff)
                .limit(1)
            )
            if session.exec(stmt).first():
                logger.debug(
                    f"[Recorder] تکراری: {ticker} {tf_name} {signal} "
                    f"({source}/{market_type}/{risk_profile})"
                )
                return False

            # ═══ ۲. درج اتمیک ═══
            # ON CONFLICT DO NOTHING → نخ بازنده rollback نمی‌کند
            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            logger.info(
                f"[Recorder] ✅ ثبت: {ticker} {tf_name} {signal} "
                f"({source}, {confidence}%)"
            )
            return True

        logger.debug(f"[Recorder] تعارض dedup_key — رد شد: {ticker} {tf_name} {signal}")
        return False

    except IntegrityError:
        # ═══ ۳. fallback برای دیتابیس‌هایی که ON CONFLICT ندارند ═══
        logger.debug(f"[Recorder] IntegrityError — تکراری: {ticker} {tf_name} {signal}")
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا در ثبت {ticker} {tf_name} {signal}")
        return False
