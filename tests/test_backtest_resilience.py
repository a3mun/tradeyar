"""
tests/test_backtest_resilience.py
تست باگ ۷ — مقاوم‌بودن backtest_all
============================================================
مسئله:  خطای یک سیگنال، نتایج **همه‌ی** batch را از بین می‌برد
        و همان سیگنال در اجرای بعدی هم خطا می‌داد → بن‌بست دائمی.

تست کاربر:
    _check_one با یه ticker نامعتبر → بقیه continue بشن
"""

import logging
from datetime import timedelta

import pytest
from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from core.tz import utc_now

TEST_PREFIX = "ZZBT"


@pytest.fixture(autouse=True)
def _cleanup():
    """حذف ردیف‌های تست"""

    def _purge():
        with Session(engine) as s:
            for row in s.exec(
                select(SignalLog).where(SignalLog.ticker.like(f"{TEST_PREFIX}%"))
            ).all():
                s.delete(row)
            s.commit()

    _purge()
    yield
    _purge()


def _seed(n: int, *, tf: str = "۵ دقیقه", age_minutes: int = 10) -> list[int]:
    """
    ساخت n سیگنال در انتظار و برگرداندن idهایشان.

    age_minutes: چند دقیقه قبل ثبت شده‌اند (باید کمتر از timeout باشد)
    """
    ts = utc_now() - timedelta(minutes=age_minutes)
    ids = []
    with Session(engine) as s:
        for i in range(n):
            log = SignalLog(
                ticker=f"{TEST_PREFIX}-{i}",
                name=f"Test {i}",
                signal="LONG",
                direction="long",
                price=100.0,
                sl=95.0,
                tp=110.0,
                tf=tf,
                source="nobitex",
                market_type="futures",
                risk_profile="aggressive",
                timestamp=ts,
            )
            s.add(log)
        s.commit()
        for row in s.exec(
            select(SignalLog).where(SignalLog.ticker.like(f"{TEST_PREFIX}%"))
        ).all():
            ids.append(row.id)
    return ids


def _results() -> list[str | None]:
    with Session(engine) as s:
        rows = s.exec(
            select(SignalLog)
            .where(SignalLog.ticker.like(f"{TEST_PREFIX}%"))
            .order_by(SignalLog.id)
        ).all()
    return [r.result for r in rows]


# ═══════════════════════════════════════════════════════════
# ۱. 🔴 تست کاربر
# ═══════════════════════════════════════════════════════════
class TestOneBadSignalDoesNotKillBatch:
    def test_error_in_middle_others_still_processed(self, monkeypatch):
        """
        🔴 تست کاربر:
        ۸ سیگنال؛ سیگنال چهارم خطا می‌دهد. ۷ تای دیگر باید
        پردازش و **commit** شوند.
        """
        import services.backtest_service as bs

        _seed(8)

        call = {"n": 0}
        real = bs._check_one

        def flaky(log):
            call["n"] += 1
            if call["n"] == 4:
                raise RuntimeError("ticker نامعتبر — boom")
            return real(log)

        # ─── fetch را mock کن تا شبیه‌سازی قطعی باشد ───
        import pandas as pd

        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)
        monkeypatch.setattr(bs, "_check_one", flaky)

        r = bs.backtest_all()

        assert r["checked"] == 8, f"انتظار ۸ بررسی، گرفت {r['checked']}"
        assert r["errors"] == 1, f"انتظار ۱ خطا، گرفت {r['errors']}"
        assert r["updated"] == 7, f"انتظار ۷ به‌روز، گرفت {r['updated']}"
        assert r["win"] == 7

        # ─── 🔴 نتایج باید در دیتابیس باشند، نه فقط در شمارنده ───
        stored = _results()
        assert stored.count("win") == 7, f"در دیتابیس: {stored}"
        assert stored.count(None) == 1, "سیگنال خطادار باید در انتظار بماند"

    def test_first_signal_error_others_processed(self, monkeypatch):
        """خطا در اولین سیگنال هم بقیه را متوقف نمی‌کند"""
        import pandas as pd

        import services.backtest_service as bs

        _seed(5)
        call = {"n": 0}
        real = bs._check_one

        def flaky(log):
            call["n"] += 1
            if call["n"] == 1:
                raise ValueError("اولی خراب")
            return real(log)

        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)
        monkeypatch.setattr(bs, "_check_one", flaky)

        r = bs.backtest_all()
        assert r["errors"] == 1
        assert r["updated"] == 4, f"گرفت {r}"

    def test_all_signals_error_no_crash(self, monkeypatch):
        """همه خطا بدهند → هیچ commit، ولی کرش هم نه"""
        import services.backtest_service as bs

        _seed(4)
        monkeypatch.setattr(
            bs, "_check_one", lambda log: (_ for _ in ()).throw(RuntimeError("x"))
        )

        r = bs.backtest_all()
        assert r["checked"] == 4
        assert r["errors"] == 4
        assert r["updated"] == 0
        assert all(x is None for x in _results())

    def test_invalid_ticker_is_skipped_gracefully(self, monkeypatch):
        """
        🔴 tester کاربر: ticker نامعتبر نباید batch را بشکند.
        ``fetch_ohlcv`` برای آن None می‌دهد → نتیجه None، نه خطا.
        """
        import services.backtest_service as bs

        _seed(3)

        def fetch(ticker, *a, **k):
            if "ZZBT-1" in ticker:
                return None  # ─── ticker نامعتبر ───
            import pandas as pd

            return pd.DataFrame(
                {
                    "open": [100.0],
                    "high": [111.0],
                    "low": [99.0],
                    "close": [105.0],
                    "volume": [1.0],
                },
                index=pd.date_range(
                    (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                    periods=1,
                    tz="UTC",
                ),
            )

        monkeypatch.setattr(bs, "fetch_ohlcv", fetch)
        r = bs.backtest_all()

        assert r["checked"] == 3
        assert r["errors"] == 0, "None برگرداندن خطا نیست"
        assert r["updated"] == 2


# ═══════════════════════════════════════════════════════════
# ۲. commit تدریجی — کار انجام‌شده از دست نرود
# ═══════════════════════════════════════════════════════════
class TestIncrementalCommit:
    def test_partial_results_persisted_before_later_error(self, monkeypatch):
        """
        🔴 نتایج سیگنال‌های موفق باید commit شوند، حتی اگر
        سیگنال‌های بعدی خطا بدهند.

        پیش از اصلاح: commit در **پایان** batch بود، پس خطا
        همه‌چیز را از بین می‌برد.
        """
        import pandas as pd

        import services.backtest_service as bs

        _seed(6)

        call = {"n": 0}
        real = bs._check_one

        def fail_after_three(log):
            call["n"] += 1
            if call["n"] > 3:
                raise RuntimeError("از چهارمی به بعد خطا")
            return real(log)

        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)
        monkeypatch.setattr(bs, "_check_one", fail_after_three)

        r = bs.backtest_all()
        assert r["updated"] == 3
        assert r["errors"] == 3

        # ─── 🔴 ۳ نتیجه باید واقعاً در دیتابیس باشند ───
        stored = _results()
        assert stored.count("win") == 3, (
            f"نتایج commit نشدند — در دیتابیس: {stored}"
        )

    def test_next_run_does_not_recheck_completed(self, monkeypatch):
        """
        اجرای دوم نباید سیگنال‌های پردازش‌شده را دوباره بررسی کند
        (اثبات اینکه commit واقعاً انجام شده).
        """
        import pandas as pd

        import services.backtest_service as bs

        _seed(4)

        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)

        r1 = bs.backtest_all()
        assert r1["updated"] == 4

        r2 = bs.backtest_all()
        assert r2["checked"] == 0, (
            f"اجرای دوم {r2['checked']} سیگنال را دوباره بررسی کرد — commit نشده"
        )


# ═══════════════════════════════════════════════════════════
# ۳. بن‌بست دائمی از بین رفته
# ═══════════════════════════════════════════════════════════
class TestNoPermanentDeadlock:
    def test_queue_makes_progress_across_runs(self, monkeypatch):
        """
        🔴 سناریوی بن‌بست پیشین:
        سیگنال خراب همیشه خطا می‌دهد. پیش از اصلاح، چون هیچ‌چیز
        commit نمی‌شد، صف هرگز جلو نمی‌رفت و سیگنال‌های سالم
        هرگز پردازش نمی‌شدند.

        حالا: سیگنال خراب رد می‌شود، بقیه پیش می‌روند.
        """
        import pandas as pd

        import services.backtest_service as bs

        _seed(5)
        broken_ticker = f"{TEST_PREFIX}-2"  # ─── این همیشه خطا می‌دهد ───
        real = bs._check_one

        def always_broken_for_one(log):
            # ─── تشخیص بر اساس ticker، نه ترتیب (پایدار بین اجراها) ───
            if log.ticker == broken_ticker:
                raise RuntimeError("این همیشه خراب است")
            return real(log)

        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)
        monkeypatch.setattr(bs, "_check_one", always_broken_for_one)

        r1 = bs.backtest_all()
        assert r1["updated"] == 4, f"اجرای اول: {r1}"

        # ─── اجرای دوم: فقط سیگنال خراب می‌ماند ───
        r2 = bs.backtest_all()
        assert r2["checked"] == 1, (
            f"اجرای دوم باید فقط ۱ سیگنال خراب را ببیند، دید {r2['checked']}"
        )
        assert r2["errors"] == 1

        # ─── صف باید جلو رفته باشد ───
        assert _results().count("win") == 4


# ═══════════════════════════════════════════════════════════
# ۴. شمارنده‌ها و خروجی
# ═══════════════════════════════════════════════════════════
class TestResultCounters:
    def test_all_counters_present(self):
        """
        🔴 پیش از این فقط checked/updated/expired/win/loss بود؛
        الان errors و skipped هم لازم است تا scheduler بتواند
        وضعیت را گزارش کند.
        """
        import services.backtest_service as bs

        r = bs.backtest_all(max_checks=0)
        for key in ("checked", "updated", "expired", "win", "loss", "errors", "skipped"):
            assert key in r, f"شمارنده‌ی {key} غایب است: {r}"

    def test_empty_queue_returns_zeros(self):
        import services.backtest_service as bs

        r = bs.backtest_all()
        assert r["checked"] == 0
        assert r["errors"] == 0
        assert r["skipped"] == 0

    def test_max_checks_respected(self, monkeypatch):
        import pandas as pd

        import services.backtest_service as bs

        _seed(10)
        candles = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [111.0] * 3,
                "low": [99.0] * 3,
                "close": [105.0] * 3,
                "volume": [1.0] * 3,
            },
            index=pd.date_range(
                (utc_now() - timedelta(minutes=9)).replace(tzinfo=None),
                periods=3,
                freq="1min",
                tz="UTC",
            ),
        )
        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)

        r = bs.backtest_all(max_checks=4)
        assert r["checked"] == 4, f"max_checks رعایت نشد: {r}"

    def test_expired_signals_counted(self, monkeypatch):
        """سیگنال قدیمی → expired، بدون fetch"""
        import services.backtest_service as bs

        # ─── ۲۰ روز قبل، timeout «۵ دقیقه» = ۲ ساعت ───
        _seed(3, age_minutes=20 * 24 * 60)

        called = {"n": 0}

        def should_not_be_called(*a, **k):
            called["n"] += 1
            return None

        monkeypatch.setattr(bs, "fetch_ohlcv", should_not_be_called)

        r = bs.backtest_all()
        assert r["expired"] == 3, f"گرفت {r}"
        assert called["n"] == 0, "برای سیگنال منقضی نباید fetch بزند"


# ═══════════════════════════════════════════════════════════
# ۵. scheduler با نتایج خطادار
# ═══════════════════════════════════════════════════════════
class TestSchedulerHandlesErrors:
    @pytest.mark.anyio
    async def test_scheduler_reports_errors_in_log(self, caplog, monkeypatch):
        """scheduler باید errors را در لاگ بیاورد"""
        import services.backtest_service as bs
        from api.scheduler import check_pending_signals

        monkeypatch.setattr(
            bs,
            "backtest_all",
            lambda max_checks=200: {
                "checked": 5,
                "updated": 2,
                "expired": 0,
                "win": 2,
                "loss": 0,
                "errors": 3,
                "skipped": 0,
            },
        )

        # ─── scheduler ماژول را هم patch کن ───
        import api.scheduler as sched

        monkeypatch.setattr(
            sched,
            "backtest_all",
            lambda max_checks=200: {
                "checked": 5,
                "updated": 2,
                "expired": 0,
                "win": 2,
                "loss": 0,
                "errors": 3,
                "skipped": 0,
            },
        )

        with caplog.at_level(logging.INFO, logger="api.scheduler"):
            r = await check_pending_signals("test")

        assert r["ok"] is True
        assert r["errors"] == 3
        assert any("errors=3" in rec.message for rec in caplog.records), (
            f"errors در لاگ نیامد: {[x.message for x in caplog.records]}"
        )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
