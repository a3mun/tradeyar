"""
tests/test_signal_recorder.py
تست باگ ۵ — چک تکراری با منبع
============================================================
پوشش:
  ۱. تست کاربر: دو بار BTC-USD با source نوبیتکس و بیت‌پین → هر دو ثبت
  ۲. تکراری واقعی (همه‌ی پارامترها یکسان) → فقط یکی
  ۳. تفکیک بر اساس market_type
  ۴. تفکیک بر اساس risk_profile
  ۵. تفکیک بر اساس tf و signal
  ۶. race condition — UniqueConstraint جلوی درج هم‌زمان را می‌گیرد
  ۷. اعتبارسنجی ورودی (سیگنال خنثی، قیمت نامعتبر)
  ۸. الگوی INSERT...OR IGNORE برای جلوگیری از rollback
"""

import threading

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from services.signal_recorder import record_signal

UTC = None

# ─── پیشوند ticker تست‌ها تا با دیتای واقعی قاطی نشود ───
TEST_PREFIX = "ZZTEST"


@pytest.fixture(autouse=True)
def _cleanup():
    """حذف ردیف‌های تست قبل و بعد از هر تست"""
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


def _count(ticker: str) -> int:
    with Session(engine) as s:
        return len(
            s.exec(select(SignalLog).where(SignalLog.ticker == ticker)).all()
        )


def _kwargs(ticker: str, **overrides):
    """پارامترهای پایه‌ی یک سیگنال معتبر"""
    base = dict(
        ticker=ticker,
        name="Test Symbol",
        signal="LONG",
        price=100.0,
        tf_name="۵ دقیقه",
        source="nobitex",
        market_type="futures",
        risk_profile="aggressive",
        sl_tp={"sl": 95.0, "tp": 110.0, "type": "LONG"},
        direction="long",
        confidence=70,
    )
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════
# ۱. 🔴 تست کاربر
# ═══════════════════════════════════════════════════════════
class TestUserScenario:
    def test_same_signal_different_source_both_recorded(self):
        """
        🔴 تست کاربر:
        دو بار BTC-USD با source نوبیتکس و بیت‌پین → هر دو باید ثبت شوند.

        پیش از اصلاح: source در شرط نبود، پس دومی بلوکه می‌شد و
        آمار بک‌تست بیت‌پین همیشه خالی می‌ماند.
        """
        t = f"{TEST_PREFIX}-BTC-USD"

        assert record_signal(**_kwargs(t, source="nobitex")) is True
        assert record_signal(**_kwargs(t, source="bitpin")) is True
        assert record_signal(**_kwargs(t, source="wallex")) is True

        assert _count(t) == 3, f"انتظار ۳ ردیف، گرفت {_count(t)}"

    def test_three_sources_independent(self):
        """هر منبع یک ردیف مستقل"""
        t = f"{TEST_PREFIX}-ETH-USD"
        for src in ["nobitex", "bitpin", "wallex", "abantether"]:
            assert record_signal(**_kwargs(t, source=src)) is True
        assert _count(t) == 4

    def test_sources_do_not_interfere_across_tickers(self):
        """منابع مختلف روی نمادهای مختلف نباید همدیگر را بلوکه کنند"""
        a, b = f"{TEST_PREFIX}-A", f"{TEST_PREFIX}-B"
        assert record_signal(**_kwargs(a, source="nobitex")) is True
        assert record_signal(**_kwargs(b, source="bitpin")) is True
        assert _count(a) == 1 and _count(b) == 1


# ═══════════════════════════════════════════════════════════
# ۲. تکراری واقعی
# ═══════════════════════════════════════════════════════════
class TestRealDuplicate:
    def test_exact_duplicate_blocked(self):
        """همه‌ی پارامترها یکسان → فقط یکی ثبت می‌شود"""
        t = f"{TEST_PREFIX}-DUP"
        assert record_signal(**_kwargs(t)) is True
        assert record_signal(**_kwargs(t)) is False
        assert record_signal(**_kwargs(t)) is False
        assert _count(t) == 1, f"انتظار ۱ ردیف، گرفت {_count(t)}"

    def test_duplicate_different_confidence_still_blocked(self):
        """تفاوت در confidence سیگنال را «متفاوت» نمی‌کند"""
        t = f"{TEST_PREFIX}-CONF"
        assert record_signal(**_kwargs(t, confidence=70)) is True
        assert record_signal(**_kwargs(t, confidence=95)) is False
        assert _count(t) == 1


# ═══════════════════════════════════════════════════════════
# ۳. تفکیک market_type
# ═══════════════════════════════════════════════════════════
class TestMarketTypeSeparation:
    def test_spot_and_futures_both_recorded(self):
        t = f"{TEST_PREFIX}-MKT"
        assert record_signal(**_kwargs(t, market_type="spot")) is True
        assert record_signal(**_kwargs(t, market_type="futures")) is True
        assert _count(t) == 2

    def test_same_market_type_blocked(self):
        t = f"{TEST_PREFIX}-MKT2"
        assert record_signal(**_kwargs(t, market_type="spot")) is True
        assert record_signal(**_kwargs(t, market_type="spot")) is False
        assert _count(t) == 1


# ═══════════════════════════════════════════════════════════
# ۴. تفکیک risk_profile
# ═══════════════════════════════════════════════════════════
class TestRiskProfileSeparation:
    def test_two_profiles_both_recorded(self):
        t = f"{TEST_PREFIX}-RISK"
        assert record_signal(**_kwargs(t, risk_profile="aggressive")) is True
        assert record_signal(**_kwargs(t, risk_profile="conservative")) is True
        assert _count(t) == 2


# ═══════════════════════════════════════════════════════════
# ۵. تفکیک tf و signal
# ═══════════════════════════════════════════════════════════
class TestTfAndSignalSeparation:
    @pytest.mark.parametrize(
        "tf", ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۱ ساعت", "روزانه"]
    )
    def test_different_tf_allowed(self, tf):
        t = f"{TEST_PREFIX}-TF-{tf}"
        assert record_signal(**_kwargs(t, tf_name=tf)) is True
        assert _count(t) == 1

    def test_long_and_short_both_allowed(self):
        t = f"{TEST_PREFIX}-DIR"
        assert record_signal(**_kwargs(t, signal="LONG", direction="long")) is True
        assert (
            record_signal(
                **_kwargs(
                    t,
                    signal="SHORT",
                    direction="short",
                    sl_tp={"sl": 105.0, "tp": 90.0, "type": "SHORT"},
                )
            )
            is True
        )
        assert _count(t) == 2

    def test_long_and_weak_long_blocked_as_same(self):
        """«LONG» و «LONG ضعیف» دو رشته‌ی متفاوت‌اند → هر دو ثبت می‌شوند"""
        t = f"{TEST_PREFIX}-WEAK"
        assert record_signal(**_kwargs(t, signal="LONG")) is True
        assert record_signal(**_kwargs(t, signal="LONG ضعیف")) is True
        assert _count(t) == 2


# ═══════════════════════════════════════════════════════════
# ۶. race condition
# ═══════════════════════════════════════════════════════════
class TestRaceCondition:
    def test_concurrent_same_signal_only_one_row(self):
        """
        🔴 ۱۰ نخ هم‌زمان همان سیگنال را ثبت می‌کنند.
        باید دقیقاً ۱ ردیف ساخته شود (نه خطا، نه تکراری).

        چرا INSERT...OR IGNORE لازم است: اگر ORM ساده INSERT کند،
        نخ بازنده IntegrityError می‌گیرد و session را rollback
        می‌کند — که در یک batch می‌تواند نتایج نخ‌های دیگر را
        هم از بین ببرد.
        """
        t = f"{TEST_PREFIX}-RACE"
        results: list[bool] = []
        errors: list[str] = []
        lock = threading.Lock()

        def worker():
            try:
                r = record_signal(**_kwargs(t))
                with lock:
                    results.append(r)
            except Exception as e:  # pragma: no cover
                with lock:
                    errors.append(repr(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors, f"خطا در نخ‌ها: {errors[:3]}"
        assert results.count(True) == 1, (
            f"انتظار ۱ ثبت موفق، گرفت {results.count(True)}"
        )
        assert _count(t) == 1, f"انتظار ۱ ردیف، گرفت {_count(t)}"

    def test_concurrent_different_sources_all_recorded(self):
        """۸ نخ، ۴ منبع مختلف → ۴ ردیف"""
        t = f"{TEST_PREFIX}-RACE2"
        sources = ["nobitex", "bitpin", "wallex", "abantether"]
        errors: list[str] = []

        def worker(src):
            try:
                record_signal(**_kwargs(t, source=src))
            except Exception as e:  # pragma: no cover
                errors.append(repr(e))

        threads = [
            threading.Thread(target=worker, args=(sources[i % 4],))
            for i in range(8)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors, f"خطا: {errors[:3]}"
        assert _count(t) == 4, f"انتظار ۴ ردیف، گرفت {_count(t)}"


# ═══════════════════════════════════════════════════════════
# ۷. اعتبارسنجی ورودی
# ═══════════════════════════════════════════════════════════
class TestValidation:
    def test_neutral_signal_rejected(self):
        t = f"{TEST_PREFIX}-NEUTRAL"
        assert record_signal(**_kwargs(t, signal="خنثی", direction="neutral")) is False
        assert record_signal(**_kwargs(t, signal="NEUTRAL", direction="neutral")) is False
        assert _count(t) == 0

    @pytest.mark.parametrize("bad_price", [0, -1, None])
    def test_invalid_price_rejected(self, bad_price):
        t = f"{TEST_PREFIX}-PRICE"
        assert record_signal(**_kwargs(t, price=bad_price)) is False
        assert _count(t) == 0

    def test_trap_extraction_from_non_dict_values(self):
        """مقادیر غیر-dict در traps نباید کرش کنند"""
        t = f"{TEST_PREFIX}-TRAP"
        assert (
            record_signal(
                **_kwargs(
                    t,
                    traps={
                        "bull_trap": {"active": False},
                        "bear_trap": {"active": True, "reason": "x"},
                        "weird": "not-a-dict",
                    },
                )
            )
            is True
        )

        with Session(engine) as s:
            row = s.exec(
                select(SignalLog).where(SignalLog.ticker == t)
            ).first()
        assert row is not None
        assert row.had_trap is True
        assert row.trap_type == "bear_trap"


# ═══════════════════════════════════════════════════════════
# ۸. dedup_key و constraint
# ═══════════════════════════════════════════════════════════
class TestDedupKey:
    def test_dedup_key_is_written(self):
        t = f"{TEST_PREFIX}-KEY"
        record_signal(**_kwargs(t, source="bitpin"))
        with Session(engine) as s:
            row = s.exec(select(SignalLog).where(SignalLog.ticker == t)).first()
        assert row is not None and row.dedup_key
        assert row.dedup_key.startswith(t)
        assert "bitpin" in row.dedup_key

    def test_dedup_key_differs_by_source(self):
        t = f"{TEST_PREFIX}-KEY2"
        record_signal(**_kwargs(t, source="nobitex"))
        record_signal(**_kwargs(t, source="bitpin"))
        with Session(engine) as s:
            keys = {
                r.dedup_key
                for r in s.exec(
                    select(SignalLog).where(SignalLog.ticker == t)
                ).all()
            }
        assert len(keys) == 2, "کلید دو منبع باید متفاوت باشد"

    def test_unique_index_exists_in_db(self):
        """UniqueConstraint واقعاً در دیتابیس ساخته شده"""
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='signals_log'"
                )
            ).fetchall()
        names = {r[0] for r in rows}
        assert "uq_signals_log_dedup_key" in names, (
            f"ایندکس یکتا ساخته نشده. ایندکس‌ها: {names}"
        )

    def test_column_exists_in_db(self):
        """ستون dedup_key واقعاً در جدول موجود است"""
        with engine.connect() as conn:
            cols = [
                r[1]
                for r in conn.execute(text("PRAGMA table_info(signals_log)"))
            ]
        assert "dedup_key" in cols, f"ستون موجود نیست. ستون‌ها: {cols}"


# ═══════════════════════════════════════════════════════════
# ۹. migration
# ═══════════════════════════════════════════════════════════
class TestMigration:
    def test_migrate_is_idempotent(self):
        """اجرای دوباره‌ی migration نباید خطا بدهد"""
        from api.database import migrate_db

        first = migrate_db()
        second = migrate_db()

        assert not first["errors"], first["errors"]
        assert not second["errors"], second["errors"]
        # ─── اجرای دوم باید همه را skip کند ───
        assert second["applied"] == [], (
            f"اجرای دوم نباید تغییری بدهد: {second['applied']}"
        )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
