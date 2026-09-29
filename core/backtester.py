"""
core/backtester.py
راستی‌آزمایی سیگنال‌ها — نسخه ۵.۱ (فاز ۵)
============================================================
تغییرات نسخه ۵.۱:
  - backtest_all حالا همیشه اجرا می‌شه (نه یک بار)
  - expire خودکار با چک زمان دقیق
  - اضافه شدن last_check_time به لاگ
  - بهبود پیام‌های شفاف
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from .contracts import (
    SIGNAL_TIMEOUT,
    AppDefaults,
    Signal as SigEnum,
)
from .data_fetcher import fetch_history_by_source
from .utils import safe_num

SIGNAL_FILE = Path("data/signals_log.json")


# ═══════════════════════════════════════════════════════════
# بارگذاری / ذخیره
# ═══════════════════════════════════════════════════════════
def load_signal_log() -> list:
    if not SIGNAL_FILE.exists():
        return []
    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Backtester] load: {e}")
        return []


def _save_signal_log(log: list) -> None:
    try:
        SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[Backtester] save: {e}")


def clear_log() -> None:
    if SIGNAL_FILE.exists():
        try:
            SIGNAL_FILE.unlink()
            print("[Backtester] لاگ پاک شد")
        except Exception as e:
            print(f"[Backtester] clear: {e}")


reset_signal_log = clear_log


# ═══════════════════════════════════════════════════════════
# ثبت سیگنال
# ═══════════════════════════════════════════════════════════
def record_signal(
    ticker: str,
    name: str,
    signal: str,
    price: float,
    tf_name: str,
    sl_tp: Optional[dict] = None,
    market_type: str = "spot",
    source: str = "global",
) -> None:
    """ثبت سیگنال جدید (قبول «ضعیف» هم)"""
    if not SigEnum.is_directional(signal):
        return
    if not price or price <= 0:
        return

    log = load_signal_log()
    now = datetime.now()

    # جلوگیری از تکرار در ۲۴ ساعت
    for entry in reversed(log):
        try:
            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
            if (now - entry_time).total_seconds() < 24 * 3600:
                if (
                    entry.get("ticker") == ticker
                    and entry.get("tf") == tf_name
                    and entry.get("signal") == signal
                ):
                    return
        except Exception:
            continue

    entry = {
        "timestamp": now.isoformat(),
        "ticker": ticker,
        "name": name,
        "signal": signal,
        "price": float(price),
        "tf": tf_name,
        "market_type": market_type,
        "source": source,
        "result": None,
        "result_time": None,
    }

    if sl_tp:
        entry["sl"] = safe_num(sl_tp.get("sl"))
        entry["tp"] = safe_num(sl_tp.get("tp"))
        entry["sl_tp_type"] = sl_tp.get("type", "")

    log.append(entry)
    if len(log) > AppDefaults.MAX_SIGNAL_LOG:
        log = log[-AppDefaults.MAX_SIGNAL_LOG :]

    _save_signal_log(log)


# ═══════════════════════════════════════════════════════════
# بررسی سیگنال
# ═══════════════════════════════════════════════════════════
def _check_signal_with_df(entry: dict, df: pd.DataFrame) -> dict:
    """
    بررسی سیگنال با df آماده (به جای fetch مجدد).

    df از قبل گرفته شده و برای چند سیگنال قابل استفاده‌ست.
    """
    if entry.get("result") is not None:
        return entry

    signal = entry.get("signal")
    entry_price = safe_num(entry.get("price"))
    entry_time_str = entry.get("timestamp")
    tf_name = entry.get("tf")

    sl = safe_num(entry.get("sl"))
    tp = safe_num(entry.get("tp"))

    if not signal or not entry_price or not sl or not tp:
        return entry
    if not entry_time_str:
        return entry

    try:
        entry_time = datetime.fromisoformat(entry_time_str)
    except Exception:
        return entry

    now = datetime.now()
    timeout = SIGNAL_TIMEOUT.get(tf_name, timedelta(hours=2))
    expires_at = entry_time + timeout

    # ═══ چک انقضا ═══
    if now > expires_at:
        entry["result"] = "expired"
        entry["result_time"] = now.isoformat()
        entry["exit_price"] = None
        entry["expired"] = True
        return entry

    # ═══ فیلتر کندل‌های بعد از entry ═══
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df_filtered = df[df.index.tz_localize(None) >= entry_time]
        else:
            df_filtered = df[df.index >= entry_time]
    except Exception:
        df_filtered = df

    if df_filtered.empty:
        return entry

    # ═══ بررسی کندل به کندل ═══
    for idx, row in df_filtered.iterrows():
        high = safe_num(row.get("high"))
        low = safe_num(row.get("low"))

        try:
            candle_time = pd.to_datetime(idx)
            if hasattr(candle_time, "to_pydatetime"):
                candle_time = candle_time.to_pydatetime()
            result_time_iso = candle_time.isoformat()
        except Exception:
            result_time_iso = now.isoformat()

        if SigEnum.is_long(signal):
            if high >= tp:
                entry["result"] = True
                entry["result_time"] = result_time_iso
                entry["exit_price"] = tp
                return entry
            if low <= sl:
                entry["result"] = False
                entry["result_time"] = result_time_iso
                entry["exit_price"] = sl
                return entry
        elif SigEnum.is_short(signal):
            if low <= tp:
                entry["result"] = True
                entry["result_time"] = result_time_iso
                entry["exit_price"] = tp
                return entry
            if high >= sl:
                entry["result"] = False
                entry["result_time"] = result_time_iso
                entry["exit_price"] = sl
                return entry

    return entry


def _check_signal_simple(entry: dict) -> dict:
    """
    بررسی سیگنال بدون batch — خودش dата رو می‌گیره.
    برای fallback اگه batch کار نکرد.
    """
    if entry.get("result") is not None:
        return entry

    ticker = entry.get("ticker")
    tf_name = entry.get("tf")
    signal = entry.get("signal")
    entry_price = safe_num(entry.get("price"))
    entry_time_str = entry.get("timestamp")
    source = entry.get("source", "nobitex")

    sl = safe_num(entry.get("sl"))
    tp = safe_num(entry.get("tp"))

    if not ticker or not signal or not entry_price or not sl or not tp:
        return entry
    if not entry_time_str:
        return entry

    from .contracts import TIMEFRAMES

    interval, period = "1h", "3mo"
    for iv, p, n in TIMEFRAMES:
        if n == tf_name:
            interval, period = iv, p
            break

    try:
        entry_time = datetime.fromisoformat(entry_time_str)
    except Exception:
        return entry

    now = datetime.now()
    timeout = SIGNAL_TIMEOUT.get(tf_name, timedelta(hours=2))
    expires_at = entry_time + timeout

    # ═══ چک انقضا ═══
    if now > expires_at:
        entry["result"] = "expired"
        entry["result_time"] = now.isoformat()
        entry["exit_price"] = None
        entry["expired"] = True
        return entry

    # ═══ fetch دیتا ═══
    try:
        df = fetch_history_by_source(ticker, interval, period, source)
        if df is None or df.empty:
            return entry
    except Exception:
        return entry

    # ═══ فیلتر کندل‌های بعد از entry ═══
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df = df[df.index.tz_localize(None) >= entry_time]
        else:
            df = df[df.index >= entry_time]
    except Exception:
        pass

    if df.empty:
        return entry

    # ═══ بررسی کندل به کندل ═══
    for idx, row in df.iterrows():
        high = safe_num(row.get("high"))
        low = safe_num(row.get("low"))

        try:
            candle_time = pd.to_datetime(idx)
            if hasattr(candle_time, "to_pydatetime"):
                candle_time = candle_time.to_pydatetime()
            result_time_iso = candle_time.isoformat()
        except Exception:
            result_time_iso = now.isoformat()

        if SigEnum.is_long(signal):
            if high >= tp:
                entry["result"] = True
                entry["result_time"] = result_time_iso
                entry["exit_price"] = tp
                return entry
            if low <= sl:
                entry["result"] = False
                entry["result_time"] = result_time_iso
                entry["exit_price"] = sl
                return entry
        elif SigEnum.is_short(signal):
            if low <= tp:
                entry["result"] = True
                entry["result_time"] = result_time_iso
                entry["exit_price"] = tp
                return entry
            if high >= sl:
                entry["result"] = False
                entry["result_time"] = result_time_iso
                entry["exit_price"] = sl
                return entry

    return entry


# ═══════════════════════════════════════════════════════════
# Backtest همه
# ═══════════════════════════════════════════════════════════
def backtest_all(max_checks: int = 200) -> dict:
    """
    بررسی همه سیگنال‌های در انتظار.

    بررسی همه pending ها (چون تعدادشون کمه).
    """
    log = load_signal_log()
    if not log:
        return {"checked": 0, "updated": 0, "expired": 0, "win": 0, "loss": 0}

    updated = 0
    expired = 0
    win = 0
    loss = 0
    checked = 0

    # اول قدیمی‌ترها (که زودتر expire می‌شن)
    pending_indexes = sorted(
        [i for i, e in enumerate(log) if e.get("result") is None],
        key=lambda i: log[i].get("timestamp", ""),
    )[:max_checks]

    for i in pending_indexes:
        checked += 1
        entry = log[i]
        new_entry = _check_signal_simple(entry)
        new_result = new_entry.get("result")

        if new_result is not None:
            log[i] = new_entry
            updated += 1
            if new_result == "expired":
                expired += 1
            elif new_result is True:
                win += 1
            elif new_result is False:
                loss += 1

    if updated:
        _save_signal_log(log)

    return {
        "checked": checked,
        "updated": updated,
        "expired": expired,
        "win": win,
        "loss": loss,
    }


# ═══════════════════════════════════════════════════════════
# آمار
# ═══════════════════════════════════════════════════════════
def compute_stats(log: Optional[list] = None) -> dict:
    if log is None:
        log = load_signal_log()

    stats = {
        "total": 0,
        "win": 0,
        "loss": 0,
        "pending": 0,
        "expired": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "max_dd": 0.0,
        "expectancy": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "by_tf": {},
        "by_symbol": {},
    }

    if not log:
        return stats

    stats["total"] = len(log)
    total_win_pct = 0.0
    total_loss_pct = 0.0

    for entry in log:
        result = entry.get("result")
        tf = entry.get("tf", "?")
        ticker = entry.get("ticker", "?")

        if tf not in stats["by_tf"]:
            stats["by_tf"][tf] = {
                "win": 0,
                "loss": 0,
                "pending": 0,
                "expired": 0,
                "win_rate": 0.0,
            }
        if ticker not in stats["by_symbol"]:
            stats["by_symbol"][ticker] = {
                "win": 0,
                "loss": 0,
                "pending": 0,
                "expired": 0,
                "win_rate": 0.0,
            }

        if result is True:
            stats["win"] += 1
            stats["by_tf"][tf]["win"] += 1
            stats["by_symbol"][ticker]["win"] += 1
            price = safe_num(entry.get("price"))
            tp = safe_num(entry.get("tp"))
            if price > 0 and tp > 0:
                total_win_pct += abs(tp - price) / price * 100
        elif result is False:
            stats["loss"] += 1
            stats["by_tf"][tf]["loss"] += 1
            stats["by_symbol"][ticker]["loss"] += 1
            price = safe_num(entry.get("price"))
            sl = safe_num(entry.get("sl"))
            if price > 0 and sl > 0:
                total_loss_pct += abs(price - sl) / price * 100
        elif result == "expired":
            stats["expired"] += 1
            stats["by_tf"][tf]["expired"] += 1
            stats["by_symbol"][ticker]["expired"] += 1
        else:
            stats["pending"] += 1
            stats["by_tf"][tf]["pending"] += 1
            stats["by_symbol"][ticker]["pending"] += 1

    closed = stats["win"] + stats["loss"]
    if closed > 0:
        stats["win_rate"] = stats["win"] / closed * 100

    if total_loss_pct > 0:
        stats["profit_factor"] = total_win_pct / total_loss_pct
    elif total_win_pct > 0:
        stats["profit_factor"] = 999.0

    if stats["win"] > 0:
        stats["avg_win"] = total_win_pct / stats["win"]
    if stats["loss"] > 0:
        stats["avg_loss"] = total_loss_pct / stats["loss"]

    if closed > 0:
        wr = stats["win"] / closed
        stats["expectancy"] = (wr * stats["avg_win"]) - ((1 - wr) * stats["avg_loss"])

    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for entry in log:
        result = entry.get("result")
        price = safe_num(entry.get("price"))
        if result is True:
            tp = safe_num(entry.get("tp"))
            if price > 0 and tp > 0:
                cumulative += abs(tp - price) / price * 100
        elif result is False:
            sl = safe_num(entry.get("sl"))
            if price > 0 and sl > 0:
                cumulative -= abs(sl - price) / price * 100
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)
    stats["max_dd"] = max_dd

    for tf, s in stats["by_tf"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0
    for ticker, s in stats["by_symbol"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0

    return stats


# ═══════════════════════════════════════════════════════════
# فیلترها
# ═══════════════════════════════════════════════════════════
def filter_logs(
    logs: list,
    market_filter: str = "all",
    signal_filter: str = "all",
    status_filter: str = "all",
    time_filter: str = "all",
) -> list:
    if not logs:
        return []

    now = datetime.now()
    filtered = []

    for entry in logs:
        if market_filter != "all":
            if entry.get("market_type", "spot") != market_filter:
                continue

        sig = entry.get("signal", "")
        if signal_filter == "long" and not SigEnum.is_long(sig):
            continue
        if signal_filter == "short" and not SigEnum.is_short(sig):
            continue

        result = entry.get("result")
        if status_filter == "pending" and result is not None:
            continue
        if status_filter == "win" and result is not True:
            continue
        if status_filter == "loss" and result is not False:
            continue
        if status_filter == "expired" and result != "expired":
            continue

        if time_filter != "all":
            try:
                ts = datetime.fromisoformat(entry.get("timestamp", ""))
                delta = now - ts
                if time_filter == "7d" and delta > timedelta(days=7):
                    continue
                if time_filter == "30d" and delta > timedelta(days=30):
                    continue
            except Exception:
                pass

        filtered.append(entry)

    return filtered


def get_recent_signals(n: int = 20) -> list:
    log = load_signal_log()
    return log[-n:] if len(log) > n else log


__all__ = [
    "load_signal_log",
    "record_signal",
    "backtest_all",
    "compute_stats",
    "filter_logs",
    "get_recent_signals",
    "clear_log",
    "reset_signal_log",
    "SIGNAL_FILE",
]
