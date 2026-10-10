"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس
============================================================
نسخه ۵.۰ · فاز ۱۰.۴
🔴 تغییرات:
  • quote (USDT/IRT) استخراج از ticker
  • TF=۱m در whitelist نیست (فقط پیش‌بینی)
  • dedup بهبود
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine, is_sqlite
from api.models import SignalLog
from core.contracts import Signal as SigEnum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# TF whitelist — ۱ دقیقه ثبت نمی‌شه
# ═══════════════════════════════════════════════════════════
_TF_MINUTES: dict[str, int] = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30,
    "۱ ساعت": 60,
    "روزانه": 1440,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_quote(ticker: str) -> str:
    """استخراج نوع ارز از ticker"""
    upper = ticker.upper()
    if "IRT" in upper or "TMN" in upper:
        return "IRT"
    if "USDT" in upper or "USD" in upper:
        return "USDT"
    return "USDT"  # پیش‌فرض


def _make_bucket(tf_name: str, now: datetime) -> str:
    """bucket = شروع کندل فعلی"""
    tf_min = _TF_MINUTES.get(tf_name, 5)
    epoch_min = int(now.timestamp() // 60)
    bucket_min = (epoch_min // tf_min) * tf_min
    return str(bucket_min)


def _extract_quote(ticker: str) -> str:
    """استخراج نوع ارز از ticker."""
    upper = ticker.upper()
    if "IRT" in upper or "TMN" in upper:
        return "IRT"
    if "USDT" in upper or "USD" in upper:
        return "USDT"
    return "USDT"


def _signal_base(signal: str) -> str:
    """LONG/SHORT/NEUTRAL — مستقل از متن دقیق"""
    if "LONG" in signal:
        return "LONG"
    if "SHORT" in signal:
        return "SHORT"
    return "NEUTRAL"


def _dedup_key(ticker, tf_name, signal, source, market_type, risk_profile, bucket):
    return "|".join(
        [
            ticker,
            tf_name,
            _signal_base(signal),
            source,
            market_type,
            risk_profile,
            bucket,
        ]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
    if is_sqlite:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(SignalLog).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
    else:
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(SignalLog).values(**values)
            stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
        except ImportError:
            stmt = insert(SignalLog).values(**values)
    result = session.execute(stmt)
    session.commit()
    return bool(result.rowcount)


def _compute_is_weak(signal: str, confidence: int, consensus: str) -> bool:
    """is_weak منطقی"""
    if "ضعیف" in signal:
        return True
    if confidence < 50:
        return True
    if consensus == "weak":
        return True
    return False


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
    """ثبت سیگنال — نسخه ۵.۰"""

    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    is_weak = _compute_is_weak(signal, confidence, consensus)
    now = _utcnow()
    bucket = _make_bucket(tf_name, now)
    dedup = _dedup_key(
        ticker, tf_name, signal, source, market_type, risk_profile, bucket
    )

    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_tp_type: Optional[str] = None
    if sl_tp:
        sl = sl_tp.get("sl")
        tp = sl_tp.get("tp")
        sl_tp_type = sl_tp.get("type")

    active_trap: Optional[str] = None
    if traps:
        for key, val in traps.items():
            if isinstance(val, dict) and val.get("active"):
                active_trap = key
                break

    # 🔴 استخراج quote
    quote = _extract_quote(ticker)

    values = {
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
        "is_weak": is_weak,
    }

    try:
        with Session(engine) as session:
            stmt = select(SignalLog.id).where(SignalLog.dedup_key == dedup).limit(1)
            if session.exec(stmt).first():
                return False
            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            weak_flag = " [ضعیف]" if is_weak else ""
            logger.info(
                f"[Recorder] ✅ {ticker} {tf_name} {signal}{weak_flag} "
                f"({source}, {confidence}%, {quote})"
            )
            return True
        return False
    except IntegrityError:
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا {ticker} {tf_name} {signal}")
        return False
