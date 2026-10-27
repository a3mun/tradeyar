"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس
============================================================
نسخه ۶.۰ · فاز ۱۰.۱۰
🔴 تغییرات نسبت به ۵.۳:
  • + trend_predicted_at_entry در ورودی‌ها
  • + فیلتر نرم confidence < 35 (برای جلوگیری از آمار کاذب)
  • + Cooldown ۵ دقیقه‌ای در همان TF (جلوگیری از تکرار)
  • حفظ دیتای کامل برای یکپارچگی با UI و Backtest
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine, is_sqlite
from api.models import SignalLog
from core.contracts import Signal as SigEnum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════
_TF_MINUTES: dict[str, int] = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30,
    "۱ ساعت": 60,
    "روزانه": 1440,
}

_TF_SKIP_FOR_IRT = frozenset({"۱ دقیقه"})

# حداقل اطمینان برای ثبت سیگنال (حتی برای کاربر جسور)
MIN_CONFIDENCE_TO_RECORD = 35

# مدت زمان Cooldown برای جلوگیری از ثبت تکراری در یک TF (به دقیقه)
COOLDOWN_MINUTES_SAME_TF = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_quote(ticker: str) -> str:
    upper = ticker.upper()
    if "IRT" in upper or "TMN" in upper:
        return "IRT"
    if "USDT" in upper or "USD" in upper:
        return "USDT"
    return "USDT"


def _signal_base(signal: str) -> str:
    if "LONG" in signal:
        return "LONG"
    if "SHORT" in signal:
        return "SHORT"
    return "NEUTRAL"


def _dedup_key_simple(
    ticker: str,
    tf_name: str,
    signal: str,
    source: str,
    market_type: str,
    risk_profile: str = "aggressive",
) -> str:
    return "|".join(
        [
            ticker,
            tf_name,
            _signal_base(signal),
            source,
            market_type,
            risk_profile,
        ]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
    """درج با نادیده‌گرفتن تعارض روی dedup_key."""
    if is_sqlite:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(SignalLog).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
        result = session.execute(stmt)
        session.commit()
        return bool(result.rowcount)
    else:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(SignalLog).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
        stmt = stmt.returning(SignalLog.id)

        result = session.execute(stmt)
        inserted_id = result.fetchone()
        session.commit()
        return inserted_id is not None


def _compute_is_weak(signal: str, confidence: int, consensus: str) -> bool:
    if "ضعیف" in signal:
        return True
    if confidence < 50:
        return True
    if consensus == "weak":
        return True
    return False


def _has_recent_same_tf_signal(
    session: Session,
    ticker: str,
    direction: str,
    source: str,
    tf_name: str,
    market_type: str = "futures",
    risk_profile: str = "aggressive",
) -> bool:
    """
    آیا سیگنال مشابهی در همین TF در چند دقیقه اخیر ثبت شده است؟
    (جهت‌های مختلف، market_type‌ها و risk_profile‌ها مستقل هستند)
    """
    cutoff = _utcnow() - timedelta(minutes=COOLDOWN_MINUTES_SAME_TF)
    existing = session.exec(
        select(SignalLog)
        .where(SignalLog.ticker == ticker)
        .where(SignalLog.direction == direction)
        .where(SignalLog.source == source)
        .where(SignalLog.tf == tf_name)
        .where(SignalLog.market_type == market_type)
        .where(SignalLog.risk_profile == risk_profile)
        .where(SignalLog.timestamp >= cutoff)
    ).first()
    return existing is not None


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
    origin: str = "auto_scan",
    trend_predicted_at_entry: str = "flat",
) -> bool:
    """
    ثبت سیگنال — نسخه ۶.۰.
    """
    # ═══ ۱. فیلترهای اولیه ═══
    if tf_name in _TF_SKIP_FOR_IRT and trade_side_irt:
        return False

    if not SigEnum.is_directional(signal):
        return False

    if not price or price <= 0:
        return False

    # 🔴 فیلتر نرم: سیگنال‌های با اطمینان بسیار پایین حتی در پروفایل جسور هم ثبت نمی‌شن
    if confidence < MIN_CONFIDENCE_TO_RECORD:
        logger.debug(
            f"[Recorder] سیگنال خیلی ضعیف رد شد: {ticker} {tf_name} (conf={confidence}%)"
        )
        return False

    # 🔴 جلوگیری از ثبت سیگنال ناقص
    if not sl_tp or not sl_tp.get("sl") or not sl_tp.get("tp"):
        logger.debug(f"[Recorder] سیگنال ناقص (بدون SL/TP): {ticker}")
        return False

    is_weak = _compute_is_weak(signal, confidence, consensus)
    now = _utcnow()

    dedup = _dedup_key_simple(
        ticker=ticker,
        tf_name=tf_name,
        signal=signal,
        source=source,
        market_type=market_type,
        risk_profile=risk_profile,
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
        "trend_predicted_at_entry": trend_predicted_at_entry,
    }

    try:
        with Session(engine) as session:
            # ═══ ۲. چک Cooldown در همان TF ═══
            if _has_recent_same_tf_signal(
                session, ticker, direction, source, tf_name, market_type, risk_profile
            ):
                logger.info(
                    f"[Recorder] ⏳ Cooldown active for {ticker} {tf_name} {signal} "
                    f"(less than {COOLDOWN_MINUTES_SAME_TF}m ago)"
                )
                return False

            # ═══ ۳. درج در دیتابیس ═══
            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            weak_flag = " [ضعیف]" if is_weak else ""
            logger.info(
                f"[Recorder] ✅ {ticker} {tf_name} {signal}{weak_flag} "
                f"({source}, {confidence}%, {market_type})"
            )

            try:
                from services.notifier import notify_signal

                notify_signal(values)
            except Exception as e:
                logger.warning(f"[Recorder] Notifier failed: {e}")

            return True
        return False
    except IntegrityError:
        logger.debug(f"[Recorder] تکراری در دیتابیس: {ticker} {tf_name}")
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا {ticker} {tf_name} {signal}")
        return False
