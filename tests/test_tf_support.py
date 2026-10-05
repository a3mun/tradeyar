"""
tests/test_tf_support.py
تست اصلاح TF (نسخه ۱.۶) — حذف سخت‌گیری + اعتبارسنجی بازه
============================================================
پوشش:
  ۱. ``is_ohlcv_supported`` فقط قیدهای قطعی (نه whitelist)
  ۲. ``interval_matches_tf`` — کشف کندل با بازه‌ی اشتباه
  ۳. fallback آگاه از بازه (والکس res=15 → کندل ۱ دقیقه)
  ۴. ردیابی منبع واقعی با ``df.attrs``
  ۵. کش منفی تفکیک‌شده (قطعی ۲۴h در برابر موقت ۵min)
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from core.contracts import (
    TIMEFRAME_SPECS,
    TF_NAMES,
    get_tf_spec,
    is_ohlcv_supported,
    source_lacks_ohlcv,
)
from core.tz import (
    TF_SECONDS,
    dominant_interval_seconds,
    interval_matches_tf,
    interval_mismatch_detail,
)

UTC = timezone.utc


def _df(interval_sec: int, n: int = 20, tz="UTC") -> pd.DataFrame:
    """دیتافریم با بازه‌ی مشخص"""
    idx = pd.date_range("2026-10-01", periods=n, freq=f"{interval_sec}s", tz=tz)
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [1.0] * n,
        },
        index=idx,
    )


# ═══════════════════════════════════════════════════════════
# ۱. قیدهای قطعی (نه whitelist)
# ═══════════════════════════════════════════════════════════
class TestChecksAreConstraintsNotWhitelist:
    def test_nobitex_and_bitpin_unconstrained(self):
        """نوبیتکس و بیت‌پین هیچ قید قطعی ندارند"""
        for src in ("nobitex", "bitpin"):
            for tf in TF_NAMES:
                assert is_ohlcv_supported(tf, src) is True, f"{src}/{tf}"

    def test_wallex_only_30m_blocked(self):
        """
        🔴 اصلاح کلیدی: والکس فقط «۳۰ دقیقه» را قطعاً ندارد.
        بقیه باید اجازه‌ی درخواست بگیرند (پشتیبانی per-نماد).
        """
        assert is_ohlcv_supported("۳۰ دقیقه", "wallex") is False
        for tf in ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۱ ساعت", "روزانه"]:
            assert is_ohlcv_supported(tf, "wallex") is True, (
                f"والکس {tf} نباید قطعاً مسدود شود"
            )

    def test_tsetmc_only_daily(self):
        assert is_ohlcv_supported("روزانه", "tsetmc") is True
        for tf in ["۱ دقیقه", "۵ دقیقه", "۱ ساعت"]:
            assert is_ohlcv_supported(tf, "tsetmc") is False

    def test_tabdeal_no_ohlcv_at_all(self):
        """🔴 تبدیل (Tabdeal) OHLCV عمومی ندارد → همه TFها False"""
        assert source_lacks_ohlcv("tabdeal") is True
        for tf in TF_NAMES:
            assert is_ohlcv_supported(tf, "tabdeal") is False

    def test_abantether_removed(self):
        """🔴 آبان‌تتر در نسخه ۱.۸ حذف شد"""
        assert source_lacks_ohlcv("abantether") is False, (
            "آبان‌تتر دیگر در فهرست منابع نیست"
        )
        assert is_ohlcv_supported("۵ دقیقه", "abantether") is False, (
            "منبع ناشناخته باید False بدهد"
        )

    def test_5m_not_blocked_anywhere(self):
        """
        🔴 رگرسیون هدف: «۵ دقیقه» قبلاً در والکس مسدود می‌شد.
        الان باید اجازه بگیرد.
        """
        for src in ("nobitex", "bitpin", "wallex"):
            assert is_ohlcv_supported("۵ دقیقه", src) is True, src

    def test_15m_not_blocked_in_wallex(self):
        """
        🔴 رگرسیون هدف: «۱۵ دقیقه» در والکس هرگز نباید
        در لایه‌ی پشتیبانی مسدود شود (تصمیم با پاسخ API است).
        """
        assert is_ohlcv_supported("۱۵ دقیقه", "wallex") is True

    def test_unknown_source_and_tf(self):
        assert is_ohlcv_supported("۵ دقیقه", "ناشناخته") is False
        # ─── TF ناشناخته → fail-open ───
        assert is_ohlcv_supported("ناشناخته", "nobitex") is True
        assert is_ohlcv_supported("", "nobitex") is False


# ═══════════════════════════════════════════════════════════
# ۲. اعتبارسنجی بازه‌ی کندل
# ═══════════════════════════════════════════════════════════
class TestIntervalValidation:
    def test_tf_seconds_complete(self):
        """هر ۶ TF باید طول مشخص داشته باشد"""
        assert set(TF_SECONDS) == set(TF_NAMES)
        assert TF_SECONDS["۱ دقیقه"] == 60
        assert TF_SECONDS["۵ دقیقه"] == 300
        assert TF_SECONDS["۱۵ دقیقه"] == 900
        assert TF_SECONDS["۳۰ دقیقه"] == 1800
        assert TF_SECONDS["۱ ساعت"] == 3600
        assert TF_SECONDS["روزانه"] == 86400

    def test_dominant_interval_correct(self):
        for tf, sec in TF_SECONDS.items():
            assert dominant_interval_seconds(_df(sec)) == sec, tf

    def test_dominant_interval_uses_mode_not_mean(self):
        """
        بازار تعطیلات دارد؛ یک شکاف بزرگ نباید میانگین را
        خراب کند. پس مد استفاده می‌شود.
        """
        idx = list(pd.date_range("2026-10-01", periods=10, freq="300s", tz="UTC"))
        # ─── یک شکاف ۳ روزه اضافه کن ───
        idx.append(idx[-1] + timedelta(days=3))
        df = pd.DataFrame(
            {"open": [1.0] * 11, "high": [1.0] * 11, "low": [1.0] * 11,
             "close": [1.0] * 11, "volume": [1.0] * 11},
            index=pd.DatetimeIndex(idx),
        )
        assert dominant_interval_seconds(df) == 300

    def test_dominant_interval_none_for_short_df(self):
        assert dominant_interval_seconds(None) is None
        assert dominant_interval_seconds(pd.DataFrame()) is None
        assert dominant_interval_seconds(_df(300, n=2)) is None

    @pytest.mark.parametrize("tf", TF_NAMES)
    def test_matching_interval_passes(self, tf):
        assert interval_matches_tf(_df(TF_SECONDS[tf]), tf) is True

    def test_wrong_interval_rejected(self):
        """
        🔴 قلب اصلاح: والکس + «۱۵ دقیقه» کندل ۶۰ ثانیه می‌دهد.
        باید رد شود.
        """
        df = _df(60)  # ─── ۱ دقیقه ───
        assert interval_matches_tf(df, "۱۵ دقیقه") is False
        assert interval_matches_tf(df, "۵ دقیقه") is False
        assert interval_matches_tf(df, "۱ ساعت") is False

    def test_wallex_15m_bug_is_caught(self):
        """سناریوی واقعی والکس: ۲۸۷۱۷ کندل ۱ دقیقه‌ای"""
        df = _df(60, n=500)
        assert interval_matches_tf(df, "۱۵ دقیقه") is False
        detail = interval_mismatch_detail(df, "۱۵ دقیقه")
        assert "900" in detail and "60" in detail

    def test_small_deviation_allowed(self):
        """انحراف ±۱۰٪ مجاز است (کندل‌های واقعی همیشه دقیق نیستند)"""
        # ─── ۳۱۰ ثانیه در برابر ۳۰۰s = ۳.۳٪ ───
        assert interval_matches_tf(_df(310), "۵ دقیقه") is True
        # ─── ۲۹۰ ثانیه = ۳.۳٪ ───
        assert interval_matches_tf(_df(290), "۵ دقیقه") is True

    def test_large_deviation_rejected(self):
        """۳۶۰s در برابر ۳۰۰s = ۲۰٪ → رد"""
        assert interval_matches_tf(_df(360), "۵ دقیقه") is False

    def test_fails_open_on_unmeasurable(self):
        """اگر قابل اندازه‌گیری نباشد، رد نکن (fail-open)"""
        tiny = _df(300, n=2)
        assert interval_matches_tf(tiny, "۵ دقیقه") is True
        assert interval_matches_tf(None, "۵ دقیقه") is True

    def test_unknown_tf_does_not_crash(self):
        assert interval_matches_tf(_df(300), "نامعلوم") is True


# ═══════════════════════════════════════════════════════════
# ۳. fallback آگاه از بازه
# ═══════════════════════════════════════════════════════════
class TestIntervalAwareFallback:
    def test_bad_first_source_falls_to_next(self, monkeypatch):
        """
        🔴 منبع اول کندل اشتباه می‌دهد → باید منبع دوم امتحان شود
        و دیتای **درست** برگردد (نه None).
        """
        from services import data_service as ds
        from services.cache import clear_all_negative, data_cache

        data_cache.clear()
        clear_all_negative()

        good = _df(900)  # ─── ۱۵ دقیقه درست ───

        def fake_fetch(*, ticker, interval, period, source, tf_name):
            if source == "wallex":
                return _df(60)  # ─── ❌ کندل ۱ دقیقه ───
            if source == "nobitex":
                return good  # ─── ✅ درست ───
            return None

        monkeypatch.setattr(ds, "fetch_history_by_source", fake_fetch)
        monkeypatch.setattr(ds, "is_valid_nobitex_symbol", lambda t: True)

        df = ds._fetch_ohlcv_uncached(
            ticker="BTC-USD",
            tf_name="۱۵ دقیقه",
            source="wallex",
            effective_source="wallex",
            interval="15m",
            period="5d",
            cache_key="test-key",
            use_cache=False,
        )

        assert df is not None, "fallback باید دیتای درست بدهد"
        assert dominant_interval_seconds(df) == 900

    def test_all_sources_bad_returns_none(self, monkeypatch):
        """اگر همه کندل اشتباه بدهند → None"""
        from services import data_service as ds
        from services.cache import clear_all_negative, data_cache

        data_cache.clear()
        clear_all_negative()

        monkeypatch.setattr(
            ds, "fetch_history_by_source",
            lambda **k: _df(60),  # ─── همه ۱ دقیقه ───
        )
        monkeypatch.setattr(ds, "is_valid_nobitex_symbol", lambda t: True)

        df = ds._fetch_ohlcv_uncached(
            ticker="BTC-USD", tf_name="۱۵ دقیقه", source="wallex",
            effective_source="wallex", interval="15m", period="5d",
            cache_key="test-key2", use_cache=False,
        )
        assert df is None, "نباید دیتای با بازه‌ی اشتباه بدهد"

    def test_bad_interval_marks_permanent_negative(self, monkeypatch):
        """رد به‌خاطر بازه = خطای قطعی → کش منفی ۲۴ ساعته"""
        from services import data_service as ds
        from services.cache import (
            clear_all_negative,
            data_cache,
            is_permanent_failure,
        )

        data_cache.clear()
        clear_all_negative()
        key = "test-key3"

        monkeypatch.setattr(ds, "fetch_history_by_source", lambda **k: _df(60))
        monkeypatch.setattr(ds, "is_valid_nobitex_symbol", lambda t: True)

        ds._fetch_ohlcv_uncached(
            ticker="BTC-USD", tf_name="۱۵ دقیقه", source="wallex",
            effective_source="wallex", interval="15m", period="5d",
            cache_key=key, use_cache=True,
        )
        assert is_permanent_failure(key) is True, (
            "رد به‌خاطر بازه‌ی اشتباه باید قطعی ثبت شود"
        )


# ═══════════════════════════════════════════════════════════
# ۴. ردیابی منبع واقعی
# ═══════════════════════════════════════════════════════════
class TestSourceTracking:
    def test_tag_and_read(self):
        from core.data_fetcher import _tag_source, get_data_source

        df = _df(300)
        _tag_source(df, "wallex")
        assert get_data_source(df) == "wallex"

    def test_default_when_untagged(self):
        from core.data_fetcher import get_data_source

        assert get_data_source(_df(300)) == ""
        assert get_data_source(_df(300), "nobitex") == "nobitex"
        assert get_data_source(None, "x") == "x"

    def test_fetch_tags_real_source(self, monkeypatch):
        """
        🔴 زنجیره‌ی داخلی نباید منبع را گم کند.

        کاربر «والکس» می‌خواهد، والکس دیتا ندارد، نوبیتکس می‌دهد
        → برچسب باید «nobitex» باشد، نه «wallex».
        """
        import core.wallex_fetcher as wf
        from core.data_fetcher import fetch_history_by_source, get_data_source

        monkeypatch.setattr(wf, "fetch_wallex_candles", lambda *a, **k: None)

        df = fetch_history_by_source(
            "BTC-USD", "1h", "3mo", "wallex", tf_name="۱ ساعت"
        )
        if df is not None:
            assert get_data_source(df) in ("nobitex", "bitpin"), (
                f"منبع واقعی باید نوبیتکس/بیت‌پین باشد، نه "
                f"{get_data_source(df)}"
            )


# ═══════════════════════════════════════════════════════════
# ۵. کش منفی تفکیک‌شده
# ═══════════════════════════════════════════════════════════
class TestNegativeCacheTTL:
    def test_ttls_defined_and_differentiated(self):
        """
        ⚠️ بازنویسی ۱.۷: TTL از ۲۴ ساعت به ۱۰ دقیقه کاهش یافت.

        دلیل: اگر صرافی لحظه‌ای مشکل داشت یا TF جدید اضافه می‌شد،
        آن ترکیب یک روز کامل خاموش می‌ماند و کاربر «خالی» می‌دید.
        الان سیستم خودش را سریع بازیابی می‌کند.
        """
        from services.cache import (
            NEGATIVE_TTL_STATIC,
            NEGATIVE_TTL_TRANSIENT,
        )

        assert NEGATIVE_TTL_STATIC == 600, "ساختاری باید ۱۰ دقیقه باشد"
        assert NEGATIVE_TTL_TRANSIENT < NEGATIVE_TTL_STATIC
        assert NEGATIVE_TTL_TRANSIENT <= 300, "گذرا باید کوتاه باشد"

    def test_ttl_short_enough_for_recovery(self):
        """هیچ TTL نباید بیش از ۱۵ دقیقه باشد"""
        from services.cache import (
            NEGATIVE_TTL_STATIC,
            NEGATIVE_TTL_TRANSIENT,
        )

        assert max(NEGATIVE_TTL_STATIC, NEGATIVE_TTL_TRANSIENT) <= 900

    def test_permanent_flag_tracked(self):
        from services.cache import (
            clear_all_negative,
            get_negative,
            is_permanent_failure,
            set_negative,
        )

        clear_all_negative()
        pk, tk = "perm-key", "temp-key"

        set_negative(pk, permanent=True)
        set_negative(tk, permanent=False)

        assert get_negative(pk) and get_negative(tk)
        assert is_permanent_failure(pk) is True
        assert is_permanent_failure(tk) is False
        clear_all_negative()

    def test_stats(self):
        from services.cache import (
            clear_all_negative,
            negative_cache_stats,
            set_negative,
        )

        clear_all_negative()
        set_negative("a", permanent=True)
        set_negative("b", permanent=False)
        st = negative_cache_stats()
        assert st["total"] == 2
        assert st["permanent"] == 1
        assert st["temporary"] == 1
        clear_all_negative()

    def test_clear_removes_permanent_flag(self):
        from services.cache import (
            clear_all_negative,
            clear_negative,
            is_permanent_failure,
            set_negative,
        )

        clear_all_negative()
        set_negative("k", permanent=True)
        clear_negative("k")
        assert is_permanent_failure("k") is False


# ═══════════════════════════════════════════════════════════
# ۶. والکس — نقشه‌ی دقیق
# ═══════════════════════════════════════════════════════════
class TestWallexMapPrecision:
    def test_only_verified_resolutions(self):
        """
        فقط resolution هایی که کندل **درست** می‌دهند.

        ⚠️ «15» عمداً غایب: کد 200 می‌دهد ولی محتوایش ۱ دقیقه است.
        """
        from core.wallex_fetcher import _WALLEX_WORKING_RES

        assert _WALLEX_WORKING_RES == frozenset({"60", "1D"})
        assert "15" not in _WALLEX_WORKING_RES

    def test_tf_map_matches_working_set(self):
        from core.wallex_fetcher import TF_MAP, _WALLEX_WORKING_RES

        for tf, res in TF_MAP.items():
            assert res in _WALLEX_WORKING_RES, f"{tf} → {res} معتبر نیست"

    def test_all_six_tfs_documented(self):
        """WALLEX_RESOLUTIONS باید هر ۶ TF را مستند کند (حتی غایب‌ها)"""
        from core.wallex_fetcher import WALLEX_RESOLUTIONS

        assert set(WALLEX_RESOLUTIONS) == set(TF_NAMES)

    def test_map_tf_none_for_unsupported(self):
        from core.wallex_fetcher import map_tf

        assert map_tf("۱ ساعت") == "60"
        assert map_tf("روزانه") == "1D"
        for tf in ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "نامعلوم"]:
            assert map_tf(tf) is None, f"{tf} نباید resolution داشته باشد"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
