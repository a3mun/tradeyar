"""
services/backtest_service.py
بررسی خودکار سیگنال‌ها — نسخه ۳.۰
============================================================
🔴 تغییرات فاز ۱۰.۱:

  ۱. **timeout check قبل از fetch** — اگر سیگنال منقضی شده،
     بدون fetch_ohlcv مستقیم expired می‌شه. (رفع ۱ تست قدیمی)

  ۲. **trend_correct مستقل از TP/SL** — الان فقط بر اساس
     جهت واقعی قیمت (exit vs entry) تعریف می‌شه. TP/SL
     خوردن یا نخوردن ربطی به trend_correct نداره.

     مثال:
       LONG @ 100 → exit @ 102 → trend_correct=True (حتی اگه TP نخورده باشه)
       SHORT @ 100 → exit @ 102 → trend_correct=False

  ۳. **آمار تفکیکی confidence** — compute_stats_by_quality
     که ۴ دسته برمی‌گردونه:
        all (همه)، strong (>=70)، normal (50-69)، weak (<50)

  ۴. **آمار جداگانه trend_accuracy و win_rate**:
     • win_rate = TP/SL real (فقط win/loss)
     • trend_accuracy = جهت درست (شامل expired با bias)
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
    """زمان فعلی UTC-aware"""
    return utc_now()


def _iso_utc(dt):
    """سریال‌سازی با timezone"""
    return iso_utc(dt)


def _candle_time(idx) -> datetime:
    """ایندکس کندل را به datetime **UTC-aware** تبدیل می‌کند."""
    ts = pd.Timestamp(idx)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC").to_pydatetime()


def _compute_trend_correct(
    signal: str,
    entry_price: float,
    exit_price: float,
) -> bool | None:
    """
    🔴 فاز ۱۰.۱ — trend_correct مستقل از TP/SL.

    ═══ تعریف جدید ═══
    trend_correct = آیا قیمت **در جهت** سیگنال حرکت کرده؟

    • LONG و exit > entry → True
    • LONG و exit < entry → False
    • SHORT و exit < entry → True
    • SHORT و exit > entry → False
    • LONG و exit == entry → None (بی‌طرف)
    • SHORT و exit == entry → None (بی‌طرف)

    ═══ چرا این معیار ═══
    اگه فقط win/loss رو نگاه کنیم، سیگنالی که TP نخورده ولی
    در جهت درست رفته باشه هم loss حساب می‌شه. ولی کاربر
    می‌خواد بدونه: «آیا موتور ترند-سنجی من داره درست کار
    می‌کنه؟» → این معیار دقیقاً همون رو نشون می‌ده.

    ═══ نکته مهم ═══
    **بدون** threshold اینجا. حتی ۰.۰۰۱٪ هم در جهت درست
    حساب می‌شه. threshold فقط توی UI برای نمایش.

    Args:
        signal: "LONG" یا "SHORT" یا "LONG ضعیف" و ...
        entry_price: قیمت ورود
        exit_price: قیمت خروج

    Returns:
        True/False/None (None اگه قیمت تغییر نکرده یا سیگنال جهت‌دار نیست)
    """
    if not entry_price or entry_price <= 0:
        return None
    if not exit_price or exit_price <= 0:
        return None

    # ─── محاسبه‌ی delta با دقت ───
    delta = (exit_price - entry_price) / entry_price
    # ─── آستانه‌ی نویز: کمتر از ۰.۰۱٪ = بی‌طرف ───
    if abs(delta) < 0.0001:
        return None

    if SigEnum.is_long(signal):
        return delta > 0
    if SigEnum.is_short(signal):
        return delta < 0
    return None


def _mark_expired(
    log: SignalLog,
    df: pd.DataFrame | None,
    df_raw: pd.DataFrame | None,
    now_utc: datetime,
) -> None:
    """
    علامت‌گذاری سیگنال به‌عنوان منقضی + ذخیره‌ی قیمت لحظه‌ی انقضا.

    ═══ فاز ۱۰.۱ ═══
    trend_correct الان **مستقل** از PnL محاسبه می‌شه — بر اساس
    مقایسه‌ی قیمت انقضا با قیمت ورود.
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

        # ─── دسته‌بندی ───
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

    # ═══ 🔴 trend_correct — مستقل از TP/SL ═══
    if exit_price and log.price and log.price > 0:
        log.trend_correct = _compute_trend_correct(log.signal, log.price, exit_price)
    else:
        log.trend_correct = None


def _check_one(log: SignalLog) -> str | None:
    """
    بررسی یک سیگنال — نسخه ۳.۰.

    ═══ ترتیب جدید (مهم!) ═══
      ۱. **چک timeout** اول — اگه منقضی شده، بدون fetch مستقیم expire
      ۲. دریافت داده
      ۳. فیلتر کندل‌ها
      ۴. چک TP/SL
      ۵. چک timeout نهایی
      ۶. pending

    ═══ چرا timeout اول ═══
    در دیتای واقعی، ۷۱ سیگنال pending مونده بود چون
    fetch_ohlcv برای هر یک صدا زده می‌شد. این:
      • کند بود (هر fetch ~۱-۲s)
      • باعث می‌شد شبکه بی‌دلیل مصرف بشه
      • وقتی صرافی timeout بده، منطق خراب می‌شد

    الان: قبل از هر fetch چک می‌کنیم که آیا سیگنال **هنوز
    زنده** هست یا نه. اگه منقضی شده، مستقیم expired می‌شه.
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

    # ═══════════════════════════════════════════════════════
    # 🔴 فاز ۱۰.۱ — timeout check **قبل از** fetch
    # ═══════════════════════════════════════════════════════
    # ═══ چرا ═══
    # قبلاً اول fetch می‌شد، بعد اگه timeout بود expire.
    # نتیجه: برای سیگنال‌های ۲۰ روزه هم fetch می‌زد.
    #
    # ═══ الان ═══
    # اگه منقضی شده، **بدون fetch** expire می‌شه. قیمت انقضا
    # از fetch_quote (سبک) گرفته می‌شه، نه OHLCV کامل.
    if now_utc > deadline:
        _mark_expired(log, None, None, now_utc)
        logger.debug(f"[Backtest] {log.ticker}: منقضی (بدون fetch)")
        return "expired"

    # ═══ ۱. دریافت داده (فقط اگه هنوز زنده است) ═══
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
    df_raw = df.copy()

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

    # ═══ ۵. بررسی کندل‌ها — TP/SL ═══
    for idx, row in df.iterrows():
        high = float(row.get("high", 0))
        low = float(row.get("low", 0))

        if high <= 0 or low <= 0 or high < low:
            continue

        candle_time = _candle_time(idx)

        # ─── LONG ───
        if SigEnum.is_long(log.signal):
            tp_hit = high >= log.tp
            sl_hit = low <= log.sl

            if tp_hit and sl_hit:
                # ─── ambiguous → محافظه‌کارانه loss ───
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False
                return "loss"

            if tp_hit:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                log.trend_correct = True
                return "win"

            if sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False
                return "loss"

        # ─── SHORT ───
        elif SigEnum.is_short(log.signal):
            tp_hit = low <= log.tp
            sl_hit = high >= log.sl

            if tp_hit and sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False
                return "loss"

            if tp_hit:
                log.result = "win"
                log.result_time = candle_time
                log.exit_price = log.tp
                log.trend_correct = True
                return "win"

            if sl_hit:
                log.result = "loss"
                log.result_time = candle_time
                log.exit_price = log.sl
                log.trend_correct = False
                return "loss"

    # ═══ ۶. هیچ‌کدوم لمس نشد — چک timeout ═══
    if now_utc > deadline:
        _mark_expired(log, df, df_raw, now_utc)
        return "expired"

    return None


def backtest_all(max_checks: int = 200) -> dict:
    """بررسی سیگنال‌های در انتظار — مقاوم در برابر خطا."""
    result = {
        "checked": 0,
        "updated": 0,
        "expired": 0,
        "win": 0,
        "loss": 0,
        "errors": 0,
        "skipped": 0,
    }

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
            logger.exception(f"[Backtest] خطا در سیگنال id={log_id}")
            continue

        if outcome:
            result["updated"] += 1
            if outcome == "expired":
                result["expired"] += 1
            elif outcome == "win":
                result["win"] += 1
            elif outcome == "loss":
                result["loss"] += 1

    if result["errors"]:
        logger.warning(
            f"[Backtest] {result['errors']} سیگنال با خطا رد شد "
            f"(از {result['checked']} بررسی‌شده)"
        )

    return result


# ═══════════════════════════════════════════════════════════
# compute_stats — نسخه ۳.۰ (trend_accuracy مستقل)
# ═══════════════════════════════════════════════════════════
def _compute_stats_for_rows(rows: list[SignalLog]) -> dict:
    """
    محاسبه‌ی آمار برای یک لیست از ردیف‌ها.

    ═══ دو معیار مستقل ═══
    ۱. win_rate = TP/SL (فقط win/loss)
    ۲. trend_accuracy = جهت‌سنجی (شامل expired)
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
        "trend_correct": 0,
        "trend_wrong": 0,
        "trend_accuracy": 0.0,
        "expired_win": 0,
        "expired_loss": 0,
        "expired_flat": 0,
    }

    if not rows:
        return stats

    stats["total"] = len(rows)
    stats["wins"] = sum(1 for r in rows if r.result == "win")
    stats["losses"] = sum(1 for r in rows if r.result == "loss")
    stats["pending"] = sum(1 for r in rows if r.result is None and not r.expired)
    stats["expired"] = sum(1 for r in rows if r.expired)

    closed = stats["wins"] + stats["losses"]
    if closed > 0:
        stats["win_rate"] = round(stats["wins"] / closed * 100, 2)

    # ═══ Trend accuracy ═══
    trend_correct = sum(1 for r in rows if getattr(r, "trend_correct", None) is True)
    trend_wrong = sum(1 for r in rows if getattr(r, "trend_correct", None) is False)
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

    # ═══ Profit Factor ═══
    gross_win = 0.0
    gross_loss = 0.0
    for r in rows:
        if r.result not in ("win", "loss") or not r.price:
            continue

        fee_pct = (r.fee_pct or 0.0) / 100

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

    # ═══ R:R ═══
    rrs = [r.rr for r in rows if r.rr]
    if rrs:
        stats["avg_rr"] = round(sum(rrs) / len(rrs), 2)

    rrs_net = [r.rr_net for r in rows if r.rr_net is not None]
    if rrs_net:
        stats["avg_rr_net"] = round(sum(rrs_net) / len(rrs_net), 2)

    # ═══ Expectancy ═══
    if closed > 0 and rrs_net:
        wr = stats["win_rate"] / 100
        avg_net = stats["avg_rr_net"]
        stats["expectancy"] = round(wr * avg_net - (1 - wr), 3)

    return stats


def compute_stats(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict:
    """
    آمار راستی‌آزمایی — نسخه ۳.۰.

    🔴 تغییر فاز ۱۰.۱:
      • فیلتر is_weak حذف شد از compute_stats
      • **همه** سیگنال‌ها در آمار میان
      • تفکیک is_weak از طریق compute_stats_by_quality

    ═══ چرا ═══
    فیلتر is_weak قبلی باعث می‌شد که آمار **گمراه‌کننده** باشه،
    چون سیگنال‌های ضعیف (که در دیتا بهتر عمل کردن!) از آمار
    حذف می‌شدند.
    """
    try:
        with Session(engine) as session:
            stmt = select(SignalLog)
            if tf:
                stmt = stmt.where(SignalLog.tf == tf)
            if source:
                stmt = stmt.where(SignalLog.source == source)
            if risk_profile:
                stmt = stmt.where(SignalLog.risk_profile == risk_profile)

            now = _utcnow()
            if time_filter == "7d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
            elif time_filter == "30d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

            all_rows = session.exec(stmt).all()

        return _compute_stats_for_rows(list(all_rows))

    except Exception:
        logger.exception("[Backtest] خطا در compute_stats")
        return _compute_stats_for_rows([])


# ═══════════════════════════════════════════════════════════
# 🎯 جدید فاز ۱۰.۱ — آمار تفکیکی بر اساس quality
# ═══════════════════════════════════════════════════════════
def compute_stats_by_quality(
    tf: str = "",
    source: str = "",
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict:
    """
    آمار به تفکیک سطح کیفیت سیگنال.

    ═══ ساختار خروجی ═══
        {
            "all":    {win_rate, trend_accuracy, total, ...},
            "strong": {نفس},
            "normal": {نفس},
            "weak":   {نفس},
        }

    ═══ تعریف دسته‌ها ═══
      • strong: confidence >= 70
      • normal: 50 <= confidence < 70
      • weak:   confidence < 50
    """
    try:
        with Session(engine) as session:
            stmt = select(SignalLog)
            if tf:
                stmt = stmt.where(SignalLog.tf == tf)
            if source:
                stmt = stmt.where(SignalLog.source == source)
            if risk_profile:
                stmt = stmt.where(SignalLog.risk_profile == risk_profile)

            now = _utcnow()
            if time_filter == "7d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
            elif time_filter == "30d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

            all_rows = list(session.exec(stmt).all())

    except Exception:
        logger.exception("[Backtest] خطا در compute_stats_by_quality")
        all_rows = []

    def _filter_by_conf(min_c: int, max_c: int) -> list[SignalLog]:
        return [r for r in all_rows if min_c <= (r.confidence or 0) < max_c]

    return {
        "all": _compute_stats_for_rows(all_rows),
        "strong": _compute_stats_for_rows(_filter_by_conf(70, 101)),
        "normal": _compute_stats_for_rows(_filter_by_conf(50, 70)),
        "weak": _compute_stats_for_rows(_filter_by_conf(0, 50)),
    }


# ═══════════════════════════════════════════════════════════
# compute_stats_by_tf — بدون تغییر اساسی
# ═══════════════════════════════════════════════════════════
def compute_stats_by_tf(
    time_filter: str = "all",
    risk_profile: str = "",
) -> dict:
    """آمار به تفکیک TF."""
    from core.contracts import TF_NAMES

    out: dict[str, dict] = {}

    try:
        now = _utcnow()
        with Session(engine) as session:
            for tf in TF_NAMES:
                stmt = select(SignalLog).where(SignalLog.tf == tf)

                if time_filter == "7d":
                    stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
                elif time_filter == "30d":
                    stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

                if risk_profile:
                    stmt = stmt.where(SignalLog.risk_profile == risk_profile)

                rows = list(session.exec(stmt).all())

                if not rows:
                    continue

                s = _compute_stats_for_rows(rows)

                # ─── ساختار سازگار با فرانت قبلی ───
                out[tf] = {
                    "total": s["total"],
                    "wins": s["wins"],
                    "losses": s["losses"],
                    "win_rate": s["win_rate"],
                    "trend_correct": s["trend_correct"],
                    "trend_wrong": s["trend_wrong"],
                    "trend_total": s["trend_correct"] + s["trend_wrong"],
                    "trend_accuracy": s["trend_accuracy"],
                }
    except Exception:
        logger.exception("[Backtest] خطا در compute_stats_by_tf")

    return out


def compute_stats_by_profile(time_filter: str = "all") -> dict:
    """آمار به تفکیک پروفایل (جسورانه vs محتاطانه)."""
    out = {}
    for profile in ["aggressive", "conservative"]:
        out[profile] = compute_stats(
            time_filter=time_filter,
            risk_profile=profile,
        )
    return out
