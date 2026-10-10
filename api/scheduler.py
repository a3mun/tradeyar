"""
api/scheduler.py — راستی‌آزمایی و اسکن خودکار
============================================================
نسخه ۳.۰ · فاز ۱۰.۲
🔴 تغییرات:
  • auto_scan_and_record فقط نمادهای هدفمند رو اسکن می‌کنه:
      - نمادهای ثابت (BTC-USD, BTC-IRT, PAXG-USD, PAXG-IRT)
      - نمادهای واچ‌لیست (فقط کریپتو)
      - نماد فعال فعلی (اگه کاربر داره نگاه می‌کنه)
  • فقط ۱ TF و ۱ پروفایل (نه همه ترکیب‌ها)
  • حذف حلقه‌های تودرتوی اشتباه
"""

import asyncio
import json
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

_backtest_lock = asyncio.Lock()

_EMPTY_RESULT = {
    "ok": False,
    "reason": "already_running",
    "checked": 0,
    "updated": 0,
    "expired": 0,
    "win": 0,
    "loss": 0,
}

# ═══════════════════════════════════════════════════════════
# 🎯 نمادهای ثابت برای اسکن خودکار
# ═══════════════════════════════════════════════════════════
# فقط این نمادها + واچ‌لیست کاربر اسکن می‌شن
FIXED_WATCH_SYMBOLS = [
    # بیت‌کوین
    {"ticker": "BTC-USD", "source": "nobitex", "name": "بیت‌کوین (USDT)"},
    {"ticker": "BTC-IRT", "source": "nobitex", "name": "بیت‌کوین (تومان)"},
    # پکس گلد
    {"ticker": "PAXG-USD", "source": "nobitex", "name": "پکس گلد (USDT)"},
    {"ticker": "PAXG-IRT", "source": "nobitex", "name": "پکس گلد (تومان)"},
]

# ─── TF و پروفایل ثابت برای اسکن خودکار ───
SCAN_TIMEFRAME = "۳۰ دقیقه"  # ← تو گفتی ۳۰ دقیقه جسورانه
SCAN_RISK_PROFILE = "aggressive"
SCAN_MARKET_TYPE = "futures"


# ═══════════════════════════════════════════════════════════
# واچ‌لیست — از فایل یا DB
# ═══════════════════════════════════════════════════════════
def _load_watchlist_from_file() -> list[dict]:
    """
    واچ‌لیست رو از فایل می‌خونه.

    ⚠️ در فاز بعدی، از DB کاربر می‌خونیم.
    فعلاً یه فایل JSON ساده در /opt/trademun/data/watchlist.json
    """
    path = Path("/app/data/watchlist.json")

    # ─── اگه روی لوکال هستیم ───
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "data" / "watchlist.json"

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # ─── فقط کریپتو (نماد ASCII) ───
        result = []
        for item in data:
            ticker = item.get("ticker", "")
            if not ticker:
                continue

            # ─── فیلتر: فقط ASCII (کریپتو) ───
            if not ticker[0].isascii():
                continue

            result.append(
                {
                    "ticker": ticker,
                    "source": item.get("source", "nobitex"),
                    "name": item.get("name", ticker),
                }
            )

        return result
    except Exception as e:
        logger.warning(f"[AutoScan] خطا در خواندن واچ‌لیست: {e!r}")
        return []


async def check_pending_signals(trigger: str = "scheduler") -> dict:
    """بررسی سیگنال‌های در انتظار راستی‌آزمایی."""
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان است — رد شد")
        return dict(_EMPTY_RESULT)

    async with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌های در انتظار...")
        try:
            result = await asyncio.to_thread(backtest_all, 200)

            updated = result.get("updated", 0)
            if updated > 0:
                logger.info(
                    f"[Backtest/{trigger}] ✅ {updated} به‌روز شد "
                    f"(win={result.get('win', 0)}, "
                    f"loss={result.get('loss', 0)}, "
                    f"expired={result.get('expired', 0)}, "
                    f"errors={result.get('errors', 0)})"
                )
            else:
                logger.info(
                    f"[Backtest/{trigger}] {result.get('checked', 0)} بررسی شد، "
                    f"تغییری نبود"
                )
            return {"ok": True, **result}

        except Exception as e:
            logger.exception(f"[Backtest/{trigger}] خطای غیرمنتظره")
            return {
                "ok": False,
                "reason": str(e),
                "checked": 0,
                "updated": 0,
                "expired": 0,
                "win": 0,
                "loss": 0,
            }


async def auto_scan_and_record(trigger: str = "scheduler"):
    """
    اسکن خودکار + ثبت سیگنال‌ها — نسخه ۳.۰.

    ═══ تغییرات نسخه ۳.۰ ═══
    • فقط نمادهای ثابت + واچ‌لیست اسکن می‌شن (نه همه ۲۰ نماد صرافی)
    • فقط ۱ TF + ۱ پروفایل (نه ۳ TF × ۲ پروفایل)
    • نتیجه: از ~۱۲۰ رکورد در هر اسکن → ~۶ رکورد
    """
    logger.info(f"[AutoScan/{trigger}] شروع اسکن خودکار...")

    try:
        from services.analyzer_service import analyze

        # ═══ جمع‌آوری نمادها ═══
        fixed = list(FIXED_WATCH_SYMBOLS)
        watchlist = _load_watchlist_from_file()

        # ═══ ادغام بدون تکرار ═══
        seen: set[str] = set()
        all_symbols: list[dict] = []

        for s in fixed + watchlist:
            key = s["ticker"]
            if key in seen:
                continue
            seen.add(key)
            all_symbols.append(s)

        logger.info(
            f"[AutoScan/{trigger}] نمادهای هدف: "
            f"{len(fixed)} ثابت + {len(watchlist)} واچ‌لیست "
            f"= {len(all_symbols)} نماد"
        )

        total_recorded = 0
        total_errors = 0

        for sym in all_symbols:
            ticker = sym["ticker"]
            source = sym["source"]
            name = sym["name"]

            try:
                r = await asyncio.to_thread(
                    analyze,
                    ticker=ticker,
                    source=source,
                    tf_name=SCAN_TIMEFRAME,
                    market_type=SCAN_MARKET_TYPE,
                    risk_profile=SCAN_RISK_PROFILE,
                    ticker_name=name,
                    include_extras=False,
                    skip_record=False,
                )
                if r and r.get("signal") != "خنثی":
                    total_recorded += 1
            except Exception as e:
                logger.debug(f"[AutoScan] {ticker}: {e}")
                total_errors += 1

        logger.info(
            f"[AutoScan/{trigger}] ✅ {total_recorded} سیگنال جدید "
            f"از {len(all_symbols)} نماد (خطا: {total_errors})"
        )
        return {
            "ok": True,
            "recorded": total_recorded,
            "symbols_scanned": len(all_symbols),
            "errors": total_errors,
        }

    except Exception as e:
        logger.exception(f"[AutoScan/{trigger}] خطا")
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# start_scheduler واحد
# ═══════════════════════════════════════════════════════════
def start_scheduler():
    """راه‌اندازی scheduler با هر دو job."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال (SCHEDULER_ENABLED=false)")
        return

    if scheduler.running:
        logger.debug("[Scheduler] از قبل در حال اجراست")
        return

    # ═══ job ۱: راستی‌آزمایی سیگنال‌ها ═══
    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=settings.BACKTEST_INTERVAL_MINUTES),
        id="check_pending_signals",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        kwargs={"trigger": "scheduler"},
    )

    # ═══ job ۲: اسکن خودکار ═══
    scheduler.add_job(
        auto_scan_and_record,
        IntervalTrigger(minutes=60),
        id="auto_scan_and_record",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        kwargs={"trigger": "scheduler"},
    )

    scheduler.start()
    logger.info(
        f"[Scheduler] ✅ فعال — راستی‌آزمایی هر "
        f"{settings.BACKTEST_INTERVAL_MINUTES} دقیقه + "
        f"اسکن خودکار هر ۶۰ دقیقه (فقط {len(FIXED_WATCH_SYMBOLS)} نماد ثابت + واچ‌لیست)"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
