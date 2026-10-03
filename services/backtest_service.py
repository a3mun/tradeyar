"""
services/backtest_service.py
بررسی خودکار سیگنال‌ها
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from core.contracts import SIGNAL_TIMEOUT, Signal as SigEnum
from services.data_service import fetch_ohlcv

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _strip_tz(dt: datetime) -> datetime:
    """حذف timezone — برای مقایسه با pandas index"""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _check_one(log: SignalLog) -> str | None:
    if log.result is not None:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    timeout = SIGNAL_TIMEOUT.get(log.tf, timedelta(hours=2))
    now = _utcnow()
    entry_ts = (
        log.timestamp
        if log.timestamp.tzinfo
        else log.timestamp.replace(tzinfo=timezone.utc)
    )

    if now > entry_ts + timeout:
        log.expired = True
        log.result = "expired"
        log.result_time = now
        return "expired"

    try:
        df = fetch_ohlcv(log.ticker, log.tf, log.source, use_cache=True)
        if df is None or df.empty:
            return None
    except Exception as e:
        logger.debug(f"[Backtest] {log.ticker}: {e}")
        return None

    # ─── فیلتر کندل‌های بعد از ثبت ───
    entry_naive = _strip_tz(entry_ts)
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df = df[df.index.tz_localize(None) >= entry_naive]
        else:
            df = df[df.index >= entry_naive]
    except Exception:
        pass

    if df.empty:
        return None

    for idx, row in df.iterrows():
        high = float(row.get("high", 0))
        low = float(row.get("low", 0))

        try:
            candle_time = pd.to_datetime(idx)
            if hasattr(candle_time, "to_pydatetime"):
                candle_time = candle_time.to_pydatetime()
            if candle_time.tzinfo is None:
                candle_time = candle_time.replace(tzinfo=timezone.utc)
        except Exception:
            candle_time = now

        if SigEnum.is_long(log.signal):
            if high >= log.tp:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                return "win"
            if low <= log.sl:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                return "loss"
        elif SigEnum.is_short(log.signal):
            if low <= log.tp:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                return "win"
            if high >= log.sl:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                return "loss"

    return None


def backtest_all(max_checks: int = 200) -> dict:
    result = {"checked": 0, "updated": 0, "expired": 0, "win": 0, "loss": 0}

    try:
        with Session(engine) as session:
            stmt = (
                select(SignalLog)
                .where(SignalLog.result.is_(None))
                .order_by(SignalLog.timestamp.asc())
                .limit(max_checks)
            )
            logs = session.exec(stmt).all()

            for log in logs:
                result["checked"] += 1
                outcome = _check_one(log)
                if outcome:
                    result["updated"] += 1
                    if outcome == "expired":
                        result["expired"] += 1
                    elif outcome == "win":
                        result["win"] += 1
                    elif outcome == "loss":
                        result["loss"] += 1
                    session.add(log)

            session.commit()
    except Exception as e:
        logger.error(f"[Backtest] خطا: {e}")

    return result


def compute_stats(tf: str = "", source: str = "", time_filter: str = "all") -> dict:
    stats = {
        "total": 0,
        "wins": 0,
        "losses": 0,
        "pending": 0,
        "expired": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_rr": 0.0,
        "expectancy": 0.0,
    }

    try:
        with Session(engine) as session:
            stmt = select(SignalLog)
            if tf:
                stmt = stmt.where(SignalLog.tf == tf)
            if source:
                stmt = stmt.where(SignalLog.source == source)

            now = _utcnow()
            if time_filter == "7d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
            elif time_filter == "30d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

            rows = session.exec(stmt).all()

            stats["total"] = len(rows)
            stats["wins"] = sum(1 for r in rows if r.result == "win")
            stats["losses"] = sum(1 for r in rows if r.result == "loss")
            stats["pending"] = sum(
                1 for r in rows if r.result is None and not r.expired
            )
            stats["expired"] = sum(1 for r in rows if r.expired)

            closed = stats["wins"] + stats["losses"]
            if closed > 0:
                stats["win_rate"] = round(stats["wins"] / closed * 100, 2)

            gross_win = sum(
                (abs(r.tp - r.price) / r.price)
                for r in rows
                if r.result == "win" and r.tp and r.price
            )
            gross_loss = sum(
                (abs(r.price - r.sl) / r.price)
                for r in rows
                if r.result == "loss" and r.sl and r.price
            )
            if gross_loss > 0:
                stats["profit_factor"] = round(gross_win / gross_loss, 2)
            elif gross_win > 0:
                stats["profit_factor"] = 999.0

            rrs = [r.rr for r in rows if r.rr]
            if rrs:
                stats["avg_rr"] = round(sum(rrs) / len(rrs), 2)

            if closed > 0 and rrs:
                wr = stats["win_rate"] / 100
                stats["expectancy"] = round(wr * stats["avg_rr"] - (1 - wr), 3)
    except Exception as e:
        logger.error(f"[Backtest] stats: {e}")

    return stats
