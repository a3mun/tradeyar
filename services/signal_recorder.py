"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس — با جلوگیری از تکرار
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from core.contracts import Signal as SigEnum

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
) -> bool:
    """
    ثبت سیگنال در دیتابیس.
    Returns True اگه ثبت شد.
    """
    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    try:
        with Session(engine) as session:
            # ═══ جلوگیری از تکرار در ۲۴ ساعت ═══
            cutoff = _utcnow() - timedelta(hours=24)
            stmt = (
                select(SignalLog)
                .where(SignalLog.ticker == ticker)
                .where(SignalLog.tf == tf_name)
                .where(SignalLog.signal == signal)
                .where(SignalLog.timestamp >= cutoff)
                .limit(1)
            )
            existing = session.exec(stmt).first()
            if existing:
                logger.debug(f"[Recorder] {ticker} {tf_name} {signal} — تکراری")
                return False

            # ═══ ثبت ═══
            sl = None
            tp = None
            sl_tp_type = None
            if sl_tp:
                sl = sl_tp.get("sl")
                tp = sl_tp.get("tp")
                sl_tp_type = sl_tp.get("type")

            # ─── استخراج trap ───
            active_trap = None
            if traps:
                for key, val in traps.items():
                    if val.get("active"):
                        active_trap = key
                        break

            log = SignalLog(
                ticker=ticker,
                name=name,
                source=source,
                signal=signal,
                direction=direction,
                confidence=confidence,
                consensus=consensus,
                regime=regime,
                price=float(price),
                sl=float(sl) if sl else None,
                tp=float(tp) if tp else None,
                sl_tp_type=sl_tp_type,
                rr=float(rr) if rr else None,
                tf=tf_name,
                market_type=market_type,
                risk_profile=risk_profile,
                had_trap=bool(active_trap),
                trap_type=active_trap,
                timestamp=_utcnow(),
            )
            session.add(log)
            session.commit()
            logger.info(f"[Recorder] ✅ ثبت: {ticker} {tf_name} {signal}")
            return True
    except Exception as e:
        logger.error(f"[Recorder] خطا: {e}")
        return False
