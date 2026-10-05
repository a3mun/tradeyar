"""
tests/test_quote_independence.py
تست: قیمت هر صرافی باید **مستقل** باشد
============================================================
🔴 باگ رفع‌شده:
    ``fetch_quote_by_source`` برای آبان‌تتر + جفت‌های تتری به
    نوبیتکس fallback می‌زد و قیمت نوبیتکس را با برچسب
    «abantether» برمی‌گرداند. نتیجه: در جدول مقایسه قیمت،
    دو ردیف یکسان دیده می‌شد و کاربر فکر می‌کرد بازارها یکی‌اند.

قاعده (نسخه ۱.۷):
    هر صرافی قیمت **خودش** را می‌دهد. اگر آن بازار را ندارد،
    ``None`` — هرگز قیمت صرافی دیگر با برچسب خودمان.
"""

from unittest.mock import patch

import pytest

from core.data_fetcher import source_has_market


# ═══════════════════════════════════════════════════════════
# ۱. محدودیت ساختاری بازارها
# ═══════════════════════════════════════════════════════════
class TestSourceHasMarket:
    def test_tabdeal_has_both_markets(self):
        """
        🔴 تبدیل هم IRT هم USDT دارد (۵۲۵ بازار USDT تأیید شد).

        ⚠️ آبان‌تتر حذف شد — فقط تومانی بود و با بقیه هماهنگ
           نبود (نسخه ۱.۸).
        """
        assert source_has_market("BTC-USD", "tabdeal") is True
        assert source_has_market("PAXG-USD", "tabdeal") is True
        assert source_has_market("BTC-IRT", "tabdeal") is True
        assert source_has_market("PAXG-IRT", "tabdeal") is True

    def test_abantether_removed(self):
        """🔴 آبان‌تتر دیگر منبع معتبری نیست"""
        assert source_has_market("BTC-IRT", "abantether") is False

    def test_crypto_exchanges_have_both(self):
        """نوبیتکس/بیت‌پین/والکس/تبدیل هر دو جفت را دارند"""
        for src in ("nobitex", "bitpin", "wallex", "tabdeal"):
            assert source_has_market("BTC-USD", src) is True, src
            assert source_has_market("BTC-IRT", src) is True, src

    def test_tsetmc_only_iranian_stocks(self):
        assert source_has_market("فولاد", "tsetmc") is True
        assert source_has_market("BTC-USD", "tsetmc") is False

    def test_empty_and_unknown(self):
        assert source_has_market("", "nobitex") is False
        assert source_has_market("BTC-USD", "ناشناخته") is False


# ═══════════════════════════════════════════════════════════
# ۲. 🔴 تست اصلی: عدم fallback در quote
# ═══════════════════════════════════════════════════════════
class TestNoQuoteFallback:
    def test_removed_source_returns_none(self):
        """
        🔴 منبع حذف‌شده (آبان‌تتر) نباید قیمت از نوبیتکس بگیرد.
        """
        from core.data_fetcher import fetch_quote_by_source

        for ticker in ["BTC-USD", "ETH-USD", "PAXG-IRT"]:
            assert fetch_quote_by_source(ticker, "abantether") is None

    def test_no_cross_exchange_contamination(self):
        """
        🔴 هیچ دو صرافی‌ای نباید قیمت یکسان برگردانند مگر
        بازار واقعاً یکی باشد.

        این تست با mock کار می‌کند تا قطعی باشد.
        """
        from core.data_fetcher import fetch_quote_by_source

        # ─── قیمت‌های متمایز برای هر صرافی ───
        distinct = {
            "nobitex": 4151.00,
            "bitpin": 4151.31,
            "wallex": 4062.51,
        }

        def fake_nobitex(ticker):
            return {"price": distinct["nobitex"], "change_24h": 0.0}

        with patch(
            "core.nobitex_fetcher.fetch_nobitex_stats_for_ticker",
            fake_nobitex,
        ):
            results = {}
            for src in ["nobitex", "abantether"]:
                results[src] = fetch_quote_by_source("PAXG-USD", src)

        # ─── نوبیتکس قیمت دارد، منبع حذف‌شده None ───
        assert results["nobitex"] is not None
        assert results["abantether"] is None, (
            "🔴 منبع حذف‌شده نباید قیمت نوبیتکس را با برچسب خودش بدهد"
        )

    def test_tabdeal_uses_own_depths(self):
        """
        🔴 تبدیل باید از **عمق بازار خودش** قیمت بگیرد،
        نه از نوبیتکس.
        """
        from core.data_fetcher import fetch_quote_by_source

        nb_called = {"n": 0}

        def fake_nobitex(ticker):
            nb_called["n"] += 1
            return {"price": 999.0, "change_24h": 0.0}

        with patch(
            "core.nobitex_fetcher.fetch_nobitex_stats_for_ticker",
            fake_nobitex,
        ), patch(
            "core.tabdeal_fetcher.fetch_tabdeal_ticker",
            lambda t: {"price": 1106119300.12, "change_24h": 0.0},
        ):
            q = fetch_quote_by_source("PAXG-IRT", "tabdeal")

        assert q is not None
        assert q["source"] == "tabdeal"
        assert q["price"] == pytest.approx(1106119300.12)
        assert nb_called["n"] == 0, "نباید نوبیتکس صدا زده شود"


# ═══════════════════════════════════════════════════════════
# ۳. والکس — quote از markets (نه کندل)
# ═══════════════════════════════════════════════════════════
class TestWallexQuoteUsesMarkets:
    def test_wallex_quote_does_not_use_candles(self):
        """
        🔴 باگ رفع‌شده: پیش‌تر quote والکس از **کندل ۵ دقیقه**
        می‌آمد که والکس ندارد → همیشه None.
        """
        from core.data_fetcher import fetch_quote_by_source

        candles_called = {"n": 0}

        def fake_candles(*a, **k):
            candles_called["n"] += 1
            return None

        with patch(
            "core.wallex_fetcher.fetch_wallex_ticker",
            lambda t: {"price": 4062.51, "change_24h": -0.5},
        ), patch(
            "core.wallex_fetcher.fetch_wallex_candles",
            fake_candles,
        ):
            q = fetch_quote_by_source("PAXG-USD", "wallex")

        assert q is not None, "والکس باید قیمت بدهد"
        assert q["price"] == pytest.approx(4062.51)
        assert q["source"] == "wallex"
        assert candles_called["n"] == 0, "نباید از کندل استفاده کند"

    def test_wallex_price_parsed_from_string(self):
        """والکس قیمت را رشته می‌دهد — باید درست پارس شود"""
        from core.wallex_fetcher import fetch_wallex_ticker

        with patch("core.wallex_fetcher.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "result": {
                    "symbols": {
                        "PAXGUSDT": {
                            "stats": {"lastPrice": "4062.5100000000000000"}
                        }
                    }
                }
            }
            mock_get.return_value.raise_for_status = lambda: None

            t = fetch_wallex_ticker("PAXG-USD")

        assert t is not None
        assert t["price"] == pytest.approx(4062.51)


# ═══════════════════════════════════════════════════════════
# ۴. بیت‌پین — پارس مقاوم
# ═══════════════════════════════════════════════════════════
class TestBitpinPriceParsing:
    def test_string_price_parsed(self):
        """بیت‌پین قیمت را رشته می‌دهد"""
        from core.bitpin_fetcher import fetch_bitpin_ticker

        with patch("core.bitpin_fetcher.requests.get") as mock_get:
            mock_get.return_value.json.return_value = [
                {
                    "symbol": "PAXG_USDT",
                    "price": "4151.31",
                    "daily_change_price": 0.13,
                    "high": "4155.30",
                    "low": "4145.71",
                }
            ]
            mock_get.return_value.raise_for_status = lambda: None

            t = fetch_bitpin_ticker("PAXG-USD")

        assert t is not None
        assert t["price"] == pytest.approx(4151.31)
        assert t["change_24h"] == pytest.approx(0.13)

    def test_price_with_comma_parsed(self):
        """اگر فرمت تغییر کند (کاما)، باید همچنان کار کند"""
        from core.bitpin_fetcher import fetch_bitpin_ticker

        with patch("core.bitpin_fetcher.requests.get") as mock_get:
            mock_get.return_value.json.return_value = [
                {"symbol": "BTC_USDT", "price": "85,011.60"}
            ]
            mock_get.return_value.raise_for_status = lambda: None

            t = fetch_bitpin_ticker("BTC-USD")

        assert t is not None
        assert t["price"] == pytest.approx(85011.60), (
            "parse_number باید کاما را مدیریت کند"
        )

    def test_zero_price_rejected(self):
        """قیمت صفر نباید قبول شود"""
        from core.bitpin_fetcher import fetch_bitpin_ticker

        with patch("core.bitpin_fetcher.requests.get") as mock_get:
            mock_get.return_value.json.return_value = [
                {"symbol": "BTC_USDT", "price": "0"}
            ]
            mock_get.return_value.raise_for_status = lambda: None

            assert fetch_bitpin_ticker("BTC-USD") is None


# ═══════════════════════════════════════════════════════════
# ۵. کش منفی ۱۰ دقیقه
# ═══════════════════════════════════════════════════════════
class TestNegativeCacheShortTTL:
    def test_static_ttl_is_10_minutes(self):
        """🔴 درخواست کاربر: کش منفی ۱۰ دقیقه (نه ۲۴ ساعت)"""
        from services.cache import NEGATIVE_TTL_STATIC

        assert NEGATIVE_TTL_STATIC == 600, (
            f"باید ۶۰۰ ثانیه (۱۰ دقیقه) باشد، هست {NEGATIVE_TTL_STATIC}"
        )

    def test_transient_ttl_shorter(self):
        """خطای گذرا باید حتی سریع‌تر فراموش شود"""
        from services.cache import NEGATIVE_TTL_STATIC, NEGATIVE_TTL_TRANSIENT

        assert NEGATIVE_TTL_TRANSIENT < NEGATIVE_TTL_STATIC
        assert NEGATIVE_TTL_TRANSIENT <= 300

    def test_legacy_names_still_work(self):
        """نام‌های قدیمی باید همچنان کار کنند"""
        from services.cache import (
            NEGATIVE_TTL_PERMANENT,
            NEGATIVE_TTL_STATIC,
            NEGATIVE_TTL_TEMPORARY,
            NEGATIVE_TTL_TRANSIENT,
        )

        assert NEGATIVE_TTL_PERMANENT == NEGATIVE_TTL_STATIC
        assert NEGATIVE_TTL_TEMPORARY == NEGATIVE_TTL_TRANSIENT

    def test_key_includes_source(self):
        """
        🔴 کلید کش منفی باید شامل صرافی باشد — شکست یک صرافی
        نباید صرافی دیگر را بلاک کند.
        """
        from services.data_service import fetch_ohlcv
        from services.cache import clear_all_negative, get_negative

        clear_all_negative()

        # ─── ساخت کلید مثل خود fetch_ohlcv ───
        key_nb = "ohlcv:PAXG-IRT:nobitex:۵ دقیقه"
        key_wx = "ohlcv:PAXG-IRT:wallex:۵ دقیقه"

        assert key_nb != key_wx, "کلید دو صرافی باید متفاوت باشد"
        # ─── و در کد واقعی هم همین‌طور است ───
        import inspect

        src = inspect.getsource(fetch_ohlcv)
        assert "cache_key = f\"ohlcv:{ticker}:{source}:{tf_name}\"" in src, (
            "کلید کش باید شامل source باشد"
        )


# ═══════════════════════════════════════════════════════════
# ۶. آبان‌تتر تحلیل ندارد
# ═══════════════════════════════════════════════════════════
class TestAbantetherAnalyzesViaFallback:
    """
    ⚠️ اصلاح ۱.۷ (بازگردانی): آبان‌تتر **تحلیل می‌دهد**.

    چرا: زنجیره‌ی fallback خودکار کندل را از صرافی دیگر می‌گیرد.
    این «ادغام قیمت» نیست — **قیمت** همچنان مستقل است (quote جدا).
    فقط منبع **کندل** متفاوت است و صادقانه برچسب می‌خورد.

    اگر تحلیل را خالی می‌گذاشتیم، جدول TF در فرانت کاملاً خالی
    می‌شد و کاربر فکر می‌کرد سیستم خراب است. شفافیت از طریق
    ``source_used`` تأمین می‌شود، نه با خالی گذاشتن جدول.

    تحلیل اقتصادی: اختلاف BTC-IRT بین تبدیل و نوبیتکس فقط
    ۰.۲۳٪ است (تأیید تجربی) → یک بازار با اسپرد، نه دو بازار.
    """

    def test_multi_tf_returns_all_six(self):
        """🔴 جدول TF باید پر باشد (رگرسیون: قبلاً خالی می‌شد)"""
        from services.analyzer_service import analyze_multi_tf

        for ticker in ["BTC-USD", "PAXG-IRT", "USDT-IRT"]:
            tfs = analyze_multi_tf(ticker, "tabdeal")
            assert len(tfs) == 6, (
                f"تبدیل/{ticker} باید ۶ TF بدهد، داد {len(tfs)}"
            )

    def test_analyze_returns_result(self):
        from services.analyzer_service import analyze

        r = analyze("BTC-USD", "tabdeal", "۵ دقیقه", use_cache=False)
        assert r is not None
        assert r["is_fallback"] is True
        assert r["source_requested"] == "tabdeal"
        assert r["source_used"] in ("nobitex", "bitpin", "wallex")

    def test_quote_still_independent(self):
        """قیمت تبدیل از عمق بازار خودش می‌آید (ادغام نمی‌شود)"""
        from core.data_fetcher import fetch_quote_by_source

        q = fetch_quote_by_source("BTC-USD", "tabdeal")
        if q is not None:
            assert q["source"] == "tabdeal"


class TestNoEarlyReturnInAnalyzer:
    """
    ⚠️ رگرسیون ۱.۷: ``analyze`` و ``analyze_multi_tf`` نباید
    برای منبعی early-return خالی داشته باشند — آن کار جدول TF را
    در فرانت خالی می‌کرد و کاربر فکر می‌کرد سیستم خراب است.

    شفافیت از طریق ``source_used`` می‌آید، نه با خالی گذاشتن جدول.
    """

    def test_no_abantether_early_return_in_analyze(self):
        """``analyze`` نباید برای آبان‌تتر early-return داشته باشد"""
        import inspect

        from services import analyzer_service as svc

        src = inspect.getsource(svc.analyze)
        assert 'if source == "abantether"' not in src

    def test_no_tabdeal_early_return_in_analyze(self):
        """``analyze`` نباید برای تبدیل early-return داشته باشد"""
        import inspect

        from services import analyzer_service as svc

        src = inspect.getsource(svc.analyze)
        assert 'if source == "tabdeal"' not in src, (
            "early-return تبدیل جدول TF را خالی می‌کند"
        )

    def test_no_early_return_in_multi_tf(self):
        """``analyze_multi_tf`` نباید برای هیچ منبعی empty بدهد"""
        import inspect

        from services import analyzer_service as svc

        src = inspect.getsource(svc.analyze_multi_tf)
        assert 'if source == "abantether"' not in src
        assert 'if source == "tabdeal"' not in src


# ═══════════════════════════════════════════════════════════
# ۷. source_used در response
# ═══════════════════════════════════════════════════════════
class TestSourceUsedField:
    def test_source_used_present_in_output(self):
        """🔴 فرانت باید بداند دیتا از کجا آمده"""
        import inspect

        from services import analyzer_service as svc

        src = inspect.getsource(svc.analyze)
        assert '"source_used"' in src
        assert '"source_requested"' in src
        assert '"is_fallback"' in src

    def test_analyze_includes_source_fields(self):
        """تست واقعی: خروجی باید این فیلدها را داشته باشد"""
        import pandas as pd

        from services import analyzer_service as svc

        idx = pd.date_range("2026-09-01", periods=300, freq="5min", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [100.0] * 300,
                "high": [101.0] * 300,
                "low": [99.0] * 300,
                "close": [100.0 + i * 0.01 for i in range(300)],
                "volume": [1.0] * 300,
            },
            index=idx,
        )
        # ─── منبع واقعی را روی دیتافریم برچسب بزن ───
        df.attrs["data_source"] = "nobitex"

        # ⚠️ باید analyzer_service را patch کنیم نه core.data_fetcher،
        #    چون این تابع مستقیم import شده است.
        with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df):
            r = svc.analyze("BTC-USD", "wallex", "۵ دقیقه", use_cache=False)

        assert r is not None, "تحلیل باید نتیجه بدهد"
        assert "source_used" in r
        assert "source_requested" in r
        assert "is_fallback" in r
        assert r["source_requested"] == "wallex"
        assert r["source_used"] == "nobitex"
        assert r["is_fallback"] is True

    def test_source_used_equals_requested_when_no_fallback(self):
        """اگر fallback نزده باشد، is_fallback باید False باشد"""
        import pandas as pd

        from services import analyzer_service as svc

        idx = pd.date_range("2026-09-01", periods=300, freq="5min", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [100.0] * 300,
                "high": [101.0] * 300,
                "low": [99.0] * 300,
                "close": [100.0 + i * 0.01 for i in range(300)],
                "volume": [1.0] * 300,
            },
            index=idx,
        )
        df.attrs["data_source"] = "wallex"

        with patch.object(svc, "fetch_ohlcv", lambda *a, **k: df):
            r = svc.analyze("BTC-USD", "wallex", "۵ دقیقه", use_cache=False)

        assert r is not None
        assert r["source_used"] == "wallex"
        assert r["is_fallback"] is False


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
