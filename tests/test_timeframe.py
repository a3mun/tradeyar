"""
tests/test_timeframe.py
تست باگ ۲ — پاس دادن درست tf_name
============================================================
پوشش:
  ۱. جدول واحد TIMEFRAME_SPECS و سازگاری عقب‌رو TIMEFRAMES
  ۲. پشتیبانی واقعی هر منبع (is_ohlcv_supported)
  ۳. نقشه‌ی والکس بدون تبدیل بی‌صدا
  ۴. 🔴 تست کاربر: analyze('BTC-USD', 'wallex', '۱ ساعت')
     باید کندل‌های ۱ ساعته بدهد (فاصله‌ی ایندکس = 3600s)
  ۵. بیت‌پین «روزانه» باید res=1d بگیرد، نه 5m
"""

import inspect
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from core.contracts import (
    TIMEFRAMES,
    TIMEFRAME_SPECS,
    TF_BY_INTERVAL,
    TF_NAMES,
    get_tf_spec,
    is_ohlcv_supported,
)

UTC = timezone.utc


# ═══════════════════════════════════════════════════════════
# ۱. جدول واحد
# ═══════════════════════════════════════════════════════════
class TestTimeframeSpecs:
    def test_six_timeframes(self):
        assert len(TIMEFRAME_SPECS) == 6
        assert TF_NAMES == list(TIMEFRAME_SPECS)

    def test_legacy_timframes_order_preserved(self):
        """app.py و ui به ترتیب TIMEFRAMES وابسته‌اند"""
        names = [n for _, _, n in TIMEFRAMES]
        assert names == [
            "۱ دقیقه",
            "۵ دقیقه",
            "۱۵ دقیقه",
            "۳۰ دقیقه",
            "۱ ساعت",
            "روزانه",
        ]

    def test_legacy_tuples_unpackable(self):
        """(interval, period, tf_name) باید کار کند"""
        for iv, p, n in TIMEFRAMES:
            assert isinstance(iv, str) and iv
            assert isinstance(p, str) and p
            assert n in TIMEFRAME_SPECS

    def test_interval_matches_legacy(self):
        """interval باید همان مقادیر قبلی باشد تا نوبیتکس نشکند"""
        expected = {
            "۱ دقیقه": "1m",
            "۵ دقیقه": "5m",
            "۱۵ دقیقه": "15m",
            "۳۰ دقیقه": "30m",
            "۱ ساعت": "1h",
            "روزانه": "1d",
        }
        for tf, iv in expected.items():
            assert TIMEFRAME_SPECS[tf].interval == iv

    def test_tf_by_interval_reverse_map(self):
        assert TF_BY_INTERVAL["1h"] == "۱ ساعت"
        assert TF_BY_INTERVAL["1d"] == "روزانه"

    def test_period_days_increases_with_tf(self):
        """TF بزرگ‌تر نباید دیتای کمتری بگیرد"""
        order = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]
        days = [TIMEFRAME_SPECS[t].period_days for t in order]
        assert days == sorted(days), f"غیریکنوا: {dict(zip(order, days))}"

    def test_get_tf_spec_unknown_warns_and_falls_back(self, caplog):
        with caplog.at_level("WARNING"):
            spec = get_tf_spec("نامعلوم")
        assert spec.name_fa == "۵ دقیقه"
        assert any("ناشناخته" in r.message for r in caplog.records)


# ═══════════════════════════════════════════════════════════
# ۲. پشتیبانی واقعی منابع
# ═══════════════════════════════════════════════════════════
class TestIsTfSupported:
    """
    ⚠️ بازنویسی‌شده در نسخه ۱.۶.

    ``is_ohlcv_supported`` دیگر whitelist نیست — فقط **قیدهای
    قطعی** را برمی‌گرداند. بقیه به پاسخ واقعی صرافی واگذار می‌شود،
    چون پشتیبانی TF **per-نماد** است نه per-صرافی.
    """

    def test_nobitex_supports_all(self):
        """نوبیتکس هیچ قید قطعی ندارد"""
        for tf in TF_NAMES:
            assert is_ohlcv_supported(tf, "nobitex"), f"نوبیتکس {tf}"

    def test_bitpin_supports_all(self):
        for tf in TF_NAMES:
            assert is_ohlcv_supported(tf, "bitpin"), f"بیت‌پین {tf}"

    def test_wallex_no_absolute_block_except_30m(self):
        """
        🔴 اصلاح کلیدی: والکس فقط «۳۰ دقیقه» را قطعاً ندارد.

        پیش‌تر «۵ دقیقه» هم مسدود می‌شد که غلط بود — باید
        درخواست برود و اگر API دیتا داد، استفاده شود.
        (در عمل والکس برای ۵ دقیقه کندل ۱ دقیقه می‌دهد که
        اعتبارسنجی بازه ردش می‌کند و زنجیره به نوبیتکس می‌رود.)
        """
        # ─── تنها قید قطعی ───
        assert is_ohlcv_supported("۳۰ دقیقه", "wallex") is False

        # ─── بقیه باید «بله» باشند تا درخواست برود ───
        for tf in ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۱ ساعت", "روزانه"]:
            assert is_ohlcv_supported(tf, "wallex") is True, (
                f"والکس {tf} نباید قطعاً مسدود شود — "
                f"پشتیبانی per-نماد است"
            )

    def test_tsetmc_only_daily(self):
        """TSETMC واقعاً intraday ندارد → قید قطعی"""
        assert is_ohlcv_supported("روزانه", "tsetmc") is True
        assert is_ohlcv_supported("۵ دقیقه", "tsetmc") is False
        assert is_ohlcv_supported("۱ ساعت", "tsetmc") is False

    def test_tabdeal_has_no_ohlcv(self):
        """تبدیل OHLCV عمومی ندارد — همه‌ی TFها مسدود"""
        for tf in TF_NAMES:
            assert is_ohlcv_supported(tf, "tabdeal") is False, (
                f"تبدیل {tf} نباید OHLCV بدهد"
            )

    def test_abantether_removed(self):
        """🔴 آبان‌تتر در نسخه ۱.۸ حذف شد"""
        for tf in TF_NAMES:
            assert is_ohlcv_supported(tf, "abantether") is False

    def test_unknown_source_rejected(self):
        assert is_ohlcv_supported("۵ دقیقه", "ناشناخته") is False

    def test_unknown_tf_fails_open(self):
        """
        TF ناشناخته → ``True`` (fail-open).

        دلیل: ``is_ohlcv_supported`` فقط قیدهای قطعی را می‌داند.
        اگر TF را نشناسد نمی‌تواند قضاوت کند، پس رد نمی‌کند و
        اجازه می‌دهد ``get_tf_spec`` پیش‌فرض «۵ دقیقه» را بدهد
        و درخواست برود (fail-soft).
        """
        assert is_ohlcv_supported("ناشناخته", "nobitex") is True

    def test_legacy_alias_still_works(self):
        """نام قدیمی is_tf_supported باید کار کند"""
        from core.contracts import is_tf_supported

        assert is_tf_supported("۵ دقیقه", "nobitex") is True
        assert is_tf_supported("۳۰ دقیقه", "wallex") is False

    def test_source_lacks_ohlcv(self):
        from core.contracts import source_lacks_ohlcv

        assert source_lacks_ohlcv("tabdeal") is True
        assert source_lacks_ohlcv("nobitex") is False
        assert source_lacks_ohlcv("wallex") is False
        # ─── آبان‌تتر حذف شد ───
        assert source_lacks_ohlcv("abantether") is False


# ═══════════════════════════════════════════════════════════
# ۳. حذف تبدیل بی‌صدا در والکس
# ═══════════════════════════════════════════════════════════
class TestWallexNoSilentSubstitution:
    def test_5m_returns_none_not_15m(self):
        """
        🔴 والکس نباید برای «۵ دقیقه» کندل ۱۵ دقیقه بدهد.
        باید None برگرداند تا زنجیره‌ی fallback نوبیتکس را انتخاب کند.
        """
        from core.wallex_fetcher import fetch_wallex_candles

        assert fetch_wallex_candles("BTC-USD", "۵ دقیقه") is None

    def test_30m_returns_none_not_1h(self):
        from core.wallex_fetcher import fetch_wallex_candles

        assert fetch_wallex_candles("BTC-USD", "۳۰ دقیقه") is None

    def test_map_tf_no_default_fallback(self):
        """
        map_tf باید None بدهد برای resolution هایی که والکس
        پاسخ نمی‌دهد (نه پیش‌فرض 15).

        ⚠️ بازنویسی ۱.۶: «۵ دقیقه» حالا به res=5 نقشه می‌شود
        (تا درخواست برود و پاسخ واقعی تصمیم بگیرد)، پس در
        TF_MAP نیست چون 5 در فهرست resolution های کارکننده نیست.
        """
        from core.wallex_fetcher import map_tf

        assert map_tf("۱ ساعت") == "60"
        assert map_tf("روزانه") == "1D"
        # ─── این‌ها resolution معتبر ندارند → None ───
        assert map_tf("۱ دقیقه") is None
        assert map_tf("۵ دقیقه") is None
        assert map_tf("۳۰ دقیقه") is None
        assert map_tf("نامعلوم") is None

    def test_supported_tf_mapping_exact(self):
        """
        فقط resolution هایی که والکس **با بازه‌ی درست** می‌دهد.

        🔴 ۱۵ دقیقه (res=15) عمداً حذف شد: والکس کد 200 می‌دهد
        ولی محتوایش **کندل ۱ دقیقه** است (تأیید تجربی).
        اگر در نقشه باشد، ATR و SL/TP اشتباه محاسبه می‌شود.
        """
        from core.wallex_fetcher import TF_MAP

        assert TF_MAP == {
            "۱ ساعت": "60",
            "روزانه": "1D",
        }

    def test_wallex_resolution_map_documents_all(self):
        """WALLEX_RESOLUTIONS باید هر ۶ TF را مستند کند"""
        from core.wallex_fetcher import WALLEX_RESOLUTIONS

        assert set(WALLEX_RESOLUTIONS) == set(TF_NAMES)

    def test_bitpin_map_tf_no_default_fallback(self):
        """map_tf بیت‌پین هم نباید بی‌صدا 5m بدهد"""
        from core.bitpin_fetcher import map_tf

        assert map_tf("روزانه") == "1d"
        assert map_tf("۱ ساعت") == "1h"
        assert map_tf("نامعلوم") is None
        assert map_tf("") is None

    def test_bitpin_empty_tf_name_returns_none(self):
        from core.bitpin_fetcher import fetch_bitpin_candles

        assert fetch_bitpin_candles("BTC-USD", "") is None


# ═══════════════════════════════════════════════════════════
# ۴. پاس شدن tf_name در scanner و backtester
# ═══════════════════════════════════════════════════════════
class TestTfNameIsPassed:
    def test_data_fetcher_rejects_empty_tf_name(self):
        """بدون tf_name نباید دیتا بدهد (fail-loud)"""
        from core.data_fetcher import fetch_history_by_source

        assert (
            fetch_history_by_source("BTC-USD", "5m", "5d", "bitpin", tf_name="")
            is None
        )
        assert (
            fetch_history_by_source("BTC-USD", "1h", "3mo", "wallex", tf_name="")
            is None
        )

    def test_service_layer_always_passes_tf_name(self):
        """
        🔴 رگرسیون: لایه‌ی سرویس باید همیشه tf_name را پاس بدهد.

        ⚠️ تست‌های ``scanner`` و ``backtester`` حذف شدند چون آن
        ماژول‌ها بخشی از رابط Streamlit منسوخ بودند و پاک شدند.
        مسیر فعال FastAPI از ``services/data_service`` می‌گذرد.
        """
        import inspect

        from services import data_service

        src = inspect.getsource(data_service)
        assert "tf_name=tf_name" in src, (
            "data_service باید tf_name را به fetch_history_by_source پاس بدهد"
        )

    def test_data_fetcher_falls_back_for_unsupported_combo(self):
        """
        🔴 والکس + «۵ دقیقه» → نباید None بدهد و نباید کندل ۱۵ دقیقه
        به‌عنوان «۵ دقیقه» بدهد.

        رفتار درست: زنجیره‌ی fallback به صرافی‌ای می‌رود که این
        تایم‌فریم را دارد (نوبیتکس/بیت‌پین)، پس کاربر همان چیزی
        را می‌گیرد که خواسته.

        ⚠️ این تست پیش‌تر انتظار ``None`` داشت. آن انتظار غلط بود:
           ``fetch_history_by_source`` مسئول زنجیره‌ی fallback است،
           پس باید دیتای تایم‌فریم درست را برگرداند. رد کردن
           تایم‌فریم مربوط به خودِ ``fetch_wallex_candles`` است
           (تست جداگانه پایین).
        """
        from core.data_fetcher import fetch_history_by_source

        df = fetch_history_by_source(
            "BTC-USD", "5m", "5d", "wallex", tf_name="۵ دقیقه"
        )

        assert df is not None and not df.empty, "fallback دیتا نداد"
        # ─── 🔴 بازه‌ی کندل‌ها باید ۵ دقیقه باشد، نه ۱۵ دقیقه ───
        deltas = df.index.to_series().diff().dropna().dt.total_seconds()
        assert deltas.mode().iloc[0] == 300, (
            f"بازه {deltas.mode().iloc[0]}s — باید 300s (۵ دقیقه) باشد"
        )

    def test_wallex_itself_rejects_unsupported_tf(self):
        """خودِ والکس باید None بدهد، نه کندل تایم‌فریم دیگر"""
        from core.wallex_fetcher import fetch_wallex_candles

        assert fetch_wallex_candles("BTC-USD", "۵ دقیقه") is None
        assert fetch_wallex_candles("BTC-USD", "۳۰ دقیقه") is None


# ═══════════════════════════════════════════════════════════
# ۵. data_service — انتخاب منبع آگاه از TF
# ═══════════════════════════════════════════════════════════
class TestDataServiceSourceSelection:
    def test_supported_source_kept(self):
        from services.data_service import _resolve_source_for_tf

        assert _resolve_source_for_tf("wallex", "۱ ساعت") == "wallex"
        assert _resolve_source_for_tf("bitpin", "روزانه") == "bitpin"
        assert _resolve_source_for_tf("nobitex", "۵ دقیقه") == "nobitex"

    def test_unsupported_source_switches(self):
        """
        ⚠️ بازنویسی ۱.۸: سوئیچ در این لایه فقط برای قیدهای
        **قطعی** است — نه whitelist صرافی‌محور.

        قیدهای قطعی:
          • تبدیل (بدون OHLCV) → نوبیتکس
          • والکس + «۳۰ دقیقه» → نوبیتکس

        بقیه حفظ می‌شوند چون پشتیبانی **per-نماد** است و باید
        درخواست واقعی تصمیم بگیرد.
        """
        from services.data_service import _resolve_source_for_tf

        # ─── قید قطعی: تبدیل (کیسک ندارد) ───
        assert _resolve_source_for_tf("tabdeal", "۵ دقیقه") == "nobitex"
        assert _resolve_source_for_tf("tabdeal", "روزانه") == "nobitex"

        # ─── والکس برای TFهای مورد اختلاف حفظ می‌شود
        #     (درخواست می‌رود، اعتبارسنجی بازه تصمیم می‌گیرد) ───
        assert _resolve_source_for_tf("wallex", "۵ دقیقه") == "wallex"
        assert _resolve_source_for_tf("wallex", "۱۵ دقیقه") == "wallex"

        # ─── «۳۰ دقیقه» تنها قید قطعی والکس → سوئیچ قبل از درخواست ───
        assert _resolve_source_for_tf("wallex", "۳۰ دقیقه") == "nobitex"

        # ─── بقیه بدون تغییر ───
        assert _resolve_source_for_tf("nobitex", "۵ دقیقه") == "nobitex"
        assert _resolve_source_for_tf("bitpin", "روزانه") == "bitpin"

    def test_tf_map_matches_contracts(self):
        """TF_MAP در data_service نباید از contracts جدا بیفتد"""
        from services.data_service import TF_MAP

        for tf, spec in TIMEFRAME_SPECS.items():
            assert TF_MAP[tf] == (spec.interval, spec.period)

    def test_get_tf_params(self):
        from services.data_service import get_tf_params

        assert get_tf_params("۵ دقیقه") == ("5m", "5d")
        assert get_tf_params("۱ ساعت") == ("1h", "3mo")
        assert get_tf_params("روزانه") == ("1d", "6mo")

    def test_empty_tf_name_returns_none(self):
        from services.data_service import fetch_ohlcv

        assert fetch_ohlcv("BTC-USD", "", "nobitex") is None

    def test_tsetmc_non_daily_rejected(self):
        from services.data_service import fetch_ohlcv

        assert fetch_ohlcv("فولاد", "۵ دقیقه", "tsetmc") is None


# ═══════════════════════════════════════════════════════════
# ۶. 🔴 تست کاربر: بازه‌ی ایندکس = تایم‌فریم درخواستی
# ═══════════════════════════════════════════════════════════
class TestRequestedTfMatchesReturnedCandles:
    """
    تست کاربر:
        analyze('BTC-USD', 'wallex', '۱ ساعت') → df باید ساعت به ساعت باشد

    ما این را در سطح داده چک می‌کنیم: فاصله‌ی بین کندل‌ها باید
    با ضریب تایم‌فریم بخواند.
    """

    _EXPECTED_DELTA = {
        "۱ دقیقه": 60,
        "۵ دقیقه": 300,
        "۱۵ دقیقه": 900,
        "۳۰ دقیقه": 1800,
        "۱ ساعت": 3600,
        "روزانه": 86400,
    }

    @pytest.mark.parametrize("tf", list(TIMEFRAME_SPECS))
    def test_bitpin_returns_requested_resolution(self, tf, monkeypatch):
        """🔴 res ارسالی به بیت‌پین باید با تایم‌فریم بخواند"""
        from core import bitpin_fetcher as bf

        captured = {}

        def fake_get(url, params=None, **kw):
            captured["params"] = params

            class R:
                @staticmethod
                def raise_for_status():
                    return None

                @staticmethod
                def json():
                    step = TestRequestedTfMatchesReturnedCandles._EXPECTED_DELTA[tf]
                    base = 1791030600
                    return [
                        {
                            "ts": base + i * step,
                            "open": "100.0",
                            "high": "110.0",
                            "low": "90.0",
                            "close": "105.0",
                            "volume": "1.0",
                        }
                        for i in range(25)
                    ]

            return R()

        monkeypatch.setattr(bf.requests, "get", fake_get)

        df = bf.fetch_bitpin_candles("BTC-USD", tf)
        assert df is not None and not df.empty

        # res باید دقیقاً همان چیزی باشد که contracts می‌گوید
        assert captured["params"]["res"] == TIMEFRAME_SPECS[tf].bitpin_res, (
            f"{tf}: res={captured['params']['res']} "
            f"(انتظار {TIMEFRAME_SPECS[tf].bitpin_res})"
        )

        # 🔴 و بازه‌ی واقعی کندل‌ها باید با تایم‌فریم بخواند
        deltas = df.index.to_series().diff().dropna().dt.total_seconds().unique()
        assert len(deltas) == 1, f"بازه‌ها یکنواخت نیست: {deltas}"
        assert deltas[0] == self._EXPECTED_DELTA[tf], (
            f"{tf}: بازه‌ی کندل {deltas[0]}s است، انتظار {self._EXPECTED_DELTA[tf]}s"
        )

    def test_wallex_1h_returns_hourly_candles(self, monkeypatch):
        """
        🔴 تست دقیق کاربر:
        wallex + «۱ ساعت» → کندل‌های ۱ ساعته (3600s)
        """
        from core import wallex_fetcher as wf

        captured = {}

        def fake_get(url, params=None, **kw):
            captured["params"] = params
            base = 1791032400  # 13:00Z

            class R:
                @staticmethod
                def raise_for_status():
                    return None

                @staticmethod
                def json():
                    return {
                        "s": "ok",
                        "t": [base + i * 3600 for i in range(30)],
                        "o": [100.0] * 30,
                        "h": [110.0] * 30,
                        "l": [90.0] * 30,
                        "c": [105.0] * 30,
                        "v": [1.0] * 30,
                    }

            return R()

        monkeypatch.setattr(wf.requests, "get", fake_get)

        df = wf.fetch_wallex_candles("BTC-USD", "۱ ساعت")
        assert df is not None and not df.empty

        # resolution باید 60 باشد، نه 15
        assert captured["params"]["resolution"] == "60"

        deltas = df.index.to_series().diff().dropna().dt.total_seconds().unique()
        assert list(deltas) == [3600.0], f"بازه‌ی کندل: {deltas} (انتظار 3600)"

    def test_wallex_does_not_substitute_5m(self, monkeypatch):
        """والکس + ۵ دقیقه → هیچ درخواستی فرستاده نمی‌شود"""
        from core import wallex_fetcher as wf

        called = {"n": 0}

        def fake_get(*a, **kw):
            called["n"] += 1
            raise AssertionError("نباید درخواست بفرستد")

        monkeypatch.setattr(wf.requests, "get", fake_get)

        assert wf.fetch_wallex_candles("BTC-USD", "۵ دقیقه") is None
        assert called["n"] == 0, "برای TF پشتیبانی‌نشده نباید درخواست بفرستد"


# ═══════════════════════════════════════════════════════════
# ۷. تست live (اختیاری)
# ═══════════════════════════════════════════════════════════
import sys


@pytest.mark.skipif("--live" not in sys.argv, reason="با --live اجرا می‌شود")
class TestLiveTimeframes:
    @pytest.mark.parametrize(
        "tf,expected_sec",
        [
            ("۵ دقیقه", 300),
            ("۱۵ دقیقه", 900),
            ("۱ ساعت", 3600),
            ("روزانه", 86400),
        ],
    )
    def test_bitpin_live_delta(self, tf, expected_sec):
        from core.bitpin_fetcher import fetch_bitpin_candles

        df = fetch_bitpin_candles("BTC-USD", tf)
        if df is None or len(df) < 3:
            pytest.skip("دیتای زنده نیامد")

        deltas = df.index.to_series().diff().dropna().dt.total_seconds()
        mode = deltas.mode().iloc[0]
        assert mode == expected_sec, f"{tf}: بازه‌ی غالب {mode}s (انتظار {expected_sec}s)"

    def test_wallex_live_1h_delta(self):
        from core.wallex_fetcher import fetch_wallex_candles

        df = fetch_wallex_candles("BTC-USD", "۱ ساعت")
        if df is None or len(df) < 3:
            pytest.skip("دیتای زنده نیامد")

        deltas = df.index.to_series().diff().dropna().dt.total_seconds()
        assert deltas.mode().iloc[0] == 3600

    def test_wallex_live_5m_is_none(self):
        """والکس ۵ دقیقه ندارد — باید None بدهد"""
        from core.wallex_fetcher import fetch_wallex_candles

        assert fetch_wallex_candles("BTC-USD", "۵ دقیقه") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"] + sys.argv[1:]))
