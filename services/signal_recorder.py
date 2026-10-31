"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس
============================================================
نسخه ۶.۴ · فاز ۱۲.۴
🔴 تغییرات:
  • MIN_CONFIDENCE_TO_RECORD = 25
  • استثنا برای سیگنال قوی (≥ 70%): حتی اگه is_worthwhile=False ثبت می‌شه
  • لاگ دقیق برای دیباگ
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
MIN_CONFIDENCE_TO_RECORD = 25
COOLDOWN_MINUTES_SAME_TF = 5

# 🔴 استثنا: سیگنال‌های قوی (بالاتر از این) حتی با is_worthwhile=False ثبت می‌شن
STRONG_CONFIDENCE_BYPASS = 70


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _signal_base(signal: str) -> str:
    if "LONG" in signal:
        return "LONG"
    if "SHORT" in signal:
        return "SHORT"
    return "NEUTRAL"


def _dedup_key_simple(
    ticker, tf_name, signal, source, market_type, risk_profile
) -> str:
    return "|".join(
        [ticker, tf_name, _signal_base(signal), source, market_type, risk_profile]
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


def _has_recent_same_tf_signal(
    session, ticker, direction, source, tf_name, market_type, risk_profile
) -> bool:
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

    """گروهی که بیشترین سهم را در جهت سیگنال داشت"""
    if not groups or direction not in ("long", "short"):
        return None
    best_group, best_abs = None, 0.0
    for g_name, g_data in groups.items():
        g_score = g_data.get("score", 0.0)
        if direction == "long" and g_score > best_abs:
            best_abs = g_score
            best_group = g_name
        elif direction == "short" and g_score < -best_abs:
            best_abs = abs(g_score)
            best_group = g_name
    return best_group


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

    # ═══ لاگ ورودی ═══
    logger.info(
        f"[Recorder] 🔍 trying: {ticker} {tf_name} signal={signal} "
        f"conf={confidence}% direction={direction} "
        f"is_worthwhile={is_worthwhile}"
    )

    # ═══ چک‌های اولیه ═══
    # 🔴 منبع واحد حقیقت: سیگنال‌های زیر ۴۰٪ اصلاً ثبت نمی‌شوند
    if confidence < 40:
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: conf={confidence}% < 40% (غیرسیگنال)"
        )
        return False

    # (بقیه چک‌های قبلی مثل tf_name in _TF_SKIP_FOR_IRT و ... بدون تغییر ادامه پیدا می‌کنند)

    # ═══ چک‌های اولیه ═══
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

    if confidence < MIN_CONFIDENCE_TO_RECORD:
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: conf={confidence}% "
            f"< {MIN_CONFIDENCE_TO_RECORD}%"
        )
        return False

    # 🔴 فاز ۱۲.۴ — استثنا برای سیگنال قوی
    if is_worthwhile is False:
        if confidence < STRONG_CONFIDENCE_BYPASS:
            logger.info(
                f"[Recorder] ⏭ {ticker} {tf_name}: is_worthwhile=False "
                f"(R:R پایین) — conf={confidence}% < {STRONG_CONFIDENCE_BYPASS}%"
            )
            return False
        # سیگنال قوی با R:R پایین — ثبت با هشدار
        logger.warning(
            f"[Recorder] ⚠️ {ticker} {tf_name}: is_worthwhile=False ولی "
            f"conf={confidence}% ≥ {STRONG_CONFIDENCE_BYPASS}% — ثبت با هشدار"
        )

    if not sl_tp or not sl_tp.get("sl") or not sl_tp.get("tp"):
        logger.debug(
            f"[Recorder] ⏭ {ticker} {tf_name}: sl/tp تعریف نشده " f"(sl_tp={sl_tp})"
        )
        return False

    # ═══ ساخت values ═══
    is_weak = _compute_is_weak(signal, confidence, consensus)
    now = _utcnow()
    dedup = _dedup_key_simple(
        ticker, tf_name, signal, source, market_type, risk_profile
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
            # ═══ cooldown ═══
            if _has_recent_same_tf_signal(
                session, ticker, direction, source, tf_name, market_type, risk_profile
            ):
                logger.info(
                    f"[Recorder] ⏭ {ticker} {tf_name}: cooldown "
                    f"({COOLDOWN_MINUTES_SAME_TF} دقیقه — سیگنال مشابه اخیراً ثبت شده)"
                )
                return False

            # ═══ insert ═══
            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            logger.info(f"[Recorder] ✅ {ticker} {tf_name} {signal} ({confidence}%)")
            try:
                from services.notifier import notify_signal

                notify_signal(values)
                logger.info(f"[Recorder] 📤 notified: {ticker} {tf_name}")
            except Exception as e:
                logger.warning(f"[Recorder] ❌ Notifier failed: {e}")
            return True
        else:
            logger.info(
                f"[Recorder] ⏭ {ticker} {tf_name}: dedup "
                f"(سیگنال مشابه قبلاً ثبت شده)"
            )
            return False

    except IntegrityError:
        logger.debug(f"[Recorder] ⏭ {ticker} {tf_name}: IntegrityError")
        return False
    except Exception:
        logger.exception(f"[Recorder] ❌ خطا {ticker} {tf_name}")
        return False
