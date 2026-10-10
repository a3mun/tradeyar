"""
services/backtest_service.py
راستی‌آزمایی — موتور اصلی
============================================================
نسخه ۴.۴ · فاز ۱۰.۴ (سازگار با تست‌ها)
🔴 تغییرات نسبت به ۴.۳:
  • فیلتر کندل‌های قبل از entry (log.timestamp)
  • result_time = زمان کندلی که TP/SL رو زده
  • نرمال‌سازی index df به UTC (naive → aware)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlmodel import Session, select

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

BACKTEST_TF_WHITELIST = ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"]
BACKTEST_MAX_SIGNALS = 100


# ═══════════════════════════════════════════════════════════
# fetch_ohlcv — wrapper سطح ماژول
# ═══════════════════════════════════════════════════════════
_TF_INTERVAL_MAP = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1d",
}

_TF_PERIOD_MAP = {
    "۱ دقیقه": "1d",
    "۵ دقیقه": "5d",
    "۱۵ دقیقه": "10d",
    "۳۰ دقیقه": "1mo",
    "۱ ساعت": "3mo",
    "روزانه": "1y",
}


def fetch_ohlcv(
    ticker: str,
    source: str = "nobitex",
    tf_name: str = "۵ دقیقه",
    limit: int = 100,
) -> Optional[pd.DataFrame]:
    """wrapper سبک برای fetch_history_by_source."""
    interval = _TF_INTERVAL_MAP.get(tf_name, "5m")
    period = _TF_PERIOD_MAP.get(tf_name, "5d")

    try:
        df = fetch_history_by_source(
            ticker=ticker,
            interval=interval,
            period=period,
            source=source,
            tf_name=tf_name,
        )
        if df is None or df.empty:
            return None
        if len(df) > limit:
            df = df.tail(limit)
        return df
    except Exception as e:
        logger.debug(f"[fetch_ohlcv] {ticker}/{source}/{tf_name}: {e!r}")
        return None


# ═══════════════════════════════════════════════════════════
# ابزارهای زمانی
# ═══════════════════════════════════════════════════════════
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    """اگه naive بود، UTC فرض کن"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_timeout_min(tf_name: str, market_type: str) -> int:
    """timeout بر اساس TF."""
    tf_min = _TF_MINUTES.get(tf_name, 5)

    if tf_min <= 5:
        candles = 5
    elif tf_min <= 30:
        candles = 4
    elif tf_min <= 60:
        candles = 3
    else:
        candles = 2

    return tf_min * candles


# ═══════════════════════════════════════════════════════════
# بررسی یک سیگنال
# ═══════════════════════════════════════════════════════════
def _check_one(log: SignalLog) -> Optional[str]:
    """
    بررسی یک سیگنال — خودش fetch_ohlcv رو صدا می‌زنه.

    🔴 منطق (نسخه ۴.۴):
    ۱. کندل‌های قبل از entry (log.timestamp) فیلتر می‌شن
    ۲. روی کندل‌های بعد از entry، SL/TP چک می‌شه (high/low)
    ۳. result_time = زمان کندلی که TP/SL رو زده (نه _utcnow)
    """
    # ─── ۱. قبلاً بررسی شده ───
    if log.result is not None:
        return None
    if log.expired:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    # ─── ۲. نرمال‌سازی timestamp entry ───
    entry_ts = _ensure_utc(log.timestamp)

    # ─── ۳. چک timeout اول ───
    timeout_min = _compute_timeout_min(log.tf, log.market_type)
    elapsed_min = (_utcnow() - entry_ts).total_seconds() / 60

    if elapsed_min >= timeout_min:
        return _mark_expired(log, log.price)

    # ─── ۴. fetch قیمت ───
    df = fetch_ohlcv(
        ticker=log.ticker,
        source=log.source,
        tf_name=log.tf,
        limit=2,
    )
    if df is None or len(df) == 0:
        return None

    # ─── ۵. فیلتر کندل‌های قبل از entry ───
    # index df ممکنه naive باشه — به UTC تبدیل کن
    if not isinstance(df.index, pd.DatetimeIndex):
        return None

    df_idx = df.index
    if df_idx.tz is None:
        # naive → UTC فرض کن
        df_idx_utc = df_idx.tz_localize("UTC")
    else:
        df_idx_utc = df_idx.tz_convert("UTC")

    # فقط کندل‌هایی که timestamp >= entry_ts
    mask = df_idx_utc >= entry_ts
    df_after = df[mask]

    if df_after.empty:
        return None  # هیچ کندلی بعد از entry نیست

    # ─── ۶. چک SL/TP روی کندل‌های بعد از entry ───
    is_long = log.direction == "long"

    if is_long:
        # ─── WIN: هر کندل high >= TP ───
        win_mask = df_after["high"] >= log.tp
        if win_mask.any():
            # اولین کندلی که TP رو زد
            first_idx = df_after[win_mask].index[0]
            log.result = "win"
            log.exit_price = log.tp
            log.result_time = _to_utc_dt(first_idx)
            log.trend_correct = True
            return "win"

        # ─── LOSS: هر کندل low <= SL ───
        loss_mask = df_after["low"] <= log.sl
        if loss_mask.any():
            first_idx = df_after[loss_mask].index[0]
            log.result = "loss"
            log.exit_price = log.sl
            log.result_time = _to_utc_dt(first_idx)
            log.trend_correct = False
            return "loss"

    else:  # short
        # ─── WIN: هر کندل low <= TP ───
        win_mask = df_after["low"] <= log.tp
        if win_mask.any():
            first_idx = df_after[win_mask].index[0]
            log.result = "win"
            log.exit_price = log.tp
            log.result_time = _to_utc_dt(first_idx)
            log.trend_correct = True
            return "win"

        # ─── LOSS: هر کندل high >= SL ───
        loss_mask = df_after["high"] >= log.sl
        if loss_mask.any():
            first_idx = df_after[loss_mask].index[0]
            log.result = "loss"
            log.exit_price = log.sl
            log.result_time = _to_utc_dt(first_idx)
            log.trend_correct = False
            return "loss"

    return None


def _to_utc_dt(ts) -> datetime:
    """تبدیل timestamp به datetime UTC aware"""
    if isinstance(ts, pd.Timestamp):
        if ts.tz is None:
            return ts.tz_localize("UTC").to_pydatetime()
        return ts.tz_convert("UTC").to_pydatetime()
    if isinstance(ts, datetime):
        return _ensure_utc(ts)
    return _utcnow()


# ═══════════════════════════════════════════════════════════
# بستن با مهلت
# ═══════════════════════════════════════════════════════════
def _mark_expired(log: SignalLog, current_price: float) -> str:
    """بستن سیگنال با مهلت — آستانه بر اساس fee."""
    log.expired = True
    log.expired_at_price = current_price

    pnl_pct = (current_price - log.price) / log.price * 100
    if log.direction == "short":
        pnl_pct = -pnl_pct

    log.expired_pnl_pct = round(pnl_pct, 3)

    fee_threshold = (log.fee_pct or 0.23) * 1.5
    log.expired_bias = (
        "win"
        if pnl_pct > fee_threshold
        else "loss" if pnl_pct < -fee_threshold else "flat"
    )

    if log.expired_bias == "win":
        log.trend_correct = True
    elif log.expired_bias == "loss":
        log.trend_correct = False
    else:
        log.trend_correct = None

    if log.expired_bias == "win":
        log.result = "win"
    elif log.expired_bias == "loss":
        log.result = "loss"
    else:
        log.result = None

    log.result_time = _utcnow()
    return "expired"


# ═══════════════════════════════════════════════════════════
# اجرای backtest
# ═══════════════════════════════════════════════════════════
def backtest_all(max_checks: int = BACKTEST_MAX_SIGNALS) -> dict:
    """بررسی همه‌ی سیگنال‌های pending."""
    checked = 0
    updated = 0
    errors = 0
    stats = {"win": 0, "loss": 0, "expired": 0}

    with Session(engine) as session:
        stmt = (
            select(SignalLog)
            .where(SignalLog.result.is_(None))
            .where(SignalLog.expired == False)
            .where(SignalLog.tf.in_(BACKTEST_TF_WHITELIST))
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
# compute_stats
# ═══════════════════════════════════════════════════════════
def compute_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict:
    with Session(engine) as session:
        stmt = select(SignalLog)

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

        stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(BACKTEST_MAX_SIGNALS)
        rows = session.exec(stmt).all()

    total = len(rows)
    wins = sum(1 for r in rows if r.result == "win")
    losses = sum(1 for r in rows if r.result == "loss")
    pending = sum(1 for r in rows if not r.result and not r.expired)
    expired = sum(1 for r in rows if r.expired)

    closed = wins + losses
    win_rate = (wins / closed * 100) if closed > 0 else 0.0

    trend_correct = sum(1 for r in rows if r.trend_correct is True)
    trend_wrong = sum(1 for r in rows if r.trend_correct is False)
    trend_total = trend_correct + trend_wrong
    trend_accuracy = (trend_correct / trend_total * 100) if trend_total > 0 else 0.0

    expired_win = sum(1 for r in rows if r.expired_bias == "win")
    expired_loss = sum(1 for r in rows if r.expired_bias == "loss")
    expired_flat = sum(1 for r in rows if r.expired_bias == "flat")

    win_pnls = [
        abs(r.expired_pnl_pct)
        for r in rows
        if r.result == "win" and r.expired_pnl_pct is not None
    ]
    loss_pnls = [
        abs(r.expired_pnl_pct)
        for r in rows
        if r.result == "loss" and r.expired_pnl_pct is not None
    ]
    win_pnls += [
        abs(r.rr_net)
        for r in rows
        if r.result == "win" and r.rr_net and r.expired_pnl_pct is None
    ]
    loss_pnls += [
        abs(r.rr_net)
        for r in rows
        if r.result == "loss" and r.rr_net and r.expired_pnl_pct is None
    ]

    total_win = sum(win_pnls)
    total_loss = sum(loss_pnls)
    profit_factor = (total_win / total_loss) if total_loss > 0 else 0.0

    rr_nets = [r.rr_net for r in rows if r.rr_net is not None]
    avg_rr_net = sum(rr_nets) / len(rr_nets) if rr_nets else 0.0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "pending": pending,
        "expired": expired,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_rr": round(avg_rr_net, 3),
        "avg_rr_net": round(avg_rr_net, 3),
        "expectancy": round((win_rate / 100) * avg_rr_net - (1 - win_rate / 100), 3),
        "trend_correct": trend_correct,
        "trend_wrong": trend_wrong,
        "trend_accuracy": round(trend_accuracy, 2),
        "expired_win": expired_win,
        "expired_loss": expired_loss,
        "expired_flat": expired_flat,
    }


def compute_stats_by_tf(
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict[str, dict]:
    result: dict[str, dict] = {}

    with Session(engine) as session:
        stmt = select(SignalLog)
        if risk_profile:
            stmt = stmt.where(SignalLog.risk_profile == risk_profile)

        if time_filter != "all":
            now = _utcnow()
            days = {"1d": 1, "7d": 7, "30d": 30}.get(time_filter)
            if days:
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=days))

        rows = session.exec(stmt).all()

    by_tf: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_tf.setdefault(r.tf, []).append(r)

    for tf, items in by_tf.items():
        total = len(items)
        wins = sum(1 for r in items if r.result == "win")
        losses = sum(1 for r in items if r.result == "loss")
        pending = sum(1 for r in items if not r.result and not r.expired)
        expired = sum(1 for r in items if r.expired)

        closed = wins + losses
        win_rate = (wins / closed * 100) if closed > 0 else 0.0

        tc = sum(1 for r in items if r.trend_correct is True)
        tw = sum(1 for r in items if r.trend_correct is False)
        trend_total = tc + tw
        trend_acc = (tc / trend_total * 100) if trend_total > 0 else 0.0

        result[tf] = {
            "total": total,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "expired": expired,
            "win_rate": round(win_rate, 2),
            "trend_correct": tc,
            "trend_wrong": tw,
            "trend_total": trend_total,
            "trend_accuracy": round(trend_acc, 2),
        }

    return result


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
        wins = sum(1 for r in items if r.result == "win")
        losses = sum(1 for r in items if r.result == "loss")
        closed = wins + losses
        win_rate = (wins / closed * 100) if closed > 0 else 0.0

        result[profile] = {
            "total": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
        }

    return result


def compute_stats_by_quality(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict[str, dict]:
    with Session(engine) as session:
        stmt = select(SignalLog)

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

        rows = session.exec(stmt).all()

    def _stats(items: list[SignalLog]) -> dict:
        total = len(items)
        wins = sum(1 for r in items if r.result == "win")
        losses = sum(1 for r in items if r.result == "loss")
        pending = sum(1 for r in items if not r.result and not r.expired)
        expired = sum(1 for r in items if r.expired)

        closed = wins + losses
        win_rate = (wins / closed * 100) if closed > 0 else 0.0

        tc = sum(1 for r in items if r.trend_correct is True)
        tw = sum(1 for r in items if r.trend_correct is False)
        trend_total = tc + tw
        trend_acc = (tc / trend_total * 100) if trend_total > 0 else 0.0

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "expired": expired,
            "win_rate": round(win_rate, 2),
            "profit_factor": 0.0,
            "avg_rr": 0.0,
            "avg_rr_net": 0.0,
            "expectancy": 0.0,
            "trend_correct": tc,
            "trend_wrong": tw,
            "trend_accuracy": round(trend_acc, 2),
            "expired_win": sum(1 for r in items if r.expired_bias == "win"),
            "expired_loss": sum(1 for r in items if r.expired_bias == "loss"),
            "expired_flat": sum(1 for r in items if r.expired_bias == "flat"),
        }

    return {
        "all": _stats(rows),
        "strong": _stats([r for r in rows if r.confidence >= 70]),
        "normal": _stats([r for r in rows if 50 <= r.confidence < 70]),
        "weak": _stats([r for r in rows if r.confidence < 50]),
    }
