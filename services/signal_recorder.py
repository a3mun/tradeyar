"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس
============================================================
نسخه ۷.۱ · فاز ۱۴.۹.۴
🔴 تغییرات:
  • STRONG_CONFIDENCE_BYPASS پویا بر اساس استراتژی
    → اسکالپ: 50 (چون R:R در TF پایین طبیعتاً پایینه)
    → سوئینگ: 70
    → پوزیشن: 75
  • min_conf_to_record برای اسکالپ نرم‌تر
  • strategy در dedup_key (از قبل)
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine, is_sqlite
from api.models import SignalLog
from core.contracts import Signal as SigEnum
from core.strategies import (
    get_strategy,
    get_cooldown_minutes,
    get_min_confidence,
)

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
MIN_CONFIDENCE_FLOOR = 30


def _get_strong_bypass(strategy: str) -> int:
    """
    🔴 فاز ۱۴.۹.۴ — آستانه‌ی bypass برای is_worthwhile=False.
    اسکالپ در TF پایین همیشه R:R پایین داره، پس نباید ۷۰٪ بخواد.
    """
    if strategy == "scalp":
        return 50
    elif strategy == "position":
        return 75
    return 70  # swing


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _signal_base(signal: str) -> str:
    if "LONG" in signal:
        return "LONG"
    if "SHORT" in signal:
        return "SHORT"
    return "NEUTRAL"


def _dedup_key_simple(
    ticker, tf_name, signal, source, market_type, risk_profile, strategy
) -> str:
    return "|".join(
        [
            ticker,
            tf_name,
            _signal_base(signal),
            source,
            market_type,
            risk_profile,
            strategy,
        ]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
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


def _has_recent_same_direction_signal(
    session,
    ticker,
    direction,
    source,
    tf_name,
    market_type,
    risk_profile,
    strategy,
    cooldown_min: int,
) -> bool:
    cutoff = _utcnow() - timedelta(minutes=cooldown_min)

    existing = session.exec(
        select(SignalLog)
        .where(SignalLog.ticker == ticker)
        .where(SignalLog.direction == direction)
        .where(SignalLog.source == source)
        .where(SignalLog.tf == tf_name)
        .where(SignalLog.market_type == market_type)
        .where(SignalLog.risk_profile == risk_profile)
        .where(SignalLog.strategy == strategy)
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
    strategy: str = "swing",
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
    pump_score: float | None = None,
    dump_score: float | None = None,
    pump_warning: str | None = None,
    pump_type: str | None = None,
    suggested_entry: float | None = None,
    suggested_entry_method: str | None = None,
    suggested_entry_distance_pct: float | None = None,
    tp_levels: dict | None = None,
    timeout_planned_min: int | None = None,
) -> bool:

    # 🔴 فاز ۱۴.۹.۴ — min_conf_to_record پویا
    strategy_min_conf = get_min_confidence(strategy, risk_profile)
    if strategy == "scalp":
        # اسکالپ: floor=25 (چون min_conf=30 ولی برای ثبت 25 کافیه)
        min_conf_to_record = max(25, strategy_min_conf - 5)
    else:
        min_conf_to_record = max(MIN_CONFIDENCE_FLOOR, strategy_min_conf)

    # 🔴 فاز ۱۴.۹.۴ — bypass پویا
    strong_bypass = _get_strong_bypass(strategy)

    logger.info(
        f"[Recorder] 🔍 trying: {ticker} {tf_name} strategy={strategy} "
        f"signal={signal} conf={confidence}% (min={min_conf_to_record}%) "
        f"direction={direction} is_worthwhile={is_worthwhile} "
        f"(bypass={strong_bypass}%)"
    )

    # ═══ چک‌های اولیه ═══
    if confidence < min_conf_to_record:
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: conf={confidence}% "
            f"< {min_conf_to_record}% (استراتژی {strategy})"
        )
        return False

    if tf_name in _TF_SKIP_FOR_IRT and trade_side_irt:
        logger.debug(f"[Recorder] ⏭ {ticker} {tf_name}: TF ۱ دقیقه برای IRT رد شد")
        return False

    if not SigEnum.is_directional(signal):
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: signal={signal} directional نیست"
        )
        return False

    if not price or price <= 0:
        logger.debug(f"[Recorder] ⏭ {ticker} {tf_name}: price={price} نامعتبر")
        return False

    # 🔴 فاز ۱۵: برای اسکالپ و سوئینگ، is_worthwhile نادیده گرفته میشه
    if is_worthwhile is False and strategy == "position":
        if confidence < strong_bypass:
            logger.info(
                f"[Recorder] ⏭ {ticker} {tf_name}: is_worthwhile=False "
                f"(R:R پایین) — conf={confidence}% < {strong_bypass}% "
                f"(استراتژی={strategy})"
            )
            return False

    if not sl_tp or not sl_tp.get("sl") or not sl_tp.get("tp"):
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: sl/tp تعریف نشده (sl_tp={sl_tp})"
        )
        return False

    # ═══ ساخت values ═══
    is_weak = _compute_is_weak(signal, confidence, consensus)
    now = _utcnow()
    dedup = _dedup_key_simple(
        ticker, tf_name, signal, source, market_type, risk_profile, strategy
    )

    sl = sl_tp.get("sl") if sl_tp else None
    tp = sl_tp.get("tp") if sl_tp else None
    sl_tp_type = sl_tp.get("type") if sl_tp else None

    active_trap = None
    if traps:
        for key, val in traps.items():
            if isinstance(val, dict) and val.get("active"):
                active_trap = key
                break

    tp_levels_json = None
    if tp_levels:
        try:
            tp_levels_json = json.dumps(tp_levels, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[Recorder] tp_levels serialize: {e!r}")

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
        "strategy": strategy,
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
        "pump_score": float(pump_score) if pump_score is not None else None,
        "dump_score": float(dump_score) if dump_score is not None else None,
        "pump_warning": pump_warning,
        "pump_type": pump_type,
        "suggested_entry": (
            float(suggested_entry) if suggested_entry is not None else None
        ),
        "suggested_entry_method": suggested_entry_method,
        "suggested_entry_distance_pct": (
            float(suggested_entry_distance_pct)
            if suggested_entry_distance_pct is not None
            else None
        ),
        "tp_levels_json": tp_levels_json,
        "timeout_planned_min": timeout_planned_min,
    }

    try:
        with Session(engine) as session:
            cooldown_min = get_cooldown_minutes(strategy, tf_name)
            if _has_recent_same_direction_signal(
                session,
                ticker,
                direction,
                source,
                tf_name,
                market_type,
                risk_profile,
                strategy,
                cooldown_min,
            ):
                logger.info(
                    f"[Recorder] ⏭ {ticker} {tf_name} [{strategy}]: cooldown "
                    f"({cooldown_min} دقیقه — سیگنال مشابه در همین جهت+استراتژی)"
                )
                return False

            # 🔴 اضافه کردن tp_levels فقط برای notifier (نه برای دیتابیس)
            values_for_notifier = dict(values)
            values_for_notifier["tp_levels"] = tp_levels

            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            logger.info(
                f"[Recorder] ✅ {ticker} {tf_name} [{strategy}] {signal} ({confidence}%)"
            )
            try:
                from services.notifier import notify_signal

                notify_signal(values_for_notifier)
                logger.info(f"[Recorder] 📤 notified: {ticker} {tf_name}")
            except Exception as e:
                logger.warning(f"[Recorder] ❌ Notifier failed: {e}")
            return True
        else:
            logger.info(
                f"[Recorder] ⏭ {ticker} {tf_name} [{strategy}]: dedup "
                f"(سیگنال مشابه قبلاً ثبت شده)"
            )
            return False

    except IntegrityError:
        logger.debug(f"[Recorder] ⏭ {ticker} {tf_name}: IntegrityError")
        return False
    except Exception:
        logger.exception(f"[Recorder] ❌ خطا {ticker} {tf_name}")
        return False
