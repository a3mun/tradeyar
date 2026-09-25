"""
core/backtester.py
Backtest سیگنال‌ها با داده تاریخی yfinance
نسخه ۲.۰ — اصلاح‌شده کامل
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# مسیر فایل ذخیره سیگنال‌ها
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SIGNAL_FILE = DATA_DIR / "signals_log.json"

# نقشه تبدیل تایم‌فریم به دقیقه
TF_TO_MINUTES = {
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30,
    "۱ ساعت": 60,
    "روزانه": 1440,
}


# ═══════════════════════════════════════════════════════════
# ذخیره و بارگذاری
# ═══════════════════════════════════════════════════════════

def load_signal_log() -> list:
    """بارگذاری سیگنال‌ها از فایل JSON"""
    if not SIGNAL_FILE.exists():
        return []
    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"[Backtest] خطا در خوندن سیگنال: {e}")
        return []


def save_signal_log(log: list) -> None:
    """ذخیره سیگنال‌ها با محدودیت ۱۰۰۰ رکورد آخر"""
    try:
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(log[-1000:], f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Backtest] خطا در ذخیره سیگنال: {e}")


# ═══════════════════════════════════════════════════════════
# ثبت سیگنال جدید
# ═══════════════════════════════════════════════════════════

def record_signal(
    ticker: str,
    name: str,
    signal: str,
    price: float,
    tf_name: str,
    sl_tp: dict | None,
    cooldown_minutes: int = 60,
) -> bool:
    """
    ثبت سیگنال جدید با جلوگیری از تکرار (cooldown)
    
    Returns:
        True اگه ثبت شد، False اگه تکراری بود
    """
    if signal not in ("LONG", "SHORT"):
        return False
    if not price or price <= 0:
        return False

    log = load_signal_log()
    now = datetime.now()

    # چک کردن تکرار — اگه سیگنال مشابه در بازه cooldown ثبت شده، نادیده بگیر
    for entry in reversed(log[-50:]):
        try:
            entry_time = datetime.fromisoformat(entry["time"])
            delta = (now - entry_time).total_seconds() / 60
            if delta < cooldown_minutes:
                if (entry["ticker"] == ticker
                        and entry["tf"] == tf_name
                        and entry["signal"] == signal):
                    return False
        except (KeyError, ValueError):
            continue

    entry = {
        "time": now.isoformat(),
        "ticker": ticker,
        "name": name,
        "tf": tf_name,
        "signal": signal,
        "price": float(price),
        "sl": float(sl_tp["sl"]) if sl_tp else None,
        "tp": float(sl_tp["tp"]) if sl_tp else None,
        "result": None,           # None=در انتظار، True=برد، False=باخت، "neutral"=خنثی
        "resolved_at": None,
        "resolved_price": None,
    }
    log.append(entry)
    save_signal_log(log)
    return True


# ═══════════════════════════════════════════════════════════
# Backtest اصلی — نسخه اصلاح‌شده
# ═══════════════════════════════════════════════════════════

def _pick_interval(tf_name: str) -> str:
    """انتخاب interval مناسب yfinance بر اساس تایم‌فریم سیگنال"""
    tf_min = TF_TO_MINUTES.get(tf_name, 60)
    if tf_min <= 5:
        return "5m"
    elif tf_min <= 15:
        return "15m"
    elif tf_min <= 30:
        return "30m"
    elif tf_min <= 60:
        return "1h"
    else:
        return "1d"


def _resolve_one(entry: dict, now: datetime) -> bool:
    """
    بررسی یک سیگنال و تعیین نتیجه.
    
    Returns:
        True اگه entry تغییر کرد، False اگه نه
    """
    # اگه قبلاً حل شده، رد شو
    if entry.get("result") is not None:
        return False

    sl = entry.get("sl")
    tp = entry.get("tp")
    signal = entry.get("signal", "")

    # اگه SL/TP نداره، رد شو
    if not sl or not tp:
        return False

    try:
        entry_time = datetime.fromisoformat(entry["time"])
    except (KeyError, ValueError):
        return False

    age_hours = (now - entry_time).total_seconds() / 3600

    # اگه بیشتر از ۷ روز گذشته و حل نشده → خنثی
    if age_hours > 24 * 7:
        entry["result"] = "neutral"
        entry["resolved_at"] = now.isoformat()
        return True

    # ✅ باگ #1 رفع شد: اطمینان از اینکه start < end
    # اگه سیگنال تازه ثبت شده، start رو ۱۰ دقیقه عقب‌تر ببر
    start_dt = entry_time - timedelta(minutes=5)
    end_dt = now + timedelta(minutes=5)

    interval = _pick_interval(entry.get("tf", ""))

    try:
        df = yf.download(
            entry["ticker"],
            start=start_dt,
            end=end_dt,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as e:
        print(f"[Backtest] خطای دانلود {entry['ticker']}: {e}")
        return False

    if df is None or df.empty:
        return False

    # نرمال‌سازی ستون‌ها
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]

    if not {"high", "low"}.issubset(df.columns):
        return False

    df = df.dropna(subset=["high", "low"])
    if df.empty:
        return False

    # ✅ باگ #2 رفع شد: منطق دقیق بررسی کندل به کندل
    # در هر کندل چک می‌کنیم کدوم اول لمس میشه
    # قانون محافظه‌کارانه: اگه هم SL و هم TP در یک کندل لمس شدن، SL رو بگیر (بدبینانه)
    result = None
    resolved_price = None

    for ts, row in df.iterrows():
        try:
            high = float(row["high"])
            low = float(row["low"])
        except (ValueError, TypeError):
            continue

        if "LONG" in signal:
            # LONG: SL پایین‌تر، TP بالاتر
            hit_sl = low <= sl
            hit_tp = high >= tp
            if hit_sl and hit_tp:
                # محافظه‌کارانه: SL رو در نظر بگیر
                result = False
                resolved_price = sl
                break
            elif hit_sl:
                result = False
                resolved_price = sl
                break
            elif hit_tp:
                result = True
                resolved_price = tp
                break

        elif "SHORT" in signal:
            # SHORT: SL بالاتر، TP پایین‌تر
            hit_sl = high >= sl
            hit_tp = low <= tp
            if hit_sl and hit_tp:
                result = False
                resolved_price = sl
                break
            elif hit_sl:
                result = False
                resolved_price = sl
                break
            elif hit_tp:
                result = True
                resolved_price = tp
                break

    if result is not None:
        entry["result"] = result
        entry["resolved_at"] = now.isoformat()
        entry["resolved_price"] = float(resolved_price) if resolved_price else None
        return True

    return False


def backtest_all() -> dict:
    """
    اجرای Backtest روی همه سیگنال‌های حل‌نشده.
    
    Returns:
        dict خلاصه: {"checked": n, "resolved": m}
    """
    log = load_signal_log()
    if not log:
        return {"checked": 0, "resolved": 0}

    now = datetime.now()
    checked = 0
    resolved = 0

    for entry in log:
        if entry.get("result") is not None:
            continue
        checked += 1
        try:
            if _resolve_one(entry, now):
                resolved += 1
        except Exception as e:
            print(f"[Backtest] خطا در {entry.get('ticker')}: {e}")

    if resolved > 0:
        save_signal_log(log)

    return {"checked": checked, "resolved": resolved}


# ═══════════════════════════════════════════════════════════
# آمار و تحلیل نتایج
# ═══════════════════════════════════════════════════════════

def compute_stats(log: list | None = None) -> dict:
    """
    محاسبه آمار کامل از سیگنال‌ها.
    
    Returns:
        dict: {
            total, win, loss, neutral, pending,
            win_rate, profit_factor, max_dd, avg_win, avg_loss,
            expectancy, by_tf
        }
    """
    if log is None:
        log = load_signal_log()

    stats = {
        "total": 0, "win": 0, "loss": 0, "neutral": 0, "pending": 0,
        "win_rate": 0.0, "profit_factor": 0.0, "max_dd": 0.0,
        "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 0.0,
        "by_tf": {},
        "by_symbol": {},
    }

    profits = []
    losses = []

    for entry in log:
        stats["total"] += 1
        tf = entry.get("tf", "نامشخص")
        ticker = entry.get("ticker", "?")
        result = entry.get("result")

        # آمار کلی TF
        stats["by_tf"].setdefault(tf, {
            "total": 0, "win": 0, "loss": 0, "neutral": 0, "pending": 0,
            "win_rate": 0.0,
        })
        stats["by_tf"][tf]["total"] += 1

        # آمار به تفکیک نماد
        stats["by_symbol"].setdefault(ticker, {
            "total": 0, "win": 0, "loss": 0, "win_rate": 0.0,
        })
        stats["by_symbol"][ticker]["total"] += 1

        if result is True:
            stats["win"] += 1
            stats["by_tf"][tf]["win"] += 1
            stats["by_symbol"][ticker]["win"] += 1
            if entry.get("tp") and entry.get("price"):
                p = abs(entry["tp"] - entry["price"]) / entry["price"] * 100
                profits.append(p)
        elif result is False:
            stats["loss"] += 1
            stats["by_tf"][tf]["loss"] += 1
            stats["by_symbol"][ticker]["loss"] += 1
            if entry.get("sl") and entry.get("price"):
                l = abs(entry["sl"] - entry["price"]) / entry["price"] * 100
                losses.append(l)
        elif result == "neutral":
            stats["neutral"] += 1
            stats["by_tf"][tf]["neutral"] += 1
        else:
            stats["pending"] += 1
            stats["by_tf"][tf]["pending"] += 1

    # محاسبه نرخ برد
    resolved = stats["win"] + stats["loss"]
    stats["win_rate"] = (stats["win"] / resolved * 100) if resolved > 0 else 0.0

    # Profit Factor
    total_profit = sum(profits) if profits else 0.0
    total_loss = sum(losses) if losses else 0.0
    stats["profit_factor"] = (total_profit / total_loss) if total_loss > 0 else 0.0

    # میانگین‌ها
    stats["avg_win"] = (total_profit / len(profits)) if profits else 0.0
    stats["avg_loss"] = (total_loss / len(losses)) if losses else 0.0

    # Expectancy = (WinRate × AvgWin) - (LossRate × AvgLoss)
    if resolved > 0:
        wr = stats["win"] / resolved
        lr = stats["loss"] / resolved
        stats["expectancy"] = (wr * stats["avg_win"]) - (lr * stats["avg_loss"])

    # Max Drawdown (به درصد، روی سری cumulative)
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for entry in log:
        if entry.get("result") is True and entry.get("tp") and entry.get("price"):
            cumulative += abs(entry["tp"] - entry["price"]) / entry["price"] * 100
        elif entry.get("result") is False and entry.get("sl") and entry.get("price"):
            cumulative -= abs(entry["sl"] - entry["price"]) / entry["price"] * 100
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)
    stats["max_dd"] = max_dd

    # نرخ برد هر TF
    for tf, s in stats["by_tf"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0

    for ticker, s in stats["by_symbol"].items():
        r = s["win"] + s["loss"]
        s["win_rate"] = (s["win"] / r * 100) if r > 0 else 0.0

    return stats


def clear_log() -> None:
    """پاک کردن کامل لاگ سیگنال‌ها (برای تست)"""
    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()


def get_recent_signals(n: int = 20) -> list:
    """آخرین n سیگنال"""
    log = load_signal_log()
    return log[-n:] if len(log) > n else log