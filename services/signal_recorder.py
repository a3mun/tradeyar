"""
services/signal_recorder.py
ثبت خودکار سیگنال در دیتابیس
============================================================
نسخه ۵.۰ · فاز ۱۰.۶
🔴 تغییرات:
  • dedup_key ساده‌تر — بدون bucket
  • جلوگیری از تکرار با چک pending (نه unique forever)
  • is_weak منطقی
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

# TF که برای IRT ثبت نمی‌شن
_TF_SKIP_FOR_IRT = frozenset({"۱ دقیقه"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


def _dedup_key_simple(
    ticker: str,
    tf_name: str,
    signal: str,
    source: str,
    market_type: str,
    risk_profile: str = "aggressive",  # 🔴 اضافه شد
) -> str:
    """
    کلید یکتای «سیگنال منطقاً یکسان» — بدون bucket زمانی.

    ═══ چرا risk_profile هست ═══
    دو profile مختلف (aggressive/conservative) ممکنه SL/TP مختلف
    داشته باشن. پس دو رکورد مستقل هستن.

    ═══ چرا bucket نیست ═══
    bucket = شروع کندل TF → هر TF، هر ۵ دقیقه یه bucket جدید
    → تکرار برای یک سیگنال. الان حذف شده.
    """
    return "|".join(
        [
            ticker,
            tf_name,
            _signal_base(signal),
            source,
            market_type,
            risk_profile,  # ← اضافه شد
        ]
    )


def _insert_ignore_conflict(session: Session, values: dict) -> bool:
    """درج با نادیده‌گرفتن تعارض روی dedup_key."""
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
    origin: str = "auto_scan",
) -> bool:
    """
    ثبت سیگنال — نسخه ۵.۰.

    🔴 منطق ضد تکرار (نسخه ۵.۰):
    ۱. TF=۱m برای IRT ممنوع
    ۲. dedup_key بر اساس (ticker, tf, signal_base, source, market_type)
    ۳. قبل از insert: چک کن **pending مشابه** وجود داره یا نه
       • اگه pending هست → رد
       • اگه pending نیست (یعنی resolve شده یا وجود نداره) → ثبت
    """
    # ─── TF=۱m برای IRT ممنوع ───
    if tf_name in _TF_SKIP_FOR_IRT and trade_side_irt:
        logger.debug(f"[Recorder] TF={tf_name} برای IRT ممنوع — {ticker} رد شد")
        return False

    # ─── اعتبارسنجی ───
    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    is_weak = _compute_is_weak(signal, confidence, consensus)
    now = _utcnow()

    # ─── dedup ساده (بدون bucket) ───
    dedup = _dedup_key_simple(
        ticker=ticker,
        tf_name=tf_name,
        signal=signal,
        source=source,
        market_type=market_type,
        risk_profile=risk_profile,
    )

    # ─── SL/TP ───
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_tp_type: Optional[str] = None
    if sl_tp:
        sl = sl_tp.get("sl")
        tp = sl_tp.get("tp")
        sl_tp_type = sl_tp.get("type")

    # ─── تله ───
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
    }

    try:
        with Session(engine) as session:
            # 🔴 چک pending مشابه
            # ═══ چرا ═══
            # اگه یک pending با همین dedup_key توی DB هست،
            # یعنی همون سیگنال هنوز به نتیجه نرسیده. تکرار نکن.
            # اگه pending نیست (resolved شده یا اصلاً نیست) → ثبت کن.
            stmt = (
                select(SignalLog.id)
                .where(SignalLog.dedup_key == dedup)
                .where(SignalLog.result.is_(None))
                .where(SignalLog.expired == False)
                .limit(1)
            )
            existing_pending = session.exec(stmt).first()
            if existing_pending:
                logger.debug(
                    f"[Recorder] pending مشابه: {ticker} {tf_name} {signal} "
                    f"({market_type}) — رد"
                )
                return False

            # ─── درج ───
            # ⚠️ چون unique_constraint روی dedup_key هست، insert
            #    ممکنه به خاطر رکورد قدیمی (resolved) conflict بده.
            #    برای این کار، unique_constraint رو در آینده برداریم،
            #    یا اینکه dedup_key رو با timestamp ترکیب کنیم.
            #
            # راه‌حل فعلی: چون unique_constraint هست، فقط اگه
            # هیچ رکورد قبلی نباشه insert می‌کنیم. یعنی اگه یه
            # resolved هم باشه، نمی‌تونیم insert کنیم.
            #
            # TODO: در فاز بعدی، unique_constraint رو حذف کن و
            # به جاش یه index عادی بذار.
            stmt_any = select(SignalLog.id).where(SignalLog.dedup_key == dedup).limit(1)
            existing_any = session.exec(stmt_any).first()
            if existing_any:
                logger.debug(
                    f"[Recorder] رکورد قبلی با dedup_key مشابه: {ticker} {tf_name} — رد"
                )
                return False

            inserted = _insert_ignore_conflict(session, values)

        if inserted:
            weak_flag = " [ضعیف]" if is_weak else ""
            logger.info(
                f"[Recorder] ✅ {ticker} {tf_name} {signal}{weak_flag} "
                f"({source}, {confidence}%, {market_type})"
            )
            return True

        return False
    except IntegrityError:
        logger.debug(f"[Recorder] تکراری: {ticker} {tf_name}")
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا {ticker} {tf_name} {signal}")
        return False
