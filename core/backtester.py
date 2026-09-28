"""
core/backtester.py
راستی‌آزمایی سیگنال‌ها — نسخه ۳.۰
================================================
- ثبت سیگنال با SL/TP
- بررسی خودکار برد/باخت/انتظار
- محاسبه آمار کامل (Win Rate, PF, Max DD)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from core.data_fetcher import fetch_history, TIMEFRAMES
from core.utils import safe_num


# ═══════════════════════════════════════════════════════════
# مسیر فایل لاگ
# ═══════════════════════════════════════════════════════════
SIGNAL_FILE = Path("data/signals_log.json")


# ═══════════════════════════════════════════════════════════
# بارگذاری لاگ
# ═══════════════════════════════════════════════════════════
def load_signal_log() -> list:
    """بارگذاری لاگ سیگنال‌ها از فایل JSON"""
    if not SIGNAL_FILE.exists():
        return []

    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[Backtester] خطا در load: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# ذخیره لاگ
# ═══════════════════════════════════════════════════════════
def _save_signal_log(log: list) -> None:
    """ذخیره لاگ به فایل JSON"""
    try:
        SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[Backtester] خطا در save: {e}")


# ═══════════════════════════════════════════════════════════
# پاک کردن کامل لاگ
# ═══════════════════════════════════════════════════════════
def clear_log() -> None:
    """پاک کردن کامل لاگ سیگنال‌ها"""
    if SIGNAL_FILE.exists():
        try:
            SIGNAL_FILE.unlink()
            print(f"[Backtester] لاگ پاک شد")
        except Exception as e:
            print(f"[Backtester] خطا در پاک کردن: {e}")


# نام مستعار برای سازگاری با app.py
reset_signal_log = clear_log


# ═══════════════════════════════════════════════════════════
# ثبت سیگنال جدید
# ═══════════════════════════════════════════════════════════
def record_signal(
    ticker: str,
    name: str,
    signal: str,
    price: float,
    tf_name: str,
    sl_tp: Optional[dict] = None,
) -> None:
    """
    ثبت یه سیگنال جدید.
    اگه ۲۴ ساعت از آخرین سیگنال هم‌تایم‌فریم/نماد گذشته باشه، جدید ثبت می‌شه.
    """
    if signal not in ("LONG", "SHORT"):
        return

    if not price or price <= 0:
        return

    log = load_signal_log()

    # ─── جلوگیری از تکرار در ۲۴ ساعت اخیر ───
    now = datetime.now()
    for entry in reversed(log):
        try:
            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
            if (now - entry_time).total_seconds() < 24 * 3600:
                if (entry.get("ticker") == ticker
                        and entry.get("tf") == tf_name
                        and entry.get("signal") == signal):
                    return
        except Exception:
            continue

    # ─── ثبت ───
    entry = {
        "timestamp": now.isoformat(),
        "ticker": ticker,
        "name": name,
        "signal": signal,
        "price": float(price),
        "tf": tf_name,
        "result": None,
        "result_time": None,
    }

    if sl_tp:
        entry["sl"] = safe_num(sl_tp.get("sl"))
        entry["tp"] = safe_num(sl_tp.get("tp"))
        entry["sl_tp_type"] = sl_tp.get("type", "")

    log.append(entry)

    # ─── محدودیت ۱۰۰۰ رکورد ───
    if len(log) > 1000:
        log = log[-1000:]

    _save_signal_log(log)


# ═══════════════════════════════════════════════════════════
# بررسی یه سیگنال (بسته شده یا نه)
# ═══════════════════════════════════════════════════════════
def _check_signal(entry: dict) -> dict:
    """
    بررسی یه سیگنال:
      - آمدن به TP → result=True (برد)
      - آمدن به SL → result=False (باخت)
      - هنوز نه → result=None (انتظار)
    """
    if entry.get("result") is not None:
        return entry

    ticker = entry.get("ticker")
    tf_name = entry.get("tf")
    signal = entry.get("signal")
    entry_price = safe_num(entry.get("price"))
    entry_time_str = entry.get("timestamp")

    sl = safe_num(entry.get("sl"))
    tp = safe_num(entry.get("tp"))

    if not ticker or not signal or not entry_price or not sl or not tp:
        return entry

    if not entry_time_str:
        return entry

    # ─── تایم‌فریم ───
    interval, period = "1h", "3mo"
    for iv, p, n in TIMEFRAMES:
        if n == tf_name:
            interval, period = iv, p
            break

    try:
        entry_time = datetime.fromisoformat(entry_time_str)
    except Exception:
        return entry

    # ─── دریافت دیتای فعلی ───
    try:
        df = fetch_history(ticker, interval, period)
        if df is None or df.empty:
            return entry
    except Exception:
        return entry

    # ─── فیلتر از زمان ثبت به بعد ───
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df = df[df.index.tz_localize(None) >= entry_time]
        else:
            df = df[df.index >= entry_time]
    except Exception:
        pass

    if df.empty:
        return entry

    # ─── بررسی کندل‌ها ───
    for _, row in df.iterrows():
        high = safe_num(row.get("high"))
        low = safe_num(row.get("low"))

        if signal == "LONG":
            if high >= tp:
                entry["result"] = True
                entry["result_time"] = datetime.now().isoformat()
                entry["exit_price"] = tp
                return entry
            if low <= sl:
                entry["result"] = False
                entry["result_time"] = datetime.now().isoformat()
                entry["exit_price"] = sl
                return entry

        elif signal == "SHORT":
            if low <= tp:
                entry["result"] = True
                entry["result_time"] = datetime.now().isoformat()
                entry["exit_price"] = tp
                return entry
            if high >= sl:
                entry["result"] = False
                entry["result_time"] = datetime.now().isoformat()
                entry["exit_price"] = sl
                return entry

    return entry


# ═══════════════════════════════════════════════════════════
# Backtest همه سیگنال‌ها
# ═══════════════════════════════════════════════════════════
def backtest_all() -> None:
    """بررسی همه سیگنال‌های ثبت‌شده که هنوز نتیجه‌شون مشخص نیست"""
    log = load_signal_log()
    if not log:
        return

    updated = False
    for i, entry in enumerate(log):
        if entry.get("result") is None:
            new_entry = _check_signal(entry)
            if new_entry.get("result") is not None:
                log[i] = new_entry
                updated = True

    if updated:
        _save_signal_log(log)


# ═══════════════════════════════════════════════════════════
# محاسبه آمار
# ═══════════════════════════════════════════════════════════
def compute_stats(log: Optional[list] = None) -> dict:
    """
    محاسبه آمار کامل از لاگ سیگنال‌ها.
    
    Returns:
        {
            "total": int,
            "win": int,
            "loss": int,
            "pending": int,
            "win_rate": float,
            "profit_factor": float,
            "max_dd": float,
            "by_tf": {...},
            "by_symbol": {...},
            "expectancy": float,
            "avg_win": float,
            "avg_loss": float,
        }
    """
    if log is None:
        log = load_signal_log()

    stats = {
        "total": 0,
        "win": 0,
        "loss": 0,
        "pending": 0,
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

    # ─── شمارش ───
    total_win_pct = 0.0
    total_loss_pct = 0.0

    for entry in log:
        result = entry.get("result")
        tf = entry.get("tf", "?")
        ticker = entry.get("ticker", "?")

        if tf not in stats["by_tf"]:
            stats["by_tf"][tf] = {"win": 0, "loss": 0, "pending": 0, "win_rate": 0.0}
        if ticker not in stats["by_symbol"]:
            stats["by_symbol"][ticker] = {"win": 0, "loss": 0, "pending": 0, "win_rate": 0.0}

        if result is True:
            stats["win"] += 1
            stats["by_tf"][tf]["win"] += 1
            stats["by_symbol"][ticker]["win"] += 1

            # محاسبه درصد سود
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

        else:
            stats["pending"] += 1
            stats["by_tf"][tf]["pending"] += 1
            stats["by_symbol"][ticker]["pending"] += 1

    # ─── نرخ برد ───
    closed = stats["win"] + stats["loss"]
    if closed > 0:
        stats["win_rate"] = stats["win"] / closed * 100

    # ─── Profit Factor ───
    if total_loss_pct > 0:
        stats["profit_factor"] = total_win_pct / total_loss_pct
    elif total_win_pct > 0:
        stats["profit_factor"] = 999.0  # همه برد، ضرری نبوده

    # ─── میانگین برد/باخت ───
    if stats["win"] > 0:
        stats["avg_win"] = total_win_pct / stats["win"]
    if stats["loss"] > 0:
        stats["avg_loss"] = total_loss_pct / stats["loss"]

    # ─── Expectancy ───
    if closed > 0:
        wr = stats["win"] / closed
        stats["expectancy"] = (wr * stats["avg_win"]) - ((1 - wr) * stats["avg_loss"])

    # ─── Max Drawdown ───
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

    # ─── نرخ برد به تفکیک TF ───
    for tf, s in stats["by_tf"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0

    for ticker, s in stats["by_symbol"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0

    return stats


# ═══════════════════════════════════════════════════════════
# آخرین سیگنال‌ها
# ═══════════════════════════════════════════════════════════
def get_recent_signals(n: int = 20) -> list:
    """آخرین n سیگنال"""
    log = load_signal_log()
    return log[-n:] if len(log) > n else log