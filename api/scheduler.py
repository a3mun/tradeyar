"""
api/scheduler.py — راستی‌آزمایی و اسکن خودکار
============================================================
نسخه ۴.۰ · فاز ۱۰.۴
🔴 تغییرات:
  • چرخه‌ی صرافی: nobitex → wallex → bitpin → تکرار
  • هر اسکن فقط یک صرافی (کاهش فشار)
  • TF های whitelist: ۱۵m, ۳۰m, ۱h
  • Watchlist از data/watchlist.json
  • فقط ۱۰۰ سیگنال آخر
"""

import asyncio
import json
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
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
# نمادهای هدف
# ═══════════════════════════════════════════════════════════
FIXED_SYMBOLS = [
    # ─── nobitex ───
    {"ticker": "BTC-USD", "name": "بیت‌کوین (USDT)", "source": "nobitex"},
    {"ticker": "ETH-USD", "name": "اتریوم (USDT)", "source": "nobitex"},
    {"ticker": "PAXG-USD", "name": "پکس گلد (USDT)", "source": "nobitex"},
    {"ticker": "BTC-IRT", "name": "بیت‌کوین (تومان)", "source": "nobitex"},
    {"ticker": "PAXG-IRT", "name": "پکس گلد (تومان)", "source": "nobitex"},
    # ─── wallex ───
    {"ticker": "BTC-USDT", "name": "بیت‌کوین (USDT)", "source": "wallex"},
    {"ticker": "ETH-USDT", "name": "اتریوم (USDT)", "source": "wallex"},
    {"ticker": "BTC-TMN", "name": "بیت‌کوین (تومان)", "source": "wallex"},
    # ─── bitpin ───
    {"ticker": "BTC_USDT", "name": "بیت‌کوین (USDT)", "source": "bitpin"},
    {"ticker": "ETH_USDT", "name": "اتریوم (USDT)", "source": "bitpin"},
    {"ticker": "BTC_IRT", "name": "بیت‌کوین (تومان)", "source": "bitpin"},
]


# 🔴 فاز ۱۰.۴ — TF های اسکن (بدون ۱m و ۵m و روزانه)
SCAN_TIMEFRAMES = ["۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"]

SCAN_MARKET_TYPE = "futures"
SCAN_RISK_PROFILE = "aggressive"

# 🔴 چرخه صرافی — هر ۶۰ دقیقه یکی
EXCHANGE_CYCLE = ["nobitex", "wallex", "bitpin"]


def _next_exchange() -> str:
    """
    🔴 فاز ۱۰.۷ — چرخه deterministic (بر اساس ساعت).

    ═══ چرا ═══
    قبلاً شمارنده global بود. اگه سرور restart می‌شد،
    از ۰ شروع می‌شد → ممکنه چند بار nobitex بشه.

    الان: ساعت UTC تعیین می‌کنه. Restart-safe.
      • ساعت ۰  → nobitex
      • ساعت ۱  → wallex
      • ساعت ۲  → bitpin
      • ساعت ۳  → nobitex
      • ...
    """
    hour = datetime.now(timezone.utc).hour
    idx = hour % len(EXCHANGE_CYCLE)
    return EXCHANGE_CYCLE[idx]


def _load_watchlist_from_file() -> list[dict]:
    """خواندن watchlist از data/watchlist.json."""
    path = Path("/app/data/watchlist.json")
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "data" / "watchlist.json"

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        result = []
        for item in data:
            ticker = item.get("ticker", "")
            if not ticker:
                continue
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
        logger.warning(f"[AutoScan] خطا watchlist: {e!r}")
        return []


async def check_pending_signals(trigger: str = "scheduler") -> dict:
    """بررسی سیگنال‌های pending."""
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان — رد شد")
        return dict(_EMPTY_RESULT)

    async with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌ها...")
        try:
            result = await asyncio.to_thread(backtest_all, max_checks=100)
            updated = result.get("updated", 0)
            if updated > 0:
                logger.info(
                    f"[Backtest/{trigger}] ✅ {updated} به‌روز "
                    f"(win={result.get('win', 0)}, "
                    f"loss={result.get('loss', 0)}, "
                    f"exp={result.get('expired', 0)}, "
                    f"errors={result.get('errors', 0)})"
                )
            else:
                logger.info(
                    f"[Backtest/{trigger}] {result.get('checked', 0)} بررسی، تغییری نبود"
                )
            return {"ok": True, **result}
        except Exception as e:
            logger.exception(f"[Backtest/{trigger}] خطا")
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
    اسکن چرخه‌ای — هر بار یک صرافی.

    ═══ تغییرات فاز ۱۰.۵ ═══
    • نمادهای ثابت محدود به BTC/ETH/PAXG (حذف SOL, XRP)
    • چرخه صرافی درست کار می‌کنه (والکس و بیت‌پین هم اسکن می‌شن)
    • Watchlist از فایل خونده می‌شه
    """
    # 🔴 انتخاب صرافی برای این دور
    exchange = _next_exchange()
    logger.info(f"[AutoScan/{trigger}] شروع — صرافی: {exchange}")

    try:
        from services.analyzer_service import analyze

        # ═══ نمادهای ثابت این صرافی ═══
        exchange_fixed = [s for s in FIXED_SYMBOLS if s["source"] == exchange]

        # ═══ Watchlist این صرافی ═══
        exchange_watchlist = [
            w for w in _load_watchlist_from_file() if w["source"] == exchange
        ]

        # ═══ اگه برای این صرافی نمادی نداریم، رد شو ═══
        if not exchange_fixed and not exchange_watchlist:
            logger.info(f"[AutoScan/{trigger}] صرافی {exchange} نمادی نداره — رد")
            return {
                "ok": True,
                "exchange": exchange,
                "recorded": 0,
                "skipped": True,
            }

        # ═══ ادغام بدون تکرار ═══
        seen: set[str] = set()
        all_symbols: list[dict] = []
        for s in exchange_fixed + exchange_watchlist:
            key = f"{s['ticker']}|{s['source']}"
            if key in seen:
                continue
            seen.add(key)
            all_symbols.append(s)

        logger.info(
            f"[AutoScan/{trigger}] {len(all_symbols)} نماد × "
            f"{len(SCAN_TIMEFRAMES)} TF"
        )

        total_recorded = 0
        total_errors = 0

        # ═══ حلقه دوگانه: نماد × TF ═══
        for sym in all_symbols:
            for tf_name in SCAN_TIMEFRAMES:
                try:
                    r = await asyncio.to_thread(
                        analyze,
                        ticker=sym["ticker"],
                        source=sym["source"],
                        tf_name=tf_name,
                        market_type=SCAN_MARKET_TYPE,
                        risk_profile=SCAN_RISK_PROFILE,
                        ticker_name=sym["name"],
                        include_extras=False,
                        skip_record=False,
                    )
                    if r and r.get("signal") != "خنثی":
                        total_recorded += 1
                except Exception as e:
                    logger.debug(f"[AutoScan] {sym['ticker']} {tf_name}: {e!r}")
                    total_errors += 1

                await asyncio.sleep(0.5)

        logger.info(
            f"[AutoScan/{trigger}] ✅ {total_recorded} سیگنال "
            f"از {len(all_symbols)} نماد (خطا: {total_errors})"
        )
        return {
            "ok": True,
            "exchange": exchange,
            "recorded": total_recorded,
            "symbols_scanned": len(all_symbols),
            "errors": total_errors,
        }
    except Exception as e:
        logger.exception(f"[AutoScan/{trigger}] خطا")
        return {"ok": False, "error": str(e)}


def start_scheduler():
    """راه‌اندازی scheduler."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return

    if scheduler.running:
        logger.debug("[Scheduler] از قبل اجراست")
        return

    # ═══ job ۱: راستی‌آزمایی هر ۵ دقیقه ═══
    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=5),
        id="check_pending_signals",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        kwargs={"trigger": "scheduler"},
    )

    # ═══ job ۲: اسکن چرخه‌ای هر ۶۰ دقیقه ═══
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
        "[Scheduler] ✅ راستی‌آزمایی هر ۵ دقیقه + "
        "اسکن چرخه‌ای هر ۶۰ دقیقه (nobitex→wallex→bitpin)"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
