"""
services/backtest_service.py
راستی‌آزمایی — موتور اصلی
============================================================
نسخه ۶.۰ · فاز ۱۰.۱۰
🔴 تغییرات نسبت به ۵.۲:
  • + exit_reason: "tp_hit" | "sl_hit" | "timeout"
  • + _compute_timeout_min اصلاح شد (زمان‌های طولانی‌تر برای روزانه)
  • + compute_stats: تفکیک دقیق tp_hits, sl_hits, timeout_wins, timeout_losses
  • + trend_accuracy بر اساس trend_predicted_at_entry (نه نشت اطلاعات نتیجه)
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

# 🔴 TFهای مجاز برای محاسبه نرخ برد (۱ و ۵ دقیقه نویزی هستند و جدا محاسبه می‌شوند)
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
    """
    محاسبه زمان انقضا (به دقیقه).
    🔴 فاز ۱۰.۱۰: زمان‌ها واقعی‌تر شدند تا سیگنال‌ها زودتر از موعد منقضی نشن.
    """
    tf_min = _TF_MINUTES.get(tf_name, 5)

    if tf_min <= 5:
        candles = 12
    elif tf_min <= 15:
        candles = 10
    elif tf_min <= 30:
        candles = 10
    elif tf_min <= 60:
        candles = 8
    else:  # روزانه
        candles = 7  # ۱ هفته معاملاتی

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
    """wrapper سبک برای دریافت کندل"""
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
    """بررسی یک سیگنال باز"""
    if log.result is not None or log.expired:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    entry_ts = _ensure_utc(log.timestamp)
    timeout_min = _compute_timeout_min(log.tf, log.market_type)
    elapsed_min = (_utcnow() - entry_ts).total_seconds() / 60

    # ─── چک Timeout ───
    if elapsed_min >= timeout_min:
        current_price = log.price
        try:
            df_exp = fetch_ohlcv(log.ticker, log.source, log.tf, limit=1)
            if df_exp is not None and len(df_exp) > 0:
                current_price = float(df_exp["close"].iloc[-1])
        except Exception:
            pass
        return _mark_expired(log, current_price)

    # ─── دریافت دیتا برای چک TP/SL ───
    df = fetch_ohlcv(log.ticker, log.source, log.tf, limit=2)
    if df is None or len(df) == 0:
        return None

    if not isinstance(df.index, pd.DatetimeIndex):
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

    # ─── چک TP/SL ───
    if is_long:
        win_mask = df_after["high"] >= log.tp
        if win_mask.any():
            log.result = "win"
            log.exit_reason = "tp_hit"
            log.exit_price = log.tp
            log.result_time = _to_utc_dt(df_after[win_mask].index[0])
            return "win"

        loss_mask = df_after["low"] <= log.sl
        if loss_mask.any():
            log.result = "loss"
            log.exit_reason = "sl_hit"
            log.exit_price = log.sl
            log.result_time = _to_utc_dt(df_after[loss_mask].index[0])
            return "loss"

    else:  # short
        win_mask = df_after["low"] <= log.tp
        if win_mask.any():
            log.result = "win"
            log.exit_reason = "tp_hit"
            log.exit_price = log.tp
            log.result_time = _to_utc_dt(df_after[win_mask].index[0])
            return "win"

        loss_mask = df_after["high"] >= log.sl
        if loss_mask.any():
            log.result = "loss"
            log.exit_reason = "sl_hit"
            log.exit_price = log.sl
            log.result_time = _to_utc_dt(df_after[loss_mask].index[0])
            return "loss"

    return None


# ═══════════════════════════════════════════════════════════
# بستن با مهلت (Timeout)
# ═══════════════════════════════════════════════════════════
def _mark_expired(log: SignalLog, current_price: float) -> str:
    """بستن سیگنال با مهلت"""
    log.expired = True
    log.exit_reason = "timeout"
    log.expired_at_price = current_price
    log.exit_price = current_price

    pnl_pct = (current_price - log.price) / log.price * 100
    if log.direction == "short":
        pnl_pct = -pnl_pct

    log.expired_pnl_pct = round(pnl_pct, 3)

    # 🔴 آستانه کارمزد برای تعیین برنده/بازنده در حالت Timeout
    fee_threshold = (log.fee_pct or 0.23) * 1.5

    if pnl_pct > fee_threshold:
        log.expired_bias = "win"
        log.result = "win"  # ثبت به عنوان برد (جهت درست بود)
    elif pnl_pct < -fee_threshold:
        log.expired_bias = "loss"
        log.result = "loss"
    else:
        log.expired_bias = "flat"
        log.result = None

    log.result_time = _utcnow()
    return "expired"


# ═══════════════════════════════════════════════════════════
# اجرای backtest
# ═══════════════════════════════════════════════════════════
def backtest_all(max_checks: int = BACKTEST_MAX_SIGNALS) -> dict:
    """بررسی همه‌ی سیگنال‌های pending."""
    checked, updated, errors = 0, 0, 0
    stats = {"win": 0, "loss": 0, "expired": 0}

    with Session(engine) as session:
        stmt = (
            select(SignalLog)
            .where(SignalLog.result.is_(None))
            .where(SignalLog.expired == False)
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


# ═══════════════════════════════════════════════════════════
# ابزار داخلی: گرفتن ردیف‌های بسته‌شده
# ═══════════════════════════════════════════════════════════
def _fetch_closed_rows(
    session: Session,
    tf: str,
    source: str,
    time_filter: str,
    risk_profile: str,
    limit: int,
) -> list[SignalLog]:
    stmt = select(SignalLog).where(
        or_(SignalLog.result.isnot(None), SignalLog.expired == True)
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
# compute_stats — آمار کلی
# ═══════════════════════════════════════════════════════════
def compute_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
) -> dict:
    """
    🔴 آمار تفکیک‌شده:
    - win_rate: فقط tp_hit (برد واقعی)
    - direction_accuracy: tp_hit + timeout_win (جهت درست)
    - trend_accuracy: trend_predicted_at_entry درست بوده
    """
    limit = max(50, min(limit, 500))

    with Session(engine) as session:
        rows = _fetch_closed_rows(session, tf, source, time_filter, risk_profile, limit)

    all_rows = rows
    win_rows = [r for r in rows if r.tf in BACKTEST_TF_WHITELIST]

    total = len(all_rows)
    expired = sum(1 for r in all_rows if r.expired)

    # ─── آمار تفکیک‌شده (فقط روی TFهای معتبر) ───
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

    # نرخ برد واقعی (فقط TP)
    closed_real = tp_hits + sl_hits + timeout_wins + timeout_losses
    win_rate = (tp_hits / closed_real * 100) if closed_real > 0 else 0.0

    # دقت جهت (TP یا Timeout Win)
    direction_correct = tp_hits + timeout_wins
    direction_accuracy = (
        (direction_correct / closed_real * 100) if closed_real > 0 else 0.0
    )

    # ─── دقت روند (بر اساس پیش‌بینی لحظه ورود) ───
    trend_correct = 0
    trend_wrong = 0
    for r in all_rows:
        pred = r.trend_predicted_at_entry
        if not pred or pred == "flat":
            continue
        if pred == "bull" and r.result == "win":
            trend_correct += 1
        elif pred == "bear" and r.result == "win":  # شورت موفق
            trend_correct += 1
        elif r.result in ("win", "loss"):
            trend_wrong += 1

    trend_total = trend_correct + trend_wrong
    trend_accuracy = (trend_correct / trend_total * 100) if trend_total > 0 else 0.0

    # ─── Profit Factor ───
    win_pnls = [
        abs(r.expired_pnl_pct)
        for r in win_rows
        if r.result == "win" and r.expired_pnl_pct is not None
    ]
    loss_pnls = [
        abs(r.expired_pnl_pct)
        for r in win_rows
        if r.result == "loss" and r.expired_pnl_pct is not None
    ]
    win_pnls += [
        abs(r.rr_net)
        for r in win_rows
        if r.result == "win" and r.rr_net and r.expired_pnl_pct is None
    ]
    loss_pnls += [
        abs(r.rr_net)
        for r in win_rows
        if r.result == "loss" and r.rr_net and r.expired_pnl_pct is None
    ]

    profit_factor = (sum(win_pnls) / sum(loss_pnls)) if sum(loss_pnls) > 0 else 0.0

    rr_nets = [r.rr_net for r in all_rows if r.rr_net is not None]
    avg_rr_net = sum(rr_nets) / len(rr_nets) if rr_nets else 0.0

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
        "direction_accuracy": round(direction_accuracy, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_rr_net": round(avg_rr_net, 3),
        "expectancy": round((win_rate / 100) * avg_rr_net - (1 - win_rate / 100), 3),
        "trend_correct": trend_correct,
        "trend_wrong": trend_wrong,
        "trend_accuracy": round(trend_accuracy, 2),
    }


# ═══════════════════════════════════════════════════════════
# compute_stats_by_tf
# ═══════════════════════════════════════════════════════════
def compute_stats_by_tf(
    time_filter: str = "all", risk_profile: str = "", limit: int = BACKTEST_MAX_SIGNALS
) -> dict[str, dict]:
    """آمار به تفکیک TF"""
    limit = max(50, min(limit, 500))
    result: dict[str, dict] = {}

    with Session(engine) as session:
        rows = _fetch_closed_rows(session, "", "", time_filter, risk_profile, limit)

    by_tf: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_tf.setdefault(r.tf, []).append(r)

    for tf, items in by_tf.items():
        total = len(items)
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        timeout_wins = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "win"
        )
        timeout_losses = sum(
            1 for r in items if r.exit_reason == "timeout" and r.expired_bias == "loss"
        )

        closed_real = tp_hits + sl_hits + timeout_wins + timeout_losses
        win_rate = (tp_hits / closed_real * 100) if closed_real > 0 else 0.0
        direction_acc = (
            ((tp_hits + timeout_wins) / closed_real * 100) if closed_real > 0 else 0.0
        )

        tc, tw = 0, 0
        for r in items:
            pred = r.trend_predicted_at_entry
            if not pred or pred == "flat":
                continue
            if pred == "bull" and r.result == "win":
                tc += 1
            elif pred == "bear" and r.result == "win":
                tc += 1
            elif r.result in ("win", "loss"):
                tw += 1

        trend_acc = (tc / (tc + tw) * 100) if (tc + tw) > 0 else 0.0

        result[tf] = {
            "total": total,
            "wins": tp_hits,
            "losses": sl_hits,
            "pending": 0,
            "expired": sum(1 for r in items if r.expired),
            "win_rate": round(win_rate, 2),
            "direction_accuracy": round(direction_acc, 2),
            "trend_accuracy": round(trend_acc, 2),
        }

    return result


# ═══════════════════════════════════════════════════════════
# compute_stats_by_quality
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

        return {
            "total": total,
            "wins": tp_hits,
            "losses": sl_hits,
            "pending": 0,
            "expired": sum(1 for r in items if r.expired),
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
# compute_stats_by_profile (اصلاح خطای import)
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
        total = len(items)
        tp_hits = sum(1 for r in items if r.exit_reason == "tp_hit")
        sl_hits = sum(1 for r in items if r.exit_reason == "sl_hit")
        closed = tp_hits + sl_hits
        win_rate = (tp_hits / closed * 100) if closed > 0 else 0.0

        result[profile] = {
            "total": total,
            "wins": tp_hits,
            "losses": sl_hits,
            "win_rate": round(win_rate, 2),
        }

    return result
