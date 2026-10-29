"""
services/backtest_service.py
راستی‌آزمایی — موتور اصلی (نسخه ۷.۲ — فاز ۱۱.۶)
============================================================
🔴 تغییرات نسخه ۷.۲:
  ۱. حذف تعریف تکراری backtest_all (فقط یک نسخه باقی ماند).
  ۲. اصلاح trend_accuracy — حالا صفر نمی‌شود وقتی روند flat بوده.
  ۳. اصلاح _get_r_value — پشتیبانی از expired_pnl_pct برای timeout.
  ۴. حفظ باگ‌فیکس‌های قبلی: ۲ کندل، ترتیب زمانی TP/SL.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlmodel import Session, select, or_

from api.database import engine
from api.models import SignalLog
from core.data_fetcher import fetch_history_by_source

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

BACKTEST_TF_WHITELIST = ["۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]
BACKTEST_MAX_SIGNALS = 200


# ═══════════════════════════════════════════════════════════
# ابزارهای زمانی
# ═══════════════════════════════════════════════════════════
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_timeout_min(tf_name: str, market_type: str) -> int:
    tf_min = _TF_MINUTES.get(tf_name, 5)
    if tf_min <= 5:
        candles = 12
    elif tf_min <= 15:
        candles = 10
    elif tf_min <= 30:
        candles = 10
    elif tf_min <= 60:
        candles = 8
    else:
        candles = 7
    return tf_min * candles


def _to_utc_dt(ts) -> datetime:
    if isinstance(ts, pd.Timestamp):
        if ts.tz is None:
            return ts.tz_localize("UTC").to_pydatetime()
        return ts.tz_convert("UTC").to_pydatetime()
    if isinstance(ts, datetime):
        return _ensure_utc(ts)
    return _utcnow()


def fetch_ohlcv(
    ticker: str, source: str = "nobitex", tf_name: str = "۵ دقیقه", limit: int = 100
) -> Optional[pd.DataFrame]:
    try:
        interval_map = {
            "۱ دقیقه": "1m",
            "۵ دقیقه": "5m",
            "۱۵ دقیقه": "15m",
            "۳۰ دقیقه": "30m",
            "۱ ساعت": "1h",
            "روزانه": "1d",
        }
        period_map = {
            "۱ دقیقه": "1d",
            "۵ دقیقه": "5d",
            "۱۵ دقیقه": "10d",
            "۳۰ دقیقه": "1mo",
            "۱ ساعت": "3mo",
            "روزانه": "1y",
        }
        df = fetch_history_by_source(
            ticker=ticker,
            interval=interval_map.get(tf_name, "5m"),
            period=period_map.get(tf_name, "5d"),
            source=source,
            tf_name=tf_name,
        )
        if df is None or df.empty:
            return None
        return df.tail(limit) if len(df) > limit else df
    except Exception as e:
        logger.debug(f"[fetch_ohlcv] {ticker}/{source}/{tf_name}: {e!r}")
        return None


# ═══════════════════════════════════════════════════════════
# بررسی یک سیگنال
# ═══════════════════════════════════════════════════════════
def _check_one(log: SignalLog) -> Optional[str]:
    if log.result is not None or log.expired:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    entry_ts = _ensure_utc(log.timestamp)
    timeout_min = _compute_timeout_min(log.tf, log.market_type)
    elapsed_min = (_utcnow() - entry_ts).total_seconds() / 60

    # ─── محاسبه هوشمند تعداد کندل مورد نیاز ───
    tf_min = _TF_MINUTES.get(log.tf, 5)
    bars_needed = max(int(elapsed_min / tf_min) + 10, 50)

    if elapsed_min >= timeout_min:
        current_price = log.price
        try:
            df_exp = fetch_ohlcv(log.ticker, log.source, log.tf, limit=1)
            if df_exp is not None and len(df_exp) > 0:
                current_price = float(df_exp["close"].iloc[-1])
        except Exception:
            pass
        return _mark_expired(log, current_price)

    df = fetch_ohlcv(log.ticker, log.source, log.tf, limit=bars_needed)
    if df is None or len(df) == 0 or not isinstance(df.index, pd.DatetimeIndex):
        return None

    df_idx_utc = (
        df.index.tz_localize("UTC")
        if df.index.tz is None
        else df.index.tz_convert("UTC")
    )
    df_after = df[df_idx_utc >= entry_ts]
    if df_after.empty:
        return None

    is_long = log.direction == "long"

    # ─── بررسی ترتیب زمانی TP و SL ───
    if is_long:
        win_mask = df_after["high"] >= log.tp
        loss_mask = df_after["low"] <= log.sl
    else:
        win_mask = df_after["low"] <= log.tp
        loss_mask = df_after["high"] >= log.sl

    tp_time = df_after[win_mask].index[0] if win_mask.any() else None
    sl_time = df_after[loss_mask].index[0] if loss_mask.any() else None

    if tp_time and sl_time:
        if tp_time < sl_time:
            log.result = "win"
            log.exit_reason = "tp_hit"
            log.exit_price = log.tp
            log.result_time = _to_utc_dt(tp_time)
            return "win"
        else:
            log.result = "loss"
            log.exit_reason = "sl_hit"
            log.exit_price = log.sl
            log.result_time = _to_utc_dt(sl_time)
            return "loss"
    elif tp_time:
        log.result = "win"
        log.exit_reason = "tp_hit"
        log.exit_price = log.tp
        log.result_time = _to_utc_dt(tp_time)
        return "win"
    elif sl_time:
        log.result = "loss"
        log.exit_reason = "sl_hit"
        log.exit_price = log.sl
        log.result_time = _to_utc_dt(sl_time)
        return "loss"

    return None


def _mark_expired(log: SignalLog, current_price: float) -> str:
    log.expired = True
    log.exit_reason = "timeout"
    log.expired_at_price = current_price
    log.exit_price = current_price

    pnl_pct = (current_price - log.price) / log.price * 100
    if log.direction == "short":
        pnl_pct = -pnl_pct

    log.expired_pnl_pct = round(pnl_pct, 3)

    base_fee = log.fee_pct or 0.23
    fee_threshold = max(0.3, base_fee * 2.0)

    if pnl_pct > fee_threshold:
        log.expired_bias = "win"
        log.result = "win"
    elif pnl_pct < -fee_threshold:
        log.expired_bias = "loss"
        log.result = "loss"
    else:
        log.expired_bias = "flat"
        log.result = None

    log.result_time = _utcnow()
    return "expired"


# ═══════════════════════════════════════════════════════════
# بررسی همه‌ی سیگنال‌های pending — 🔴 فقط یک نسخه (تکراری حذف شد)
# ═══════════════════════════════════════════════════════════
def backtest_all(max_checks: int = BACKTEST_MAX_SIGNALS) -> dict:
    """بررسی همه‌ی سیگنال‌های pending."""
    checked, updated, errors = 0, 0, 0
    stats = {"win": 0, "loss": 0, "expired": 0}

    with Session(engine) as session:
        stmt = (
            select(SignalLog)
            .where(SignalLog.result.is_(None))
            .where(SignalLog.expired == False)  # noqa: E712
            .order_by(SignalLog.timestamp.desc())
            .limit(max_checks)
        )
        pending = session.exec(stmt).all()

        logger.info(f"[Backtest] {len(pending)} سیگنال pending")

        for log in pending:
            checked += 1
            try:
                outcome = _check_one(log)
                if outcome:
                    updated += 1
                    stats[outcome] = stats.get(outcome, 0) + 1
                    session.add(log)
                    session.commit()
            except Exception as e:
                logger.debug(f"[Backtest] خطا {log.ticker}: {e!r}")
                errors += 1
                session.rollback()
                continue

    result = {
        "ok": True,
        "checked": checked,
        "updated": updated,
        "win": stats["win"],
        "loss": stats["loss"],
        "expired": stats["expired"],
        "errors": errors,
        "skipped": 0,
    }
    logger.info(f"[Backtest] ✅ {result}")
    return result


def _fetch_closed_rows(
    session: Session,
    tf: str,
    source: str,
    time_filter: str,
    risk_profile: str,
    limit: int,
) -> list[SignalLog]:
    stmt = select(SignalLog).where(
        or_(SignalLog.result.isnot(None), SignalLog.expired == True)  # noqa: E712
    )
    if tf:
        stmt = stmt.where(SignalLog.tf == tf)
    if source:
        stmt = stmt.where(SignalLog.source == source)
    if risk_profile:
        stmt = stmt.where(SignalLog.risk_profile == risk_profile)
    if time_filter != "all":
        now = _utcnow()
        days = {"1d": 1, "7d": 7, "30d": 30}.get(time_filter)
        if days:
            stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=days))
    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    return session.exec(stmt).all()


# ═══════════════════════════════════════════════════════════
# محاسبه R واقعی
# ═══════════════════════════════════════════════════════════
def _get_r_value(log: SignalLog) -> float:
    """محاسبه R واقعی بر اساس ریسک اولیه"""
    risk_pct = (
        abs(log.price - log.sl) / log.price * 100 if log.price and log.sl else 1.0
    )

    if log.result == "win":
        if log.exit_reason == "tp_hit":
            return log.rr or 1.0
        elif log.exit_reason == "timeout" and log.expired_pnl_pct is not None:
            return abs(log.expired_pnl_pct) / risk_pct if risk_pct > 0 else 0.0
    elif log.result == "loss":
        if log.exit_reason == "sl_hit":
            return -1.0
        elif log.exit_reason == "timeout" and log.expired_pnl_pct is not None:
            return -abs(log.expired_pnl_pct) / risk_pct if risk_pct > 0 else 0.0
    return 0.0


# ═══════════════════════════════════════════════════════════
# آمار کلی — 🔴 trend_accuracy اصلاح‌شده
# ═══════════════════════════════════════════════════════════
def compute_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
) -> dict:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(session, tf, source, time_filter, risk_profile, limit)

    win_rows = [r for r in rows if r.tf in BACKTEST_TF_WHITELIST]
    total, expired = len(rows), sum(1 for r in rows if r.expired)

    tp_hits = sum(1 for r in win_rows if r.exit_reason == "tp_hit")
    sl_hits = sum(1 for r in win_rows if r.exit_reason == "sl_hit")
    timeout_wins = sum(
        1 for r in win_rows if r.exit_reason == "timeout" and r.expired_bias == "win"
    )
    timeout_losses = sum(
        1 for r in win_rows if r.exit_reason == "timeout" and r.expired_bias == "loss"
    )
    timeout_flats = sum(
        1 for r in win_rows if r.exit_reason == "timeout" and r.expired_bias == "flat"
    )

    closed_real = tp_hits + sl_hits + timeout_wins + timeout_losses
    win_rate = (tp_hits / closed_real * 100) if closed_real > 0 else 0.0
    direction_acc = (
        ((tp_hits + timeout_wins) / closed_real * 100) if closed_real > 0 else 0.0
    )

    # 🔴 اصلاح trend_accuracy — حالا فقط سیگنال‌های directional با پیش‌بینی مشخص
    # در نظر گرفته می‌شوند. اگر روند flat بوده و سیگنال جهت‌دار داشته،
    # به‌عنوان "نه درست نه غلط" رد می‌شود (نه اینکه به wrong اضافه شود).
    trend_correct, trend_wrong = 0, 0
    for r in rows:
        if r.result not in ("win", "loss"):
            continue
        pred = r.trend_predicted_at_entry
        if not pred or pred == "flat":
            continue

        # پیش‌بینی bull: فقط long می‌تواند درست باشد
        if pred == "bull":
            if r.direction == "long" and r.result == "win":
                trend_correct += 1
            elif r.direction == "long" and r.result == "loss":
                trend_wrong += 1
            elif r.direction == "short":
                # پیش‌بینی bull ولی short گرفته → پیش‌بینی غلط
                trend_wrong += 1
        # پیش‌بینی bear: فقط short می‌تواند درست باشد
        elif pred == "bear":
            if r.direction == "short" and r.result == "win":
                trend_correct += 1
            elif r.direction == "short" and r.result == "loss":
                trend_wrong += 1
            elif r.direction == "long":
                trend_wrong += 1

    trend_total = trend_correct + trend_wrong
    trend_acc = (trend_correct / trend_total * 100) if trend_total > 0 else 0.0

    # ─── محاسبه Profit Factor و Expectancy بر اساس R واقعی ───
    r_values = [_get_r_value(r) for r in win_rows]
    r_values = [r for r in r_values if r != 0]
    gross_profit = sum(r for r in r_values if r > 0)
    gross_loss = abs(sum(r for r in r_values if r < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    rr_nets = [r.rr_net for r in rows if r.rr_net is not None]
    avg_rr_net = sum(rr_nets) / len(rr_nets) if rr_nets else 0.0

    wins_r = [r for r in r_values if r > 0]
    losses_r = [r for r in r_values if r < 0]
    avg_win = (gross_profit / len(wins_r)) if wins_r else 0.0
    avg_loss = (gross_loss / len(losses_r)) if losses_r else 0.0
    p_win = win_rate / 100
    p_loss = 1 - p_win
    expectancy = (
        (p_win * avg_win) - (p_loss * avg_loss)
        if (avg_win > 0 or avg_loss > 0)
        else 0.0
    )

    return {
        "total": total,
        "tp_hits": tp_hits,
        "sl_hits": sl_hits,
        "timeout_wins": timeout_wins,
        "timeout_losses": timeout_losses,
        "timeout_flats": timeout_flats,
        "pending": 0,
        "expired": expired,
        "win_rate": round(win_rate, 2),
        "direction_accuracy": round(direction_acc, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_rr_net": round(avg_rr_net, 3),
        "expectancy": round(expectancy, 3),
        "trend_correct": trend_correct,
        "trend_wrong": trend_wrong,
        "trend_accuracy": round(trend_acc, 2),
    }


# ═══════════════════════════════════════════════════════════
# آمار به تفکیک رژیم بازار
# ═══════════════════════════════════════════════════════════
def compute_stats_by_regime(
    time_filter: str = "all", risk_profile: str = ""
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session, "", "", time_filter, risk_profile, BACKTEST_MAX_SIGNALS
        )

    by_regime: dict[str, list[SignalLog]] = {}
    for r in rows:
        regime_val = r.regime or "unknown"
        by_regime.setdefault(regime_val, []).append(r)

    for regime, items in by_regime.items():
        total = len(items)
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        tw = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "win"
        )
        tl = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "loss"
        )
        closed = tp_hits + sl_hits + tw + tl
        wr = (tp_hits / closed * 100) if closed > 0 else 0.0
        da = ((tp_hits + tw) / closed * 100) if closed > 0 else 0.0
        result[regime] = {
            "total": total,
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "timeout_wins": tw,
            "timeout_losses": tl,
            "win_rate": round(wr, 2),
            "direction_accuracy": round(da, 2),
        }

    return result


# ═══════════════════════════════════════════════════════════
# آمار به تفکیک TF
# ═══════════════════════════════════════════════════════════
def compute_stats_by_tf(
    time_filter: str = "all", risk_profile: str = "", limit: int = BACKTEST_MAX_SIGNALS
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    result: dict[str, dict] = {}
    with Session(engine) as session:
        rows = _fetch_closed_rows(session, "", "", time_filter, risk_profile, limit)

    by_tf: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_tf.setdefault(r.tf, []).append(r)

    for tf, items in by_tf.items():
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        tw = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "win"
        )
        tl = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "loss"
        )
        closed = tp_hits + sl_hits + tw + tl
        wr = (tp_hits / closed * 100) if closed > 0 else 0.0
        da = ((tp_hits + tw) / closed * 100) if closed > 0 else 0.0

        # trend accuracy per TF
        tc, tw_wrong = 0, 0
        for r in items:
            if r.result not in ("win", "loss"):
                continue
            pred = r.trend_predicted_at_entry
            if not pred or pred == "flat":
                continue
            if pred == "bull":
                if r.direction == "long" and r.result == "win":
                    tc += 1
                elif r.direction == "long" and r.result == "loss":
                    tw_wrong += 1
                elif r.direction == "short":
                    tw_wrong += 1
            elif pred == "bear":
                if r.direction == "short" and r.result == "win":
                    tc += 1
                elif r.direction == "short" and r.result == "loss":
                    tw_wrong += 1
                elif r.direction == "long":
                    tw_wrong += 1
        t_total = tc + tw_wrong
        t_acc = (tc / t_total * 100) if t_total > 0 else 0.0

        result[tf] = {
            "total": len(items),
            "wins": tp_hits,
            "losses": sl_hits,
            "win_rate": round(wr, 2),
            "direction_accuracy": round(da, 2),
            "trend_accuracy": round(t_acc, 2),
        }

    return result


# ═══════════════════════════════════════════════════════════
# آمار به تفکیک کیفیت
# ═══════════════════════════════════════════════════════════
def compute_stats_by_quality(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(session, tf, source, time_filter, risk_profile, limit)

    def _stats(items: list[SignalLog]) -> dict:
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        tw = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "win"
        )
        tl = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "loss"
        )
        closed = tp_hits + sl_hits + tw + tl
        wr = (tp_hits / closed * 100) if closed > 0 else 0.0
        da = ((tp_hits + tw) / closed * 100) if closed > 0 else 0.0
        return {
            "total": len(items),
            "wins": tp_hits,
            "losses": sl_hits,
            "win_rate": round(wr, 2),
            "direction_accuracy": round(da, 2),
        }

    return {
        "all": _stats(rows),
        "strong": _stats([r for r in rows if r.confidence >= 70]),
        "normal": _stats([r for r in rows if 50 <= r.confidence < 70]),
        "weak": _stats([r for r in rows if r.confidence < 50]),
    }


# ═══════════════════════════════════════════════════════════
# آمار به تفکیک پروفایل
# ═══════════════════════════════════════════════════════════
def compute_stats_by_profile(time_filter: str = "all") -> dict[str, dict]:
    result: dict[str, dict] = {}
    with Session(engine) as session:
        stmt = select(SignalLog)
        if time_filter != "all":
            now = _utcnow()
            days = {"1d": 1, "7d": 7, "30d": 30}.get(time_filter)
            if days:
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=days))
        rows = session.exec(stmt).all()

    by_profile: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_profile.setdefault(r.risk_profile, []).append(r)

    for profile, items in by_profile.items():
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        closed = tp_hits + sl_hits
        wr = (tp_hits / closed * 100) if closed > 0 else 0.0
        result[profile] = {
            "total": len(items),
            "wins": tp_hits,
            "losses": sl_hits,
            "win_rate": round(wr, 2),
        }

    return result
