"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس — با جلوگیری از تکرار
============================================================
نسخه ۳.۰ · فاز ۷
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine, is_sqlite
from api.models import SignalLog
from core.contracts import Signal as SigEnum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# نگاشت TF به دقیقه — برای dedup هوشمند
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
    """زمان فعلی UTC با timezone"""
    return datetime.now(timezone.utc)


def _make_bucket(tf_name: str, now: datetime) -> str:
    """
    bucket بر اساس TF — هر کندل یه فرصت جدید.

    🔴 نسخه ۳.۰:
        قبلاً bucket = ``(now - 24h).strftime("%Y%m%d")`` بود.
        یعنی همه‌ی سیگنال‌های هم‌نام در ۲۴ ساعت گذشته dedup
        می‌شدند. نتیجه: سیگنال ۱ دقیقه‌ای که دو بار LONG می‌شد،
        دومی ثبت نمی‌شد.

        حالا: bucket = شماره‌ی کندل TF فعلی
          • ۱ دقیقه  → هر ۱ دقیقه یه فرصت
          • ۵ دقیقه  → هر ۵ دقیقه
          • ۱۵ دقیقه → هر ۱۵ دقیقه
          • روزانه   → هر روز
    """
    tf_min = _TF_MINUTES.get(tf_name, 5)
    epoch_min = int(now.timestamp() // 60)
    bucket_min = (epoch_min // tf_min) * tf_min
    return str(bucket_min)


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

    قالب: ``ticker|tf|signal|source|market_type|risk_profile|bucket``
    """
    return "|".join(
        [ticker, tf_name, signal, source, market_type, risk_profile, bucket]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
    """درج با نادیده‌گرفتن تعارض روی ``dedup_key``."""
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
    """ثبت سیگنال در دیتابیس."""
    # ═══ اعتبارسنجی ═══
    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    now = _utcnow()

    # 🔴 نسخه ۳.۰: bucket بر اساس TF
    bucket = _make_bucket(tf_name, now)
    dedup = _dedup_key(
        ticker, tf_name, signal, source, market_type, risk_profile, bucket
    )

    # ═══ SL/TP ═══
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_tp_type: Optional[str] = None
    if sl_tp:
        sl = sl_tp.get("sl")
        tp = sl_tp.get("tp")
        sl_tp_type = sl_tp.get("type")

    # ═══ تله ═══
    active_trap: Optional[str] = None
    if traps:
        for key, val in traps.items():
            if isinstance(val, dict) and val.get("active"):
                active_trap = key
                break

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
    }

    try:
        with Session(engine) as session:
            # ═══ ۱. چک سریع تکراری ═══
            # 🔴 در نسخه ۳.۰، به جای ۲۴ ساعت، از dedup_key استفاده می‌کنیم
            # که بر اساس TF محاسبه شده
            stmt = select(SignalLog.id).where(SignalLog.dedup_key == dedup).limit(1)
            if session.exec(stmt).first():
                logger.debug(
                    f"[Recorder] تکراری: {ticker} {tf_name} {signal} "
                    f"(bucket={bucket})"
                )
                return False

            # ═══ ۲. درج اتمیک ═══
            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            logger.info(
                f"[Recorder] ✅ ثبت: {ticker} {tf_name} {signal} "
                f"({source}, {confidence}%)"
            )
            return True

        logger.debug(f"[Recorder] تعارض dedup_key — رد شد: {ticker} {tf_name}")
        return False

    except IntegrityError:
        logger.debug(f"[Recorder] IntegrityError — تکراری: {ticker} {tf_name}")
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا در ثبت {ticker} {tf_name} {signal}")
        return False
