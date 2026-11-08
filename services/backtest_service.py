"""
services/backtest_service.py
راستی‌آزمایی — موتور اصلی (نسخه ۹.۰ — فاز ۱۴.۷.۱)
============================================================
🔴 تغییرات نسخه ۹.۰:
  ۱. _check_one: timeout از log.timeout_planned_min (پویا)
  ۲. _check_one: محاسبه‌ی tp_hit_level (کدام TP لمس شد)
  ۳. _mark_expired: result_time از آخرین کندل
  ۴. win_rate یکدست در همه‌ی ۵ تابع: (tp_hits + timeout_wins) / closed
  ۵. compute_stats: tp_hit_rate + avg_tp_level + timeout_overshoot_min
  ۶. خواندن tp_levels_json از DB و استفاده در محاسبه‌ی tp_hit_level
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlmodel import Session, select, or_

from api.database import engine
from api.models import SignalLog
from core.contracts import get_signal_timeout
from core.data_fetcher import fetch_history_by_source

logger = logging.getLogger(__name__)

BACKTEST_MAX_SIGNALS = 200


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


def _parse_tp_levels(log: SignalLog) -> dict:
    """tp_levels_json را از DB می‌خواند و به dict تبدیل می‌کند."""
    if not log.tp_levels_json:
        return {}
    try:
        parsed = json.loads(log.tp_levels_json)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except Exception:
        return {}


def _compute_tp_hit_level(
    df_after: pd.DataFrame, log: SignalLog, tp_levels: dict
) -> Optional[int]:
    """
    🆕 فاز ۱۴.۷.۱ — کدام TP لمس شد (1/2/3)؟
    اگر TP1 لمس شد ولی TP2 نه → برمی‌گردونه 1.
    اگر TP2 لمس شد ولی TP3 نه → 2.
    اگر TP3 لمس شد → 3.
    اگر هیچ‌کدام → None.
    """
    if not tp_levels or not isinstance(tp_levels, dict):
        return None
    if df_after.empty:
        return None

    is_long = log.direction == "long"
    highest = None

    for level_num, key in [(1, "tp1"), (2, "tp2"), (3, "tp3")]:
        tp_val = tp_levels.get(key)
        if tp_val is None:
            continue
        try:
            tp_val = float(tp_val)
        except (TypeError, ValueError):
            continue

        if is_long:
            if (df_after["high"] >= tp_val).any():
                highest = level_num
        else:
            if (df_after["low"] <= tp_val).any():
                highest = level_num

    return highest


def _check_one(log: SignalLog) -> Optional[str]:
    if log.result is not None or log.expired:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    entry_ts = _ensure_utc(log.timestamp)

    # 🆕 فاز ۱۴.۷.۱ — timeout پویا
    if log.timeout_planned_min and log.timeout_planned_min > 0:
        timeout_td = timedelta(minutes=log.timeout_planned_min)
    else:
        timeout_td = get_signal_timeout(log.tf, log.market_type)

    timeout_end = entry_ts + timeout_td
    timeout_min = int(timeout_td.total_seconds() / 60)
    elapsed_min = (_utcnow() - entry_ts).total_seconds() / 60

    tf_min_map = {
        "۱ دقیقه": 1,
        "۵ دقیقه": 5,
        "۱۵ دقیقه": 15,
        "۳۰ دقیقه": 30,
        "۱ ساعت": 60,
        "روزانه": 1440,
    }
    tf_min = tf_min_map.get(log.tf, 5)
    bars_needed = max(int(elapsed_min / tf_min) + 10, 50)

    df = fetch_ohlcv(log.ticker, log.source, log.tf, limit=bars_needed)

    # نبود داده — اگه timeout شده، expired ثبت کن
    if df is None or len(df) == 0 or not isinstance(df.index, pd.DatetimeIndex):
        if elapsed_min >= timeout_min:
            logger.info(
                f"[Backtest] {log.ticker}/{log.tf} timeout بدون داده — expired با price"
            )
            return _mark_expired(log, log.price, None)
        return None

    df_idx_utc = (
        df.index.tz_localize("UTC")
        if df.index.tz is None
        else df.index.tz_convert("UTC")
    )

    # محدود کردن به بازه اعتبار
    df_after = df[(df_idx_utc >= entry_ts) & (df_idx_utc <= timeout_end)]

    if df_after.empty:
        if elapsed_min >= timeout_min:
            return _mark_expired(log, log.price, None)
        return None

    # 🆕 محاسبه‌ی tp_hit_level از tp_levels_json
    tp_levels = _parse_tp_levels(log)
    tp_hit_level = _compute_tp_hit_level(df_after, log, tp_levels)
    log.tp_hit_level = tp_hit_level

    is_long = log.direction == "long"

    if is_long:
        win_mask = df_after["high"] >= log.tp
        loss_mask = df_after["low"] <= log.sl
    else:
        win_mask = df_after["low"] <= log.tp
        loss_mask = df_after["high"] >= log.sl

    tp_time = df_after[win_mask].index[0] if win_mask.any() else None
    sl_time = df_after[loss_mask].index[0] if loss_mask.any() else None

    # SL-first: اگر هم‌زمان یا SL زودتر، loss (بدبینانه)
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

    if elapsed_min >= timeout_min:
        # قیمت خروج = آخرین کندل معتبر
        current_price = float(df_after["close"].iloc[-1])
        last_time = df_after.index[-1]
        return _mark_expired(log, current_price, _to_utc_dt(last_time))

    return None


def _mark_expired(
    log: SignalLog, current_price: float, result_time: Optional[datetime] = None
) -> str:
    log.expired = True
    log.exit_reason = "timeout"
    log.expired_at_price = current_price
    log.exit_price = current_price

    pnl_pct = (current_price - log.price) / log.price * 100
    if log.direction == "short":
        pnl_pct = -pnl_pct

    log.expired_pnl_pct = round(pnl_pct, 3)

    if pnl_pct > 0:
        log.expired_bias = "win"
        log.result = "win"
    elif pnl_pct < 0:
        log.expired_bias = "loss"
        log.result = "loss"
    else:
        log.expired_bias = "flat"
        log.result = None

    log.result_time = result_time or _utcnow()
    return "expired"


def backtest_all(max_checks: int = BACKTEST_MAX_SIGNALS) -> dict:
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
    strategy: str = "",
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
    if strategy:
        stmt = stmt.where(SignalLog.strategy == strategy)
    if time_filter != "all":
        now = _utcnow()
        days = {"1d": 1, "7d": 7, "30d": 30}.get(time_filter)
        if days:
            stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=days))
    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    return session.exec(stmt).all()


def _get_r_value(log: SignalLog) -> float:
    risk_pct = (
        abs(log.price - log.sl) / log.price * 100 if log.price and log.sl else 1.0
    )
    if log.result == "win":
        if log.exit_reason == "tp_hit":
            return log.rr or 1.0
        elif log.exit_reason == "timeout" and log.expired_pnl_pct is not None:
            return log.expired_pnl_pct / risk_pct if risk_pct > 0 else 0.0
    elif log.result == "loss":
        if log.exit_reason == "sl_hit":
            return -1.0
        elif log.exit_reason == "timeout" and log.expired_pnl_pct is not None:
            return log.expired_pnl_pct / risk_pct if risk_pct > 0 else 0.0
    return 0.0


def _compute_core_stats(rows: list[SignalLog]) -> dict:
    """
    🆕 فاز ۱۴.۷.۱ — محاسبه‌ی آمار پایه، مشترک بین همه‌ی ۵ تابع.
    win_rate یکدست: (tp_hits + timeout_wins) / closed
    """
    total = len(rows)
    expired_count = sum(1 for r in rows if r.expired)

    tp_hits = sum(1 for r in rows if r.exit_reason == "tp_hit")
    sl_hits = sum(1 for r in rows if r.exit_reason == "sl_hit")
    timeout_wins = sum(
        1 for r in rows if r.exit_reason == "timeout" and r.expired_bias == "win"
    )
    timeout_losses = sum(
        1 for r in rows if r.exit_reason == "timeout" and r.expired_bias == "loss"
    )
    timeout_flats = sum(
        1 for r in rows if r.exit_reason == "timeout" and r.expired_bias == "flat"
    )

    closed_real = tp_hits + sl_hits + timeout_wins + timeout_losses
    # 🔴 یکدست: WR = (TP + Timeout Win) / Closed
    win_rate = (
        ((tp_hits + timeout_wins) / closed_real * 100) if closed_real > 0 else 0.0
    )
    tp_hit_rate = (tp_hits / closed_real * 100) if closed_real > 0 else 0.0
    direction_acc = (
        ((tp_hits + timeout_wins) / closed_real * 100) if closed_real > 0 else 0.0
    )

    # 🆕 میانگین tp_hit_level (فقط بین اون‌هایی که TP لمس شد)
    tp_level_values = [r.tp_hit_level for r in rows if r.tp_hit_level]
    avg_tp_level = (
        round(sum(tp_level_values) / len(tp_level_values), 2)
        if tp_level_values
        else 0.0
    )

    # trend accuracy
    trend_correct, trend_wrong = 0, 0
    for r in rows:
        if r.result not in ("win", "loss"):
            continue
        pred = r.trend_predicted_at_entry
        if not pred or pred == "flat":
            continue
        if pred == "bull":
            if r.direction == "long" and r.result == "win":
                trend_correct += 1
            elif r.direction == "long" and r.result == "loss":
                trend_wrong += 1
            elif r.direction == "short":
                trend_wrong += 1
        elif pred == "bear":
            if r.direction == "short" and r.result == "win":
                trend_correct += 1
            elif r.direction == "short" and r.result == "loss":
                trend_wrong += 1
            elif r.direction == "long":
                trend_wrong += 1
    trend_total = trend_correct + trend_wrong
    trend_acc = (trend_correct / trend_total * 100) if trend_total > 0 else 0.0

    return {
        "total": total,
        "expired": expired_count,
        "tp_hits": tp_hits,
        "sl_hits": sl_hits,
        "timeout_wins": timeout_wins,
        "timeout_losses": timeout_losses,
        "timeout_flats": timeout_flats,
        "closed_real": closed_real,
        "win_rate": round(win_rate, 2),
        "tp_hit_rate": round(tp_hit_rate, 2),
        "direction_accuracy": round(direction_acc, 2),
        "avg_tp_level": avg_tp_level,
        "trend_correct": trend_correct,
        "trend_wrong": trend_wrong,
        "trend_accuracy": round(trend_acc, 2),
    }


def compute_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
    strategy: str = "",
) -> dict:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session, tf, source, time_filter, risk_profile, limit, strategy
        )

    core = _compute_core_stats(rows)

    # profit factor / expectancy (نیاز به R-values)
    r_values = [_get_r_value(r) for r in rows]
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
    p_win = core["win_rate"] / 100
    p_loss = 1 - p_win
    expectancy = (
        ((p_win * avg_win) - (p_loss * avg_loss))
        if (avg_win > 0 or avg_loss > 0)
        else 0.0
    )

    return {
        "total": core["total"],
        "tp_hits": core["tp_hits"],
        "sl_hits": core["sl_hits"],
        "timeout_wins": core["timeout_wins"],
        "timeout_losses": core["timeout_losses"],
        "timeout_flats": core["timeout_flats"],
        "pending": 0,
        "expired": core["expired"],
        "win_rate": core["win_rate"],
        "tp_hit_rate": core["tp_hit_rate"],
        "direction_accuracy": core["direction_accuracy"],
        "avg_tp_level": core["avg_tp_level"],  # 🆕
        "profit_factor": round(profit_factor, 3),
        "avg_rr_net": round(avg_rr_net, 3),
        "expectancy": round(expectancy, 3),
        "trend_correct": core["trend_correct"],
        "trend_wrong": core["trend_wrong"],
        "trend_accuracy": core["trend_accuracy"],
    }


def compute_stats_by_tf(
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
    strategy: str = "",
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    result: dict[str, dict] = {}
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session, "", "", time_filter, risk_profile, limit, strategy
        )
    by_tf: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_tf.setdefault(r.tf, []).append(r)

    for tf, items in by_tf.items():
        core = _compute_core_stats(items)
        result[tf] = {
            "total": core["total"],
            "wins": core["tp_hits"],
            "losses": core["sl_hits"],
            "win_rate": core["win_rate"],
            "direction_accuracy": core["direction_accuracy"],
            "trend_accuracy": core["trend_accuracy"],
            "avg_tp_level": core["avg_tp_level"],
        }
    return result


def compute_stats_by_profile(
    time_filter: str = "all",
    strategy: str = "",
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with Session(engine) as session:
        stmt = select(SignalLog)
        if strategy:
            stmt = stmt.where(SignalLog.strategy == strategy)
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
        core = _compute_core_stats(items)
        result[profile] = {
            "total": core["total"],
            "wins": core["tp_hits"],
            "losses": core["sl_hits"],
            "timeout_wins": core["timeout_wins"],
            "timeout_losses": core["timeout_losses"],
            "win_rate": core["win_rate"],
            "direction_accuracy": core["direction_accuracy"],
        }
    return result


def compute_stats_by_regime(
    time_filter: str = "all",
    risk_profile: str = "",
    strategy: str = "",
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session,
            "",
            "",
            time_filter,
            risk_profile,
            BACKTEST_MAX_SIGNALS,
            strategy,
        )
    by_regime: dict[str, list[SignalLog]] = {}
    for r in rows:
        by_regime.setdefault(r.regime or "unknown", []).append(r)

    for regime, items in by_regime.items():
        core = _compute_core_stats(items)
        result[regime] = {
            "total": core["total"],
            "tp_hits": core["tp_hits"],
            "sl_hits": core["sl_hits"],
            "timeout_wins": core["timeout_wins"],
            "timeout_losses": core["timeout_losses"],
            "win_rate": core["win_rate"],
            "direction_accuracy": core["direction_accuracy"],
        }
    return result


def compute_stats_by_quality(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
    strategy: str = "",
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session, tf, source, time_filter, risk_profile, limit, strategy
        )

    def _stats(items: list[SignalLog]) -> dict:
        core = _compute_core_stats(items)
        return {
            "total": core["total"],
            "wins": core["tp_hits"],
            "losses": core["sl_hits"],
            "win_rate": core["win_rate"],
            "direction_accuracy": core["direction_accuracy"],
        }

    return {
        "all": _stats(rows),
        "strong": _stats([r for r in rows if r.confidence >= 75]),
        "normal": _stats([r for r in rows if 60 <= r.confidence < 75]),
        "weak": _stats([r for r in rows if 45 <= r.confidence < 60]),
    }
