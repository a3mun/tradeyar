"""
services/backtest_service.py
بررسی خودکار سیگنال‌ها — نسخه ۲.۰
============================================================
تغییرات نسخه ۲.۰:
  • _mark_expired: ذخیره‌ی قیمت + PnL لحظه‌ی انقضا
  • مهلت بر اساس تعداد کندل (فیوچرز ۵ / اسپات ۱۰)
  • کندل ambiguous → همیشه loss (بدبینانه)
  • ترتیب: اول TP/SL، بعد expire
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from core.contracts import Signal as SigEnum, get_signal_timeout
from core.tz import ensure_utc_index, iso_utc, to_utc_aware, utc_now
from services.cache import closed_candles
from services.data_service import fetch_ohlcv

logger = logging.getLogger(__name__)


def _utcnow():
    """زمان فعلی UTC-aware — تنها منبع زمان در این ماژول"""
    return utc_now()


def _iso_utc(dt):
    """سریال‌سازی با timezone — تا مرورگر درست پارس کند"""
    return iso_utc(dt)


def _candle_time(idx) -> datetime:
    """
    ایندکس کندل را به datetime **UTC-aware** تبدیل می‌کند.
    """
    ts = pd.Timestamp(idx)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC").to_pydatetime()


def _mark_expired(
    log: SignalLog,
    df: pd.DataFrame | None,
    df_raw: pd.DataFrame | None,
    now_utc: datetime,
) -> None:
    """
    علامت‌گذاری سیگنال به‌عنوان منقضی + ذخیره‌ی قیمت لحظه‌ی انقضا.

    ═══ چرا نسخه ۲.۰ ═══
    قبلاً فقط `result = "expired"` ست می‌شد. کاربر نمی‌فهمید
    پیش‌بینی **درست** بود ولی مهلت تموم شد، یا **غلط** بود.

    حالا سه فیلد ذخیره می‌شه:
      • expired_at_price: قیمت لحظه‌ی انقضا
      • expired_pnl_pct: سود/زیان unrealized به درصد
      • expired_bias: "win" | "loss" | "flat" (بر اساس PnL)

    ═══ منبع قیمت (به ترتیب اولویت) ═══
      ۱. آخرین کندل بسته (df)
      ۲. آخرین کندل خام (df_raw)
      ۳. quote زنده از صرافی (fallback)
    """
    exit_price: float | None = None

    # ─── اولویت ۱ و ۲: از کندل‌ها ───
    for source_df in (df, df_raw):
        if source_df is not None and not source_df.empty:
            try:
                val = float(source_df.iloc[-1].get("close", 0))
                if val and val > 0:
                    exit_price = val
                    break
            except Exception:
                continue

    # ─── اولویت ۳: quote زنده ───
    if not exit_price:
        try:
            from services.data_service import fetch_quote

            q = fetch_quote(log.ticker, log.source)
            if q and q.get("price"):
                exit_price = float(q["price"])
        except Exception:
            pass

    # ─── محاسبه‌ی PnL ───
    pnl_pct: float | None = None
    bias: str = "flat"

    if exit_price and log.price and log.price > 0:
        if SigEnum.is_long(log.signal):
            pnl_pct = (exit_price - log.price) / log.price * 100
        else:
            pnl_pct = (log.price - exit_price) / log.price * 100

        # ─── دسته‌بندی: win/loss/flat ───
        if pnl_pct > 0.05:
            bias = "win"
        elif pnl_pct < -0.05:
            bias = "loss"

    # ─── ذخیره ───
    log.expired = True
    log.result = "expired"
    log.result_time = now_utc
    log.exit_price = exit_price
    log.expired_at_price = exit_price
    log.expired_pnl_pct = round(pnl_pct, 3) if pnl_pct is not None else None
    log.expired_bias = bias

    # ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
    # ═══ معیار: PnL > 0.05٪ → درست ═══
    # ═══ چرا ۰.۰۵؟ ═══
    # نویز معمولی بازار کریپتو در TF کوتاه ~۰.۰۵٪ است.
    # کمتر از این، نشون‌دهنده‌ی «تصادفی» است، نه «روند درست».
    if pnl_pct is not None:
        if pnl_pct > 0.05:
            log.trend_correct = True
        elif pnl_pct < -0.05:
            log.trend_correct = False
        else:
            log.trend_correct = None  # بی‌طرف


def _check_one(log: SignalLog) -> str | None:
    """
    بررسی یک سیگنال — نسخه ۲.۰.

    ═══ ترتیب (مهم!) ═══
      ۱. دریافت داده
      ۲. فیلتر کندل‌ها
      ۳. **چک TP/SL** (قبل از expire)
      ۴. اگه هیچ‌کدوم → چک timeout
      ۵. اگه timeout → expire
      ۶. وگرنه → pending

    ═══ کندل ambiguous ═══
    اگه یک کندل **هم TP و هم SL** رو لمس کنه،
    محافظه‌کارانه **loss** فرض می‌شه (چون نمی‌دونیم کدوم اول بود).

    Returns:
        str: "win" | "loss" | "expired" | None (pending)
    """
    if log.result is not None:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    # ═══ مهلت بر اساس TF + market_type ═══
    market_type = getattr(log, "market_type", "futures") or "futures"
    timeout = get_signal_timeout(log.tf, market_type)

    now_utc = _utcnow()
    entry_utc = to_utc_aware(log.timestamp)
    deadline = entry_utc + timeout

    # ═══ ۱. دریافت داده ═══
    try:
        df = fetch_ohlcv(log.ticker, log.tf, log.source, use_cache=True)
    except Exception as e:
        logger.debug(f"[Backtest] {log.ticker}: {e}")
        if now_utc > deadline:
            _mark_expired(log, None, None, now_utc)
            return "expired"
        return None

    if df is None or df.empty:
        if now_utc > deadline:
            _mark_expired(log, None, None, now_utc)
            return "expired"
        return None

    # ═══ ۲. اطمینان از UTC-aware ═══
    if not (isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None):
        logger.warning(
            f"[Backtest] ایندکس بدون tz برای {log.ticker}/{log.source} "
            f"— نرمال‌سازی به UTC"
        )
        df = ensure_utc_index(df)
        if df is None or df.empty:
            if now_utc > deadline:
                _mark_expired(log, None, None, now_utc)
                return "expired"
            return None

    # ═══ ۳. فیلتر کندل‌های بعد از ثبت سیگنال ═══
    df = df[df.index >= entry_utc]
    df_raw = df.copy()  # ← نگه‌داری نسخه‌ی خام برای _mark_expired

    if df.empty:
        if now_utc > deadline:
            _mark_expired(log, None, df_raw, now_utc)
            return "expired"
        return None

    # ═══ ۴. فقط کندل‌های بسته ═══
    df = closed_candles(df, log.tf)

    if df.empty:
        if now_utc > deadline:
            _mark_expired(log, None, df_raw, now_utc)
            return "expired"
        return None

    # ═══ ۵. بررسی کندل‌ها — TP/SL اول ═══
    for idx, row in df.iterrows():
        high = float(row.get("high", 0))
        low = float(row.get("low", 0))

        # ─── محافظت: کندل با دامنه‌ی نامعتبر ───
        if high <= 0 or low <= 0 or high < low:
            continue

        candle_time = _candle_time(idx)

        # ─── LONG ───
        if SigEnum.is_long(log.signal):
            tp_hit = high >= log.tp
            sl_hit = low <= log.sl

            if tp_hit and sl_hit:
                # ═══ کندل ambiguous → همیشه loss ═══
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False  # 🔴 جدید
                return "loss"

            if tp_hit:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                log.trend_correct = True  # 🔴 جدید
                return "win"

            if sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False  # 🔴 جدید
                return "loss"

        # ─── SHORT ───
        elif SigEnum.is_short(log.signal):
            tp_hit = low <= log.tp
            sl_hit = high >= log.sl

            if tp_hit and sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False  # 🔴 جدید
                return "loss"

            if tp_hit:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                log.trend_correct = True  # 🔴 جدید
                return "win"

            if sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False  # 🔴 جدید
                return "loss"

    # ═══ ۶. هیچ‌کدوم لمس نشد — چک timeout ═══
    if now_utc > deadline:
        _mark_expired(log, df, df_raw, now_utc)
        return "expired"

    return None


def backtest_all(max_checks: int = 200) -> dict:
    """
    بررسی سیگنال‌های در انتظار — مقاوم در برابر خطا.
    """
    result = {
        "checked": 0,
        "updated": 0,
        "expired": 0,
        "win": 0,
        "loss": 0,
        "errors": 0,
        "skipped": 0,
    }

    # ═══ ۱. جمع‌آوری شناسه‌ها ═══
    try:
        with Session(engine) as session:
            stmt = (
                select(SignalLog.id)
                .where(SignalLog.result.is_(None))
                .order_by(SignalLog.timestamp.asc())
                .limit(max_checks)
            )
            log_ids = list(session.exec(stmt).all())
    except Exception:
        logger.exception("[Backtest] خطا در خواندن لیست سیگنال‌ها")
        return result

    if not log_ids:
        logger.debug("[Backtest] سیگنال در انتظاری وجود ندارد")
        return result

    # ═══ ۲. پردازش هر سیگنال — مستقل ═══
    for log_id in log_ids:
        result["checked"] += 1

        outcome: str | None = None
        try:
            with Session(engine) as session:
                log = session.get(SignalLog, log_id)

                if log is None or log.result is not None:
                    result["skipped"] += 1
                    continue

                outcome = _check_one(log)

                if outcome:
                    session.add(log)
                    session.commit()
                else:
                    session.rollback()

        except Exception:
            result["errors"] += 1
            logger.exception(
                f"[Backtest] خطا در سیگنال id={log_id} — رد شد و ادامه می‌دهیم"
            )
            continue

        # ─── شمارش نتیجه ───
        if outcome:
            result["updated"] += 1
            if outcome == "expired":
                result["expired"] += 1
            elif outcome == "win":
                result["win"] += 1
            elif outcome == "loss":
                result["loss"] += 1

    # ═══ ۳. جمع‌بندی ═══
    if result["errors"]:
        logger.warning(
            f"[Backtest] {result['errors']} سیگنال با خطا رد شد "
            f"(از {result['checked']} بررسی‌شده)"
        )
    if result["skipped"]:
        logger.debug(
            f"[Backtest] {result['skipped']} سیگنال رد شد (پردازش‌شده/حذف‌شده)"
        )

    return result


def compute_stats(tf: str = "", source: str = "", time_filter: str = "all") -> dict:
    """
    آمار راستی‌آزمایی — با کارمزد واقعی (نسخه ۲.۰).
    """

    stats = {
        "total": 0,
        "wins": 0,
        "losses": 0,
        "pending": 0,
        "expired": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_rr": 0.0,
        "avg_rr_net": 0.0,
        "expectancy": 0.0,
        # ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
        "trend_correct": 0,  # تعداد روند درست
        "trend_wrong": 0,  # تعداد روند غلط
        "trend_accuracy": 0.0,  # درصد (correct / (correct + wrong))
        "expired_win": 0,  # منقضی با PnL مثبت
        "expired_loss": 0,  # منقضی با PnL منفی
        "expired_flat": 0,  # منقضی بی‌تغییر
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

            # ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
            trend_correct = sum(
                1 for r in rows if getattr(r, "trend_correct", None) is True
            )
            trend_wrong = sum(
                1 for r in rows if getattr(r, "trend_correct", None) is False
            )
            stats["trend_correct"] = trend_correct
            stats["trend_wrong"] = trend_wrong
            trend_total = trend_correct + trend_wrong
            if trend_total > 0:
                stats["trend_accuracy"] = round(trend_correct / trend_total * 100, 2)

            # ═══ دسته‌بندی منقضی‌ها ═══
            for r in rows:
                if not r.expired:
                    continue
                bias = getattr(r, "expired_bias", None)
                if bias == "win":
                    stats["expired_win"] += 1
                elif bias == "loss":
                    stats["expired_loss"] += 1
                else:
                    stats["expired_flat"] += 1

            # ═══ Profit Factor — با کارمزد واقعی ═══
            gross_win = 0.0
            gross_loss = 0.0
            for r in rows:
                if r.result not in ("win", "loss") or not r.price:
                    continue

                fee_pct = (r.fee_pct or 0.0) / 100  # به اعشاری

                if r.result == "win" and r.tp:
                    raw_pnl = abs(r.tp - r.price) / r.price
                    net_pnl = raw_pnl - fee_pct
                    gross_win += max(net_pnl, 0.0)
                elif r.result == "loss" and r.sl:
                    raw_pnl = abs(r.price - r.sl) / r.price
                    net_pnl = raw_pnl + fee_pct
                    gross_loss += net_pnl

            if gross_loss > 0:
                stats["profit_factor"] = round(gross_win / gross_loss, 2)
            elif gross_win > 0:
                stats["profit_factor"] = 999.0

            # ═══ R:R خام ═══
            rrs = [r.rr for r in rows if r.rr]
            if rrs:
                stats["avg_rr"] = round(sum(rrs) / len(rrs), 2)

            # ═══ R:R خالص ═══
            rrs_net = [r.rr_net for r in rows if r.rr_net is not None]
            if rrs_net:
                stats["avg_rr_net"] = round(sum(rrs_net) / len(rrs_net), 2)

            # ═══ Expectancy بر اساس R:R خالص ═══
            if closed > 0 and rrs_net:
                wr = stats["win_rate"] / 100
                avg_net = stats["avg_rr_net"]
                stats["expectancy"] = round(wr * avg_net - (1 - wr), 3)

    except Exception:
        logger.exception("[Backtest] خطا در compute_stats")

    return stats


def compute_stats_by_tf(time_filter: str = "all") -> dict:
    """
    آمار راستی‌آزمایی به تفکیک TF (نسخه ۳.۰).

    Args:
        time_filter: بازه‌ی زمانی — "all" | "7d" | "30d"

    ═══ چرا فیلتر زمانی ═══
    وقتی دیتابیس بزرگ می‌شه (۵۰۰+ سیگنال)، میانگین کل
    ممکنه رژیم‌های مختلف بازار رو مخلوط کنه. فیلتر زمانی
    اجازه می‌ده عملکرد **اخیر** رو ببینی.

    Returns:
        {
          "۱ دقیقه": {"total": 20, "trend_correct": 13, ...},
          ...
        }
    """
    from core.contracts import TF_NAMES

    out: dict[str, dict] = {}

    try:
        now = _utcnow()
        with Session(engine) as session:
            for tf in TF_NAMES:
                stmt = select(SignalLog).where(SignalLog.tf == tf)

                # ─── فیلتر زمانی ───
                if time_filter == "7d":
                    stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
                elif time_filter == "30d":
                    stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

                rows = session.exec(stmt).all()

                if not rows:
                    continue

                wins = sum(1 for r in rows if r.result == "win")
                losses = sum(1 for r in rows if r.result == "loss")
                closed = wins + losses

                trend_correct = sum(
                    1 for r in rows if getattr(r, "trend_correct", None) is True
                )
                trend_wrong = sum(
                    1 for r in rows if getattr(r, "trend_correct", None) is False
                )
                trend_total = trend_correct + trend_wrong

                out[tf] = {
                    "total": len(rows),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wins / closed * 100, 1) if closed > 0 else 0.0,
                    "trend_correct": trend_correct,
                    "trend_wrong": trend_wrong,
                    "trend_total": trend_total,
                    "trend_accuracy": (
                        round(trend_correct / trend_total * 100, 1)
                        if trend_total > 0
                        else 0.0
                    ),
                }
    except Exception:
        logger.exception("[Backtest] خطا در compute_stats_by_tf")

    return out
