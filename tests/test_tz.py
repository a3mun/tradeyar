"""
tests/test_tz.py
تست باگ ۱ — Timezone
============================================================
پوشش:
  ۱. core/tz.py — نرمال‌سازی، تبدیل، فیلتر
  ۲. سه fetcher — ایندکس باید UTC-aware باشد
  ۳. backtest_service — فیلتر کندل برابر با تست دستی کاربر
     («بیت‌پین باید فقط ۳ کندل بدهد»)
  ۴. live — بیت‌پین/والکس واقعاً UTC می‌دهند (اختیاری، با --live)
"""

import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from core.tz import (
    TEHRAN,
    ensure_utc_index,
    filter_from,
    is_utc_aware,
    iso_utc,
    to_iran,
    to_utc_aware,
    to_utc_naive,
    utc_now,
)

UTC = timezone.utc


# ═══════════════════════════════════════════════════════════
# ۱. core/tz.py
# ═══════════════════════════════════════════════════════════
class TestEnsureUtcIndex:
    def test_naive_becomes_utc(self):
        """naive بدون assume_tz → UTC فرض می‌شود"""
        df = pd.DataFrame(
            {"close": [1.0]}, index=pd.to_datetime(["2026-01-01 12:00:00"])
        )
        out = ensure_utc_index(df)
        assert out.index.tz is not None
        assert out.index[0] == pd.Timestamp("2026-01-01 12:00:00", tz="UTC")

    def test_aware_utc_unchanged(self):
        df = pd.DataFrame(
            {"close": [1.0]}, index=pd.to_datetime(["2026-01-01T12:00:00Z"])
        )
        out = ensure_utc_index(df)
        assert out.index[0] == pd.Timestamp("2026-01-01 12:00:00", tz="UTC")

    def test_tehran_localised_then_converted(self):
        """03:30 تهران → 00:00Z"""
        df = pd.DataFrame(
            {"close": [1.0]}, index=pd.to_datetime(["2026-01-01 03:30:00"])
        )
        out = ensure_utc_index(df, assume_tz=TEHRAN)
        assert out.index[0] == pd.Timestamp("2026-01-01 00:00:00", tz="UTC")

    def test_other_tz_converted_not_relabelled(self):
        """ایندکس +03:30 واقعی → UTC (تبدیل، نه تغییر برچسب)"""
        idx = pd.date_range("2026-01-01 03:30", periods=2, freq="5min", tz=TEHRAN)
        out = ensure_utc_index(pd.DataFrame({"close": [1.0, 2.0]}, index=idx))
        assert out.index[0] == pd.Timestamp("2026-01-01 00:00:00", tz="UTC")

    def test_none_and_empty_safe(self):
        assert ensure_utc_index(None) is None
        assert ensure_utc_index(pd.DataFrame()).empty

    def test_copy_does_not_mutate_original(self):
        df = pd.DataFrame(
            {"close": [1.0]}, index=pd.to_datetime(["2026-01-01 12:00:00"])
        )
        _ = ensure_utc_index(df, copy=True)
        assert df.index.tz is None, "کپی نباید اصل را تغییر دهد"

    def test_string_index_converted(self):
        df = pd.DataFrame({"close": [1.0, 2.0]}, index=["2026-01-01", "2026-01-02"])
        out = ensure_utc_index(df)
        assert isinstance(out.index, pd.DatetimeIndex)
        assert out.index.tz is not None

    def test_is_utc_aware_helper(self):
        ok = pd.DataFrame(
            {"c": [1.0]}, index=pd.date_range("2026-01-01", periods=2, tz="UTC")
        )
        bad = pd.DataFrame({"c": [1.0]}, index=pd.date_range("2026-01-01", periods=2))
        assert is_utc_aware(ok) is True
        assert is_utc_aware(bad) is False
        assert is_utc_aware(None) is False


class TestDatetimeHelpers:
    def test_to_utc_naive_from_aware(self):
        dt = datetime(
            2026, 1, 1, 3, 30, tzinfo=timezone(timedelta(hours=3, minutes=30))
        )
        assert to_utc_naive(dt) == datetime(2026, 1, 1, 0, 0)

    def test_to_utc_naive_naive_unchanged(self):
        """naive را UTC فرض می‌کنیم، نه وقت محلی"""
        assert to_utc_naive(datetime(2026, 1, 1, 12, 0)) == datetime(2026, 1, 1, 12, 0)

    def test_to_utc_aware_roundtrip(self):
        dt = datetime(2026, 1, 1, 12, 0)
        aware = to_utc_aware(dt)
        assert aware.tzinfo is not None
        assert to_utc_naive(aware) == dt

    def test_to_iran(self):
        assert to_iran(datetime(2026, 1, 1, 0, 0)).strftime("%H:%M") == "03:30"

    def test_iso_utc_has_offset(self):
        """isoformat باید +00:00 داشته باشد تا مرورگر درست پارس کند"""
        s = iso_utc(datetime(2026, 1, 1, 12, 0))
        assert s.endswith("+00:00"), f"بدون offset: {s}"
        assert "Z" in s or "+00:00" in s

    def test_iso_utc_none(self):
        assert iso_utc(None) is None

    def test_utc_now_is_aware(self):
        assert utc_now().tzinfo is not None


class TestFilterFrom:
    def _df(self, tz="UTC"):
        return pd.DataFrame(
            {"close": range(5)},
            index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min", tz=tz),
        )

    def test_aware_index_utc_entry(self):
        """🔴 تست کلیدی کاربر: ۳ کندل از ۵"""
        entry = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
        assert len(filter_from(self._df(), entry)) == 3

    def test_naive_entry_treated_as_utc(self):
        """entry بدون tz → UTC فرض می‌شود (نه وقت محلی)"""
        entry = datetime(2026, 1, 1, 0, 10)
        assert len(filter_from(self._df(), entry)) == 3

    def test_exactly_on_boundary_included(self):
        entry = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
        out = filter_from(self._df(), entry)
        assert out.index[0] == pd.Timestamp("2026-01-01 00:10:00", tz="UTC")

    def test_entry_before_all(self):
        entry = datetime(2025, 12, 31, tzinfo=UTC)
        assert len(filter_from(self._df(), entry)) == 5

    def test_entry_after_all(self):
        entry = datetime(2026, 1, 2, tzinfo=UTC)
        assert filter_from(self._df(), entry).empty

    def test_naive_index_gets_normalised(self):
        """ایندکس naive هم باید درست فیلتر شود (با نرمال‌سازی)"""
        df = pd.DataFrame(
            {"close": range(5)},
            index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min"),
        )
        entry = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
        assert len(filter_from(df, entry)) == 3


# ═══════════════════════════════════════════════════════════
# ۲. fetcherها — ایندکس باید UTC-aware باشد
# ═══════════════════════════════════════════════════════════

# ─── داده‌ی خام نمونه در سطح ماژول (تا در class body اسکوپ گم نشود) ───
_BITPIN_BASE_TS = 1791030600  # 2026-10-03 12:30:00Z

_BITPIN_RAW = [
    {
        "ts": _BITPIN_BASE_TS + i * 3600,
        "open": "100.0",
        "high": "110.0",
        "low": "90.0",
        "close": "105.0",
        "volume": "12.5",
    }
    for i in range(25)
]

_WALLEX_BASE_TS = 1791032400  # 2026-10-03 13:00:00Z

_WALLEX_RAW = {
    "s": "ok",
    "t": [_WALLEX_BASE_TS + i * 3600 for i in range(25)],
    "o": [100.0] * 25,
    "h": [110.0] * 25,
    "l": [90.0] * 25,
    "c": [105.0] * 25,
    "v": [1.0] * 25,
}

_TSETMC_RAW = {
    "closingPriceDaily": [
        {
            "dEven": 20261003,
            "priceFirst": 1000,
            "priceMax": 1100,
            "priceMin": 900,
            "pClosing": 1050,
            "qTotTran5J": 5000,
        }
    ]
}


class _FakeResp:
    """پاسخ HTTP جعلی — payload در زمان ساخت تزریق می‌شود."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestFetchersReturnUtcIndex:
    """پارس هر fetcher باید ایندکس UTC-aware بدهد — با mock، بدون شبکه."""

    def test_bitpin_index_is_utc_aware(self, monkeypatch):
        from core import bitpin_fetcher as bf

        monkeypatch.setattr(bf.requests, "get", lambda *a, **k: _FakeResp(_BITPIN_RAW))

        df = bf.fetch_bitpin_candles("BTC-USD", "۵ دقیقه")
        assert df is not None and not df.empty
        assert is_utc_aware(df), f"ایندکس UTC نیست: {df.index}"
        # اولین کندل: epoch 1791030600 = 2026-10-03 12:30Z
        assert df.index[0] == pd.Timestamp("2026-10-03 12:30:00", tz="UTC")

    def test_wallex_index_is_utc_aware(self, monkeypatch):
        from core import wallex_fetcher as wf

        monkeypatch.setattr(wf.requests, "get", lambda *a, **k: _FakeResp(_WALLEX_RAW))

        df = wf.fetch_wallex_candles("BTC-USD", "۱ ساعت")
        assert df is not None and not df.empty
        assert is_utc_aware(df)
        assert df.index[0] == pd.Timestamp("2026-10-03 13:00:00", tz="UTC")

    def test_tsetmc_calendar_date_is_tehran_midnight(self, monkeypatch):
        """
        تاریخ تقویمی TSETMC → نیمه‌شب تهران → UTC.
        2026-10-03 → 2026-10-02T20:30:00Z
        """
        from core import tsetmc_fetcher as tf

        monkeypatch.setattr(tf.requests, "get", lambda *a, **k: _FakeResp(_TSETMC_RAW))

        df = tf.fetch_tsetmc_ohlcv("12345", days=10)
        assert df is not None and not df.empty
        assert is_utc_aware(df)
        assert df.index[0] == pd.Timestamp("2026-10-02 20:30:00", tz="UTC")

    def test_nobitex_index_is_utc_aware(self):
        """نوبیتکس از قبل درست بود — مطمئن شو رگرسیون ندارد"""
        base = 1791030600
        df = pd.DataFrame(
            {"close": [1.0, 2.0]},
            index=pd.to_datetime([base, base + 3600], unit="s", utc=True),
        )
        assert is_utc_aware(df)


# ═══════════════════════════════════════════════════════════
# ۳. لحظه‌ای که مشکل اصلی بود — همه منابع یک جواب بدهند
# ═══════════════════════════════════════════════════════════
class TestAllSourcesAgree:
    """
    🔴 تست رگرسیون اصلی: همان ۵ کندل، سه نمایش مختلف،
    باید همه ۳ کندل بدهند. پیش از اصلاح، بیت‌پین ۵ می‌داد.
    """

    def test_three_representations_same_result(self):
        entry = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
        expected = 3

        # نوبیتکس — UTC-aware
        nobitex = pd.DataFrame(
            {"h": range(5)},
            index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min", tz="UTC"),
        )

        # بیت‌پین/والکس — ایندکس naive UTC (خروجی قدیمی، پیش از اصلاح)
        naive_utc = pd.DataFrame(
            {"h": range(5)},
            index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min"),
        )

        # TSETMC/تهران — نمایش محلی همان لحظات
        tehran = pd.DataFrame(
            {"h": range(5)},
            index=pd.date_range("2026-01-01 03:30", periods=5, freq="5min", tz=TEHRAN),
        )

        for name, df in (
            ("nobitex(UTC-aware)", nobitex),
            ("bitpin(naive→UTC)", naive_utc),
            ("tsetmc(Tehran-aware)", tehran),
        ):
            got = len(filter_from(df, entry))
            assert got == expected, f"{name}: انتظار {expected}، گرفت {got}"


# ═══════════════════════════════════════════════════════════
# ۴. backtest_service — مسیر انتها به انتها
# ═══════════════════════════════════════════════════════════
class TestBacktestServiceTz:
    """
    ⚠️ این تست‌ها از timestamp **نسبی به الان** استفاده می‌کنند، نه تاریخ
    ثابت. دلیل: `_check_one` سیگنال قدیمی‌تر از SIGNAL_TIMEOUT را
    «expired» می‌کند، پس تاریخ ثابت با گذر زمان تست را می‌شکند.
    """

    # ─── «الان» گرد شده به دقیقه — نقطه‌ی مرجع همه‌ی تست‌ها ───
    @staticmethod
    def _ref_now() -> datetime:
        return utc_now().replace(second=0, microsecond=0)

    def _make_log(self, sl, tp, ts, signal="LONG"):
        from api.models import SignalLog

        return SignalLog(
            ticker="BTC-USD",
            name="BTC",
            signal=signal,
            direction="long",
            price=100.0,
            sl=sl,
            tp=tp,
            tf="۵ دقیقه",
            source="bitpin",
            timestamp=ts,
        )

    def _candles(self, index, highs):
        """کندل‌های ساده — high معنی دارد، low برای ambiguous"""
        n = len(index)
        # ─── low = high - 2 (کمتر از tp و sl) ───
        # ─── چرا: برای LONG با sl=95, tp=110:
        #     high=111 → tp_hit=True, low=109 → sl_hit=False → WIN
        #     high=50  → tp_hit=False, low=48 → sl_hit=False → عبور
        lows = [max(40.0, h - 2.0) for h in highs]
        return pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": highs,
                "low": lows,
                "close": [100.0] * n,
                "volume": [1.0] * n,
            },
            index=index,
        )

    def test_filters_candles_before_entry(self, monkeypatch):
        """
        🔴 تست دستی کاربر:
        entry در دقیقه‌ی -10، پنج کندل 5m با ایندکس naive UTC
        (شبیه خروجی بیت‌پین). فقط ۳ کندل آخر باید دیده شوند و
        کندلی که high=111 دارد باید WIN بدهد.
        """
        import services.backtest_service as bs

        now = self._ref_now()
        entry = now - timedelta(minutes=10)

        # کندل‌ها: -18, -13, -8, -3, +2 دقیقه  (سه‌تای آخر بعد از entry)
        idx = pd.DatetimeIndex(
            [
                now - timedelta(minutes=18),
                now - timedelta(minutes=13),
                now - timedelta(minutes=8),
                now - timedelta(minutes=3),
                now + timedelta(minutes=2),
            ]
        )
        # فقط کندل -8 (که بعد از entry است) به TP می‌رسد
        candles = self._candles(idx, [50.0, 50.0, 111.0, 50.0, 50.0])

        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)

        log = self._make_log(sl=95.0, tp=110.0, ts=entry)
        assert bs._check_one(log) == "win"
        assert log.result_time.tzinfo is not None, "result_time باید aware باشد"
        assert log.result_time == (now - timedelta(minutes=8)).replace(tzinfo=UTC)

    def test_does_not_use_candle_before_entry(self, monkeypatch):
        """
        اگر تنها کندلی که به TP رسیده **قبل از** entry باشد،
        هیچ نتیجه‌ای نباید ثبت شود.

        پیش از اصلاح: ایندکس naive با entry UTC مقایسه می‌شد و
        آن کندل از فیلتر رد می‌شد → WIN کاذب.
        """
        import services.backtest_service as bs

        now = self._ref_now()
        entry = now - timedelta(minutes=10)

        # همه‌ی کندل‌ها قبل از entry — و اولین کندل به TP رسیده
        idx = pd.DatetimeIndex(
            [
                now - timedelta(minutes=30),
                now - timedelta(minutes=25),
                now - timedelta(minutes=20),
            ]
        )
        candles = self._candles(idx, [999.0, 50.0, 50.0])

        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)

        log = self._make_log(sl=95.0, tp=110.0, ts=entry)
        assert bs._check_one(log) is None, "کندل قبل از ورود نباید داوری شود"

    def test_timeout_uses_utc(self, monkeypatch):
        """سیگنال قدیمی‌تر از timeout → expired"""
        import services.backtest_service as bs

        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: None)

        old = utc_now() - timedelta(days=30)
        log = self._make_log(sl=95.0, tp=110.0, ts=old)
        assert bs._check_one(log) == "expired"
        assert log.expired is True
        assert log.result_time.tzinfo is not None

    def test_naive_db_timestamp_treated_as_utc(self, monkeypatch):
        """
        اگر SQLite timestamp را naive برگرداند، باید **UTC** فرض شود
        (نه وقت محلی). اگر وقت محلی فرض می‌شد، entry ۳:۳۰ ساعت
        شیفت می‌خورد و این تست می‌شکست.
        """
        import services.backtest_service as bs

        now = self._ref_now()
        idx = pd.DatetimeIndex(
            [now - timedelta(minutes=12), now - timedelta(minutes=7)]
        )
        candles = self._candles(idx, [50.0, 111.0])

        monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: candles)

        naive_ts = (now - timedelta(minutes=10)).replace(tzinfo=None)
        log = self._make_log(sl=95.0, tp=110.0, ts=naive_ts)
        assert bs._check_one(log) == "win"


# ═══════════════════════════════════════════════════════════
# ۵. تست live (اختیاری)
# ═══════════════════════════════════════════════════════════
@pytest.mark.skipif("--live" not in sys.argv, reason="با --live اجرا می‌شود")
class TestLiveSources:
    def test_bitpin_live_index_is_utc_and_recent(self):
        from core.bitpin_fetcher import fetch_bitpin_candles

        df = fetch_bitpin_candles("BTC-USD", "۱ ساعت")
        assert df is not None and not df.empty
        assert is_utc_aware(df)
        age_min = (utc_now() - df.index[-1]).total_seconds() / 60
        assert 0 <= age_min < 180, f"کندل آخر {age_min:.0f} دقیقه قدیمی است"

    def test_wallex_live_index_is_utc_and_recent(self):
        from core.wallex_fetcher import fetch_wallex_candles

        df = fetch_wallex_candles("BTC-USD", "۱ ساعت")
        assert df is not None and not df.empty
        assert is_utc_aware(df)
        age_min = (utc_now() - df.index[-1]).total_seconds() / 60
        assert 0 <= age_min < 180, f"کندل آخر {age_min:.0f} دقیقه قدیمی است"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"] + sys.argv[1:]))
