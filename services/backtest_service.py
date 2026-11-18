"""
services/backtest_service.py
راستی‌آزمایی — موتور اصلی (نسخه ۱۱.۰ — فاز ۱۶.۹)
============================================================
🔴 تغییرات نسخه ۱۱.۰:
  ۱. تفکیک کامل «برد واقعی (TP)» از «جهت درست (حتی ۱ تیک)»
  ۲. رفع باگ timeout (دیگر result=win نمی‌شود مگر TP1 زده شود)
  ۳. افزودن compute_stats_by_tf برای گزارش تفکیکی تایم‌فریم‌ها
  ۴. بازنویسی منطق _check_one برای اولویت‌بندی صحیح TP و SL
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlmodel import Session, select, or_, func

from api.database import engine
from api.models import SignalLog, SiteStatsOverride
from core.contracts import get_signal_timeout
from core.data_fetcher import fetch_history_by_source

logger = logging.getLogger(__name__)

BACKTEST_MAX_SIGNALS = 300


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
    if not log.tp_levels_json:
        return {}
    try:
        parsed = json.loads(log.tp_levels_json)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _compute_tp_hit_level(
    df_after: pd.DataFrame, log: SignalLog, tp_levels: dict
) -> Optional[int]:
    if df_after.empty:
        return None
    is_long = log.direction == "long"
    highest = None
    if not tp_levels:
        if log.tp:
            try:
                tp_val = float(log.tp)
            except (TypeError, ValueError):
                return None
            if is_long:
                if (df_after["high"] >= tp_val).any():
                    return 3
            else:
                if (df_after["low"] <= tp_val).any():
                    return 3
        return None
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
    if df is None or len(df) == 0 or not isinstance(df.index, pd.DatetimeIndex):
        if elapsed_min >= timeout_min:
            return _mark_expired(log, log.price, None)
        return None

    df_idx_utc = (
        df.index.tz_localize("UTC")
        if df.index.tz is None
        else df.index.tz_convert("UTC")
    )
    df_after = df[(df_idx_utc >= entry_ts) & (df_idx_utc <= timeout_end)]
    if df_after.empty:
        if elapsed_min >= timeout_min:
            return _mark_expired(log, log.price, None)
        return None

    tp_levels = _parse_tp_levels(log)
    tp_hit_level = _compute_tp_hit_level(df_after, log, tp_levels)
    log.tp_hit_level = tp_hit_level

    is_long = log.direction == "long"

    # پیدا کردن زمان برخورد با TP1، TP2، TP3 و SL
    tp1_time = None
    if tp_levels and "tp1" in tp_levels:
        tp1_val = float(tp_levels["tp1"])
        mask_tp1 = (
            df_after["high"] >= tp1_val if is_long else df_after["low"] <= tp1_val
        )
        tp1_time = df_after[mask_tp1].index[0] if mask_tp1.any() else None

    tp_time = None
    win_mask = df_after["high"] >= log.tp if is_long else df_after["low"] <= log.tp
    if win_mask.any():
        tp_time = df_after[win_mask].index[0]

    loss_mask = df_after["low"] <= log.sl if is_long else df_after["high"] >= log.sl
    sl_time = df_after[loss_mask].index[0] if loss_mask.any() else None

    # منطق خروج:
    # 1. اگر TP اصلی زده شد (چه قبل چه بعد از SL): win
    # 2. اگر SL زده شد ولی TP1 زده شده بود: loss (ولی tp_hit_level ثبت می‌شود)
    # 3. اگر SL زده شد و TP1 هم نزده بود: loss
    # 4. اگر فقط TP1 زده شد (نه TP اصلی): win (چون TP1 = برد واقعی)

    if tp_time and (not sl_time or tp_time < sl_time):
        log.result = "win"
        log.exit_reason = "tp_hit"
        log.exit_price = log.tp
        log.result_time = _to_utc_dt(tp_time)
        if log.tp_hit_level is None:
            log.tp_hit_level = 3
        return "win"

    if sl_time:
        log.result = "loss"
        log.exit_reason = "sl_hit"
        log.exit_price = log.sl
        log.result_time = _to_utc_dt(sl_time)
        return "loss"

    # اگر فقط TP1 زده شده (بدون TP اصلی و بدون SL)
    if tp1_time:
        log.result = "win"
        log.exit_reason = "tp1_hit"
        log.exit_price = float(tp_levels["tp1"])
        log.result_time = _to_utc_dt(tp1_time)
        log.tp_hit_level = 1
        return "win"

    if elapsed_min >= timeout_min:
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

    if log.price == 0:
        log.expired_pnl_pct = 0.0
        log.expired_bias = "flat"
        log.result = None
        log.result_time = result_time or _utcnow()
        return "expired"

    pnl_pct = (current_price - log.price) / log.price * 100
    if log.direction == "short":
        pnl_pct = -pnl_pct
    log.expired_pnl_pct = round(pnl_pct, 3)

    # 🔴 فاز ۱۶.۹: نتیجه timeout فقط در expired_bias ست می‌شود
    # result دست نمی‌خورد مگر اینکه در آینده TP1 زده شده باشد
    if pnl_pct > 0:
        log.expired_bias = "win"
    elif pnl_pct < 0:
        log.expired_bias = "loss"
    else:
        log.expired_bias = "flat"
    # result را تغییر نمی‌دهیم؛ فقط اگر TP1 زده شده بود آن را در _check_one ست می‌کنیم
    log.result_time = result_time or _utcnow()
    return "expired"


def backtest_all(
    max_checks: int = BACKTEST_MAX_SIGNALS, only_due: bool = False
) -> dict:
    checked, updated, errors = 0, 0, 0
    stats = {"win": 0, "loss": 0, "expired": 0}
    with Session(engine) as session:
        stmt = (
            select(SignalLog)
            .where(SignalLog.result.is_(None))
            .where(SignalLog.expired == False)
        )
        if only_due:
            now = _utcnow()
            pending = session.exec(stmt).all()
            due_pending = []
            for log in pending:
                if log.timeout_planned_min and log.timeout_planned_min > 0:
                    timeout_td = timedelta(minutes=log.timeout_planned_min)
                else:
                    timeout_td = get_signal_timeout(log.tf, log.market_type)
                timeout_end = _ensure_utc(log.timestamp) + timeout_td
                if now >= timeout_end:
                    due_pending.append(log)
            pending = due_pending[:max_checks]
        else:
            stmt = stmt.order_by(
                SignalLog.timeout_planned_min.asc().nulls_last(),
                SignalLog.timestamp.desc(),
            ).limit(max_checks)
            pending = session.exec(stmt).all()
        logger.info(f"[Backtest] {len(pending)} سیگنال pending (only_due={only_due})")
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
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
    strategy: str = "",
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
    if strategy:
        stmt = stmt.where(SignalLog.strategy == strategy)
    if time_filter != "all":
        now = _utcnow()
        days = {"1d": 1, "7d": 7, "30d": 30}.get(time_filter)
        if days:
            stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=days))
    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    return session.exec(stmt).all()


def _compute_core_stats(rows: list[SignalLog]) -> dict:
    total = len(rows)
    expired_count = sum(1 for r in rows if r.expired)

    # 🔴 برد واقعی: فقط TP کامل یا TP1 (با تغییر جدید)
    tp_full = sum(1 for r in rows if r.exit_reason == "tp_hit")
    tp1_hits = sum(1 for r in rows if r.exit_reason == "tp1_hit")
    sl_hits = sum(1 for r in rows if r.exit_reason == "sl_hit")

    timeout_wins = sum(1 for r in rows if r.expired and r.expired_bias == "win")
    timeout_losses = sum(1 for r in rows if r.expired and r.expired_bias == "loss")
    timeout_flats = sum(1 for r in rows if r.expired and r.expired_bias == "flat")

    closed_real = total  # همه سیگنال‌های بسته شده

    # متریک‌های نهایی:
    # - win_rate: نرخ رسیدن به TP کامل یا TP1 (برد واقعی)
    # - direction_accuracy: درصد سیگنال‌هایی که حتی ۱ تیک به سمت درست رفتن
    # - loss_rate: نرخ برخورد با SL

    real_wins = tp_full + tp1_hits
    direction_correct = tp_full + tp1_hits + timeout_wins

    win_rate = (real_wins / closed_real * 100) if closed_real > 0 else 0.0
    loss_rate = (sl_hits / closed_real * 100) if closed_real > 0 else 0.0
    direction_acc = (direction_correct / closed_real * 100) if closed_real > 0 else 0.0

    trend_correct, trend_wrong = 0, 0
    for r in rows:
        if r.expired and r.expired_bias == "flat":
            continue
        if not r.trend_predicted_at_entry or r.trend_predicted_at_entry == "flat":
            continue

        if r.expired and r.expired_bias == "win":
            trend_correct += 1
        elif r.expired and r.expired_bias == "loss":
            trend_wrong += 1
        elif r.result == "win":
            trend_correct += 1
        elif r.result == "loss":
            trend_wrong += 1

    trend_total = trend_correct + trend_wrong
    trend_acc = (trend_correct / trend_total * 100) if trend_total > 0 else 0.0

    return {
        "total": total,
        "expired": expired_count,
        "tp_hits": tp_full + tp1_hits,  # برد واقعی
        "sl_hits": sl_hits,
        "timeout_wins": timeout_wins,
        "timeout_losses": timeout_losses,
        "timeout_flats": timeout_flats,
        "closed_real": closed_real,
        "win_rate": round(win_rate, 2),
        "loss_rate": round(loss_rate, 2),
        "direction_accuracy": round(direction_acc, 2),
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
        pending_stmt = (
            select(func.count(SignalLog.id))
            .where(SignalLog.result.is_(None))
            .where(SignalLog.expired == False)
        )
        if strategy:
            pending_stmt = pending_stmt.where(SignalLog.strategy == strategy)
        if tf:
            pending_stmt = pending_stmt.where(SignalLog.tf == tf)
        if source:
            pending_stmt = pending_stmt.where(SignalLog.source == source)
        if risk_profile:
            pending_stmt = pending_stmt.where(SignalLog.risk_profile == risk_profile)
        pending_count_val = session.exec(pending_stmt).one()
    core = _compute_core_stats(rows)
    return {**core, "pending": pending_count_val}


def compute_stats_by_strategy(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(session, tf, source, time_filter, risk_profile, limit)
    by_strategy: dict[str, list[SignalLog]] = {}
    for r in rows:
        key = r.strategy or "swing"
        by_strategy.setdefault(key, []).append(r)
    result = {}
    for strat, items in by_strategy.items():
        core = _compute_core_stats(items)
        result[strat] = {
            "total": core["total"],
            "tp_hits": core["tp_hits"],
            "sl_hits": core["sl_hits"],
            "timeout_wins": core["timeout_wins"],
            "timeout_losses": core["timeout_losses"],
            "win_rate": core["win_rate"],
            "loss_rate": core["loss_rate"],
            "direction_accuracy": core["direction_accuracy"],
            "trend_correct": core["trend_correct"],
            "trend_wrong": core["trend_wrong"],
        }
    return result


def compute_stats_by_tf(
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
    limit: int = BACKTEST_MAX_SIGNALS,
    strategy: str = "",
) -> dict[str, dict]:
    limit = max(50, min(limit, 500))
    with Session(engine) as session:
        rows = _fetch_closed_rows(
            session, "", source, time_filter, risk_profile, limit, strategy
        )
    by_tf: dict[str, list[SignalLog]] = {}
    for r in rows:
        key = r.tf or "۵ دقیقه"
        by_tf.setdefault(key, []).append(r)
    result = {}
    for tf_name, items in by_tf.items():
        core = _compute_core_stats(items)
        result[tf_name] = {
            "total": core["total"],
            "tp_hits": core["tp_hits"],
            "sl_hits": core["sl_hits"],
            "timeout_wins": core["timeout_wins"],
            "timeout_losses": core["timeout_losses"],
            "win_rate": core["win_rate"],
            "loss_rate": core["loss_rate"],
            "direction_accuracy": core["direction_accuracy"],
        }
    return result


def get_site_stats() -> dict:
    """آمار نمایشی سایت — با override ادمین (۱۰۰ سیگنال اخیر)."""
    with Session(engine) as session:
        rows = _fetch_closed_rows(session, "", "", "all", "", 100)
    core = _compute_core_stats(rows)
    real_total_signals = core["total"]

    by_strategy = {"scalp": [], "swing": [], "position": []}
    for r in rows:
        strat = r.strategy or "swing"
        if strat in by_strategy:
            by_strategy[strat].append(r)

    stats_by_strat = {}
    for strat, strat_rows in by_strategy.items():
        strat_core = _compute_core_stats(strat_rows)
        stats_by_strat[strat] = {
            "real_win_rate": strat_core["win_rate"],
            "real_direction_accuracy": strat_core["direction_accuracy"],
            "real_loss_rate": strat_core["loss_rate"],
            "total": strat_core["total"],
            "win_rate": strat_core["win_rate"],
            "loss_rate": strat_core["loss_rate"],
            "direction_accuracy": strat_core["direction_accuracy"],
            "has_override": {"win_rate": False, "direction_accuracy": False},
        }

    with Session(engine) as session:
        overrides = session.exec(select(SiteStatsOverride)).all()
        override_dict = {o.key: o.value for o in overrides}

    display_win_rate = override_dict.get("win_rate", core["win_rate"])
    display_direction_acc = override_dict.get(
        "direction_accuracy", core["direction_accuracy"]
    )
    if "win_rate" in override_dict:
        display_loss_rate = 100 - display_win_rate
    else:
        display_loss_rate = core["loss_rate"]

    display_total_signals = int(override_dict.get("total_signals", real_total_signals))

    for strat in stats_by_strat:
        if f"win_rate_{strat}" in override_dict:
            stats_by_strat[strat]["win_rate"] = override_dict[f"win_rate_{strat}"]
            stats_by_strat[strat]["loss_rate"] = (
                100 - override_dict[f"win_rate_{strat}"]
            )
            stats_by_strat[strat]["has_override"]["win_rate"] = True
        if f"direction_accuracy_{strat}" in override_dict:
            stats_by_strat[strat]["direction_accuracy"] = override_dict[
                f"direction_accuracy_{strat}"
            ]
            stats_by_strat[strat]["has_override"]["direction_accuracy"] = True

    return {
        "total_signals": display_total_signals,
        "win_rate": round(display_win_rate, 2),
        "loss_rate": round(display_loss_rate, 2),
        "direction_accuracy": round(display_direction_acc, 2),
        "real_win_rate": round(core["win_rate"], 2),
        "real_loss_rate": round(core["loss_rate"], 2),
        "real_direction_accuracy": round(core["direction_accuracy"], 2),
        "real_total_signals": real_total_signals,
        "has_override": {
            "win_rate": "win_rate" in override_dict,
            "direction_accuracy": "direction_accuracy" in override_dict,
            "total_signals": "total_signals" in override_dict,
        },
        "by_strategy": stats_by_strat,
    }
