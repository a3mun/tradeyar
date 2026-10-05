"""
tests/test_cache_fingerprint.py
تست باگ ۸ — کش fingerprint از کندل بسته
============================================================
مسئله:  fingerprint از ``df.iloc[-1]`` (کندل **باز**) ساخته می‌شد.
        Close آن هر ثانیه عوض می‌شود، پس هش هر بار متفاوت بود و
        کش **هیچ‌وقت hit نمی‌شد** — یعنی ~۲۰ اندیکاتور در هر
        درخواست از صفر محاسبه می‌شد.

تست کاربر:
    ۱. analyze دوبار پشت هم → fingerprint یکی بمونه
    ۲. بعد ۵ دقیقه (کندل جدید) → fingerprint عوض بشه
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from services.cache import (
    TF_SECONDS,
    closed_candles,
    is_candle_closed,
    make_fingerprint,
)

UTC = timezone.utc

# ─── زمان مرجع ثابت ───
NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)


def _frame(
    n: int = 5,
    *,
    tf_minutes: int = 5,
    end: datetime = NOW,
    closes: list[float] | None = None,
) -> pd.DataFrame:
    """
    ساخت دیتافریم با n کندل که **آخرین کندل باز است** (شروعش = end).
    """
    idx = [end - timedelta(minutes=tf_minutes * (n - i)) for i in range(n)]
    idx[-1] = end  # ─── آخرین کندل همین الان شروع شده → باز ───
    c = closes if closes is not None else [100.0 + i for i in range(n)]
    return pd.DataFrame(
        {"open": c, "high": c, "low": c, "close": c, "volume": [1.0] * n},
        index=pd.DatetimeIndex(idx),
    )


# ═══════════════════════════════════════════════════════════
# ۱. تشخیص کندل باز/بسته
# ═══════════════════════════════════════════════════════════
class TestCandleClosedDetection:
    def test_candle_within_tf_is_open(self):
        """کندلی که همین الان شروع شده، باز است"""
        assert is_candle_closed(NOW, "۵ دقیقه", now=NOW) is False

    def test_candle_older_than_tf_is_closed(self):
        """کندلی که ۵ دقیقه پیش شروع شده، بسته است"""
        assert is_candle_closed(NOW - timedelta(minutes=5), "۵ دقیقه", now=NOW) is True

    def test_boundary_is_closed(self):
        """دقیقاً روی مرز — بسته است (شرط <=)"""
        t = NOW - timedelta(seconds=TF_SECONDS["۵ دقیقه"])
        assert is_candle_closed(t, "۵ دقیقه", now=NOW) is True

    def test_one_second_before_boundary_is_open(self):
        t = NOW - timedelta(seconds=TF_SECONDS["۵ دقیقه"] - 1)
        assert is_candle_closed(t, "۵ دقیقه", now=NOW) is False

    @pytest.mark.parametrize(
        "tf,sec",
        [
            ("۱ دقیقه", 60),
            ("۵ دقیقه", 300),
            ("۱۵ دقیقه", 900),
            ("۳۰ دقیقه", 1800),
            ("۱ ساعت", 3600),
            ("روزانه", 86400),
        ],
    )
    def test_tf_seconds_correct(self, tf, sec):
        assert TF_SECONDS[tf] == sec

    def test_naive_datetime_treated_as_utc(self):
        """datetime بدون tz باید UTC فرض شود"""
        naive = (NOW - timedelta(minutes=10)).replace(tzinfo=None)
        assert is_candle_closed(naive, "۵ دقیقه", now=NOW) is True

    def test_unknown_tf_uses_default(self):
        """TF ناشناخته نباید کرش کند"""
        assert is_candle_closed(NOW - timedelta(minutes=10), "ناشناخته", now=NOW) is True


class TestClosedCandles:
    def test_drops_last_open_candle(self):
        df = _frame(5)
        closed = closed_candles(df, "۵ دقیقه", now=NOW)
        assert len(closed) == 4
        assert closed.index[-1] == df.index[-2]

    def test_all_closed_keeps_all(self):
        """اگر همه بسته باشند، هیچی حذف نمی‌شود"""
        idx = pd.date_range(NOW - timedelta(hours=2), periods=5, freq="5min", tz="UTC")
        df = pd.DataFrame(
            {"open": [1.0] * 5, "high": [1.0] * 5, "low": [1.0] * 5,
             "close": [1.0] * 5, "volume": [1.0] * 5},
            index=pd.DatetimeIndex(idx),
        )
        # ─── آخرین کندل ۲ ساعت پیش شروع شده → قطعاً بسته ───
        assert len(closed_candles(df, "۵ دقیقه", now=NOW)) == 5

    def test_all_open_returns_empty(self):
        """اگر همه باز باشند، نتیجه خالی است"""
        idx = [NOW + timedelta(seconds=i) for i in range(3)]
        df = pd.DataFrame(
            {"open": [1.0] * 3, "high": [1.0] * 3, "low": [1.0] * 3,
             "close": [1.0] * 3, "volume": [1.0] * 3},
            index=pd.DatetimeIndex(idx),
        )
        assert closed_candles(df, "۵ دقیقه", now=NOW).empty

    def test_daily_drops_todays_open_candle(self):
        """کندل روزانه‌ی امروز باز است و باید حذف شود"""
        idx = [NOW - timedelta(days=4 - i) for i in range(5)]
        df = pd.DataFrame(
            {"open": [1.0] * 5, "high": [1.0] * 5, "low": [1.0] * 5,
             "close": [1.0] * 5, "volume": [1.0] * 5},
            index=pd.DatetimeIndex(idx),
        )
        closed = closed_candles(df, "روزانه", now=NOW)
        assert len(closed) == 4, "کندل امروز باید حذف شود"

    def test_none_and_empty_safe(self):
        assert closed_candles(None, "۵ دقیقه") is None
        assert closed_candles(pd.DataFrame(), "۵ دقیقه").empty


# ═══════════════════════════════════════════════════════════
# ۲. 🔴 تست کاربر — پایداری
# ═══════════════════════════════════════════════════════════
class TestFingerprintStability:
    def test_open_candle_close_does_not_affect_fingerprint(self):
        """
        🔴 قلب باگ ۸:
        تغییر close کندل **باز** نباید fingerprint را عوض کند.

        پیش از اصلاح: عوض می‌شد → cache miss در هر درخواست.
        """
        df1 = _frame(5)
        df2 = df1.copy()
        df2.iloc[-1, df2.columns.get_loc("close")] = 99999.0
        df2.iloc[-1, df2.columns.get_loc("high")] = 99999.0

        fp1 = make_fingerprint(df1, "۵ دقیقه", now=NOW)
        fp2 = make_fingerprint(df2, "۵ دقیقه", now=NOW)

        assert fp1 == fp2, (
            f"fingerprint با تغییر کندل باز عوض شد — باگ ۸ برگشته\n"
            f"  {fp1} != {fp2}"
        )

    def test_repeated_calls_are_idempotent(self):
        """🔴 تست کاربر: analyze دوبار پشت هم → fingerprint یکی"""
        df = _frame(5)
        hashes = {make_fingerprint(df, "۵ دقیقه", now=NOW) for _ in range(50)}
        assert len(hashes) == 1, f"{len(hashes)} هش متفاوت — ناپایدار"

    def test_many_ticks_within_candle_are_stable(self):
        """
        🔴 شبیه‌سازی ۳۰۰ تیک قیمت در طول یک کندل:
        fingerprint باید ثابت بماند.
        """
        hashes = set()
        for tick in range(300):
            df = _frame(5)
            # ─── کندل باز با قیمت در حال تغییر ───
            df.iloc[-1, df.columns.get_loc("close")] = 100.0 + tick * 0.01
            df.iloc[-1, df.columns.get_loc("high")] = 100.0 + tick * 0.01
            hashes.add(make_fingerprint(df, "۵ دقیقه", now=NOW))

        assert len(hashes) == 1, f"{len(hashes)} هش در ۳۰۰ تیک — کش بی‌فایده"


# ═══════════════════════════════════════════════════════════
# ۳. 🔴 تست کاربر — تغییر با کندل جدید
# ═══════════════════════════════════════════════════════════
class TestFingerprintChangesOnNewCandle:
    def test_new_candle_changes_fingerprint(self):
        """
        🔴 تست کاربر: بعد ۵ دقیقه (کندل جدید) → fingerprint عوض شود.
        """
        df_before = _frame(5, end=NOW)
        fp_before = make_fingerprint(df_before, "۵ دقیقه", now=NOW)

        # ─── ۵ دقیقه جلو: کندل 12:00 بسته، کندل 12:05 باز ───
        later = NOW + timedelta(minutes=5)
        df_after = _frame(6, end=later)
        fp_after = make_fingerprint(df_after, "۵ دقیقه", now=later)

        assert fp_before != fp_after, "fingerprint با کندل جدید عوض نشد"

    def test_new_closed_candle_close_changes_fingerprint(self):
        """تغییر close کندل تازه بسته‌شده هم باید هش را عوض کند"""
        df_before = _frame(5, end=NOW)
        fp_before = make_fingerprint(df_before, "۵ دقیقه", now=NOW)

        later = NOW + timedelta(minutes=5)
        df_after = _frame(6, end=later)
        # ─── close کندل 12:00 (که حالا بسته است) را عوض کن ───
        df_after.iloc[-2, df_after.columns.get_loc("close")] = 777.0
        fp_after = make_fingerprint(df_after, "۵ دقیقه", now=later)

        assert fp_before != fp_after, "close کندل بسته در هش اثر ندارد"

    @pytest.mark.parametrize(
        "tf,advance",
        [
            ("۱ دقیقه", 1),
            ("۵ دقیقه", 5),
            ("۱۵ دقیقه", 15),
            ("۳۰ دقیقه", 30),
            ("۱ ساعت", 60),
        ],
    )
    def test_fingerprint_changes_after_one_tf_period(self, tf, advance):
        """برای هر TF، با گذر یک دوره هش باید عوض شود"""
        tf_min = advance
        df_before = _frame(6, tf_minutes=tf_min, end=NOW)
        fp_before = make_fingerprint(df_before, tf, now=NOW)

        later = NOW + timedelta(minutes=advance)
        df_after = _frame(7, tf_minutes=tf_min, end=later)
        fp_after = make_fingerprint(df_after, tf, now=later)

        assert fp_before != fp_after, f"{tf}: هش عوض نشد"


# ═══════════════════════════════════════════════════════════
# ۴. حالت‌های مرزی
# ═══════════════════════════════════════════════════════════
class TestFingerprintEdgeCases:
    def test_none_returns_empty(self):
        assert make_fingerprint(None, "۵ دقیقه") == "empty"

    def test_empty_df_returns_empty(self):
        assert make_fingerprint(pd.DataFrame(), "۵ دقیقه") == "empty"

    def test_single_candle_returns_empty(self):
        """با یک کندل، هش پایدار ممکن نیست"""
        df = _frame(1)
        assert make_fingerprint(df, "۵ دقیقه", now=NOW) == "empty"

    def test_only_open_candles_returns_empty(self):
        """اگر همه باز باشند، کندل بسته‌ای نیست"""
        df = _frame(3, end=NOW)
        df.index = pd.DatetimeIndex([NOW + timedelta(seconds=i) for i in range(3)])
        assert make_fingerprint(df, "۵ دقیقه", now=NOW) == "empty"

    def test_naive_index_handled(self):
        """ایندکس بدون tz نباید کرش کند"""
        df = _frame(5)
        df.index = df.index.tz_localize(None)
        fp = make_fingerprint(df, "۵ دقیقه", now=NOW)
        assert fp and fp not in ("empty", "error")

    def test_unknown_tf_does_not_crash(self):
        df = _frame(5)
        fp = make_fingerprint(df, "نامعلوم", now=NOW)
        assert fp and fp != "error"

    def test_fingerprint_length(self):
        df = _frame(5)
        assert len(make_fingerprint(df, "۵ دقیقه", now=NOW)) == 12


# ═══════════════════════════════════════════════════════════
# ۵. یکپارچگی با analyze — کش واقعاً hit می‌شود
# ═══════════════════════════════════════════════════════════
class TestAnalyzeCacheHit:
    def test_analyze_calls_analyze_symbol_once_within_candle(self):
        """
        🔴 تست نهایی: دو ``analyze`` در یک کندل باید فقط **یک بار**
        ``analyze_symbol`` را صدا بزنند (کش hit).
        """
        from services import analyzer_service as svc
        from services.cache import analysis_cache

        analysis_cache.clear()
        df = _frame(60, end=NOW)

        calls = {"n": 0}
        real = svc.analyze_symbol

        def counting(*args, **kwargs):
            calls["n"] += 1
            return real(*args, **kwargs)

        with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df), \
             patch.object(svc, "analyze_symbol", counting), \
             patch.object(svc, "make_fingerprint",
                          lambda d, tf, **kw: make_fingerprint(d, tf, now=NOW)):

            r1 = svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")
            n_after_first = calls["n"]

            r2 = svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")
            n_after_second = calls["n"]

        assert n_after_first == 1, f"تحلیل اول {n_after_first} بار محاسبه شد"
        assert n_after_second == 1, (
            f"تحلیل دوم **دوباره** محاسبه شد ({n_after_second} بار کل) — "
            f"کش hit نمی‌شود"
        )
        assert r1 is not None and r2 is not None

    def test_cached_response_has_fresh_price(self):
        """
        🔴 با cache hit، قیمت باید تازه باشد (نه کهنه).

        تحلیل سنگین کش می‌شود، ولی قیمت کندل جاری در هر درخواست
        تازه خوانده می‌شود.
        """
        from services import analyzer_service as svc
        from services.cache import analysis_cache

        analysis_cache.clear()
        df_old = _frame(60, end=NOW)
        fp = make_fingerprint(df_old, "۵ دقیقه", now=NOW)

        with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df_old), \
             patch.object(svc, "make_fingerprint", lambda d, tf, **kw: fp):
            svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")

            # ─── حالا قیمت عوض شده ولی fingerprint همان است ───
            df_new = df_old.copy()
            df_new.iloc[-1, df_new.columns.get_loc("close")] = 555555.0
            with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df_new):
                r2 = svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")

        assert r2 is not None
        assert r2["price"] == 555555.0, (
            f"قیمت کهنه برگشت: {r2['price']} — باید 555555.0 باشد"
        )

    def test_cache_hit_returns_copy_not_reference(self):
        """نتیجه‌ی کش نبایددر جای خود تغییر کند"""
        from services import analyzer_service as svc
        from services.cache import analysis_cache

        analysis_cache.clear()
        df = _frame(60, end=NOW)
        fp = make_fingerprint(df, "۵ دقیقه", now=NOW)

        with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df), \
             patch.object(svc, "make_fingerprint", lambda d, tf, **kw: fp):
            r1 = svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")
            price1 = r1["price"]

            df2 = df.copy()
            df2.iloc[-1, df2.columns.get_loc("close")] = 777777.0
            with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df2):
                r2 = svc.analyze("BTC-USD", "nobitex", "۵ دقیقه", "futures")

        assert r2["price"] == 777777.0
        # ─── r1 دست‌نخورده بماند ───
        assert r1["price"] == price1, "نتیجه‌ی قبلی تغییر کرد (کپی سطحی نبود)"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
