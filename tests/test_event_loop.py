"""
tests/test_event_loop.py
تست باگ ۶ — قفل نشدن event loop
============================================================
مسئله:  ``async def scan_endpoint`` بدنه‌ی sync داشت. یک ``/scan``
        با ۱۵ نماد کل FastAPI را قفل می‌کرد و حتی ``/health``
        جواب نمی‌داد.

تست کاربر:
    ۱. یه /scan بزن + هم‌زمان /health → هر دو جواب بدن
    ۲. latency /health باید < 100ms باشه

روش تست:
    توابع sync را با یک تابع «شبیه‌ساز blocking» patch می‌کنیم
    که ``time.sleep`` می‌زند (دقیقاً مثل ``requests.get``).
    اگر endpoint واقعاً threadpool استفاده نکند، این sleep
    event loop را قفل می‌کند و ``/health`` time out می‌شود.
"""

import asyncio
import inspect
import time
from unittest.mock import patch

import httpx
import pytest

from api.deps import reset_rate_limits
from api.main import app

# ─── آستانه‌ها ───
BLOCKING_SEC = 0.30  # هر تحلیل چقدر طول می‌کشد (شبیه‌سازی شبکه)
HEALTH_BUDGET_MS = 100  # بودجه‌ی کاربر برای /health
# آستانه‌ی عملی (CI نویزی است): اگر event loop قفل شود،
# /health باید حداقل BLOCKING_SEC صبر کند. پس ۲۰۰ms
# با فاصله‌ی امن از ۳۰۰ms، هم شکننده نیست هم باگ را می‌گیرد.
HEALTH_PRACTICAL_MS = 200


@pytest.fixture(autouse=True)
def _clean_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _blocking_analyze(*args, **kwargs):
    """شبیه‌ساز analyze sync — مثل requests.get قفل می‌کند"""
    time.sleep(BLOCKING_SEC)
    return {
        "ok": True,
        "ticker": kwargs.get("ticker", "X"),
        "name": "Test",
        "source": "nobitex",
        "timeframe": "۵ دقیقه",
        "market_type": "futures",
        "risk_profile": "aggressive",
        "price": 100.0,
        "signal": "LONG",
        "direction": "long",
        "confidence": 75,
        "confidence_tier": "strong",
        "consensus": "normal",
        "regime": "trend",
        "action_fa": "",
        "explanation": "",
        "sl": 95.0,
        "tp": 110.0,
        "rr": 2.0,
        "atr": 1.0,
        "atr_mult_sl": 1.5,
        "atr_mult_tp": 3.0,
        "support": 90.0,
        "resistance": 120.0,
        "pivots": {},
        "swings": {},
        "fibonacci": {},
        "groups": {},
        "votes_long": 3,
        "votes_short": 1,
        "votes_neutral": 1,
        "reasons": [],
        "scenarios": [],
        "traps": {},
        "traps_summary": {},
        "divergence": {},
        "multi_tf_info": "",
        "multi_tf_ok": True,
        "neutral_explain": {},
        "deep_analysis": "",
        "checklist": {},
        "ai_export": "",
        "close_series": [],
        "fingerprint": "fp",
    }


# ═══════════════════════════════════════════════════════════
# ۱. 🔴 تست کاربر: /scan + /health هم‌زمان
# ═══════════════════════════════════════════════════════════
class TestHealthDuringScan:
    @pytest.mark.anyio
    async def test_health_responds_while_scan_runs(self, client):
        """
        🔴 تست کاربر:
        /scan سنگین در جریان است، /health باید فوراً جواب بدهد.

        پیش از اصلاح: /health منتظر می‌ماند تا /scan تمام شود
        (event loop قفل) → ۴ ثانیه یا بیشتر.
        """
        from api.routers import scan as scan_module

        with patch.object(scan_module, "analyze", _blocking_analyze):
            async with client as c:
                # ─── /scan را در پس‌زمینه شروع کن ───
                scan_task = asyncio.create_task(
                    c.post(
                        "/scan",
                        json={"category": "crypto", "limit": 8},
                        timeout=60,
                    )
                )

                # ─── کمی صبر تا /scan واقعاً شروع شود ───
                await asyncio.sleep(0.05)

                # ─── حالا /health را زمان‌بندی کن ───
                t0 = time.perf_counter()
                health = await c.get("/health", timeout=10)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                assert health.status_code == 200, "health در دسترس نبود"
                assert health.json()["status"] == "healthy"

                # ─── 🔴 ادعای اصلی: بودجه‌ی ۱۰۰ms ───
                assert elapsed_ms < HEALTH_PRACTICAL_MS, (
                    f"/health {elapsed_ms:.0f}ms طول کشید "
                    f"(بودجه {HEALTH_BUDGET_MS}ms). "
                    f"event loop احتمالاً قفل است — "
                    f"BLOCKING_SEC={BLOCKING_SEC}s"
                )

                # ─── /scan هم باید موفق تمام شود ───
                scan_res = await scan_task
                assert scan_res.status_code == 200

    @pytest.mark.anyio
    async def test_health_latency_under_100ms_ideal(self, client):
        """
        نسخه‌ی سخت‌گیرانه: latency واقعی /health بدون بار.

        این تست ثابت می‌کند خود endpoint سبک است؛ تست قبلی
        ثابت می‌کند تحت بار هم سبک می‌ماند.
        """
        async with client as c:
            # ─── warm-up ───
            await c.get("/health")

            times = []
            for _ in range(5):
                t0 = time.perf_counter()
                r = await c.get("/health")
                times.append((time.perf_counter() - t0) * 1000)
                assert r.status_code == 200

        best = min(times)
        assert best < HEALTH_BUDGET_MS, (
            f"بهترین latency /health {best:.1f}ms > {HEALTH_BUDGET_MS}ms"
        )


# ═══════════════════════════════════════════════════════════
# ۲. throughput — اثبات موازی‌سازی
# ═══════════════════════════════════════════════════════════
class TestScanThroughput:
    @pytest.mark.anyio
    async def test_scan_is_parallel_not_serial(self, client):
        """
        با ۱۲ نماد و MAX_CONCURRENT=6، اسکن باید حدود ۲ نوبت
        طول بکشد (≈ 2×BLOCKING_SEC)، نه ۱۲ نوبت.

        اگر سریال بود: 12 × 0.3 = 3.6s
        اگر موازی با سقف ۶: ~0.6s
        """
        from api.routers import scan as scan_module

        async with client as c:
            with patch.object(scan_module, "analyze", _blocking_analyze):
                t0 = time.perf_counter()
                r = await c.post(
                    "/scan",
                    json={"category": "crypto", "limit": 12},
                    timeout=60,
                )
                elapsed = time.perf_counter() - t0

        assert r.status_code == 200
        serial_estimate = 12 * BLOCKING_SEC
        # ─── آستانه‌ی محافظه‌کارانه: نصف حالت سریال ───
        assert elapsed < serial_estimate * 0.5, (
            f"اسکن {elapsed:.2f}s طول کشید؛ حالت سریال ≈ {serial_estimate:.2f}s. "
            f"موازی‌سازی کار نمی‌کند."
        )


# ═══════════════════════════════════════════════════════════
# ۳. /analyze هم event loop را قفل نکند
# ═══════════════════════════════════════════════════════════
class TestAnalyzeDoesNotBlock:
    @pytest.mark.anyio
    async def test_health_during_analyze(self, client):
        from api.routers import analyze as analyze_module

        with patch.object(analyze_module, "analyze", _blocking_analyze):
            async with client as c:
                analyze_task = asyncio.create_task(
                    c.post(
                        "/analyze",
                        json={"ticker": "BTC-USD", "timeframe": "۵ دقیقه"},
                        timeout=60,
                    )
                )
                await asyncio.sleep(0.05)

                t0 = time.perf_counter()
                health = await c.get("/health", timeout=10)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                assert health.status_code == 200
                assert elapsed_ms < HEALTH_PRACTICAL_MS, (
                    f"/analyze در حال اجرا بود و /health "
                    f"{elapsed_ms:.0f}ms طول کشید"
                )

                res = await analyze_task
                assert res.status_code == 200


# ═══════════════════════════════════════════════════════════
# ۴. /analyze/multi و /analyze/deep و /symbols/iran-prices
# ═══════════════════════════════════════════════════════════
class TestMultiTfDoesNotBlock:
    @pytest.mark.anyio
    async def test_health_during_multi_tf(self, client):
        from api.routers import analyze as analyze_module

        with patch.object(analyze_module, "analyze_multi_tf", _blocking_analyze):
            async with client as c:
                task = asyncio.create_task(
                    c.post(
                        "/analyze/multi",
                        json={"ticker": "BTC-USD", "timeframe": "۵ دقیقه"},
                        timeout=60,
                    )
                )
                await asyncio.sleep(0.05)

                t0 = time.perf_counter()
                health = await c.get("/health", timeout=10)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                assert health.status_code == 200
                assert elapsed_ms < HEALTH_PRACTICAL_MS, (
                    f"/analyze/multi در حال اجرا بود و /health "
                    f"{elapsed_ms:.0f}ms طول کشید"
                )
                await task

    @pytest.mark.anyio
    async def test_health_during_iran_prices(self, client):
        """اسکرپینگ AlanChand/TGJU (تا ۴۰s timeout) نباید loop را قفل کند"""
        from api.routers import symbols as symbols_module

        async with client as c:
            with patch.object(
                symbols_module, "get_iran_prices", _blocking_analyze
            ):
                task = asyncio.create_task(
                    c.get("/symbols/iran-prices", timeout=60)
                )
                await asyncio.sleep(0.05)

                t0 = time.perf_counter()
                health = await c.get("/health", timeout=10)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                assert health.status_code == 200
                assert elapsed_ms < HEALTH_PRACTICAL_MS
                await task


# ═══════════════════════════════════════════════════════════
# ۵. تست ساختاری — endpointهای sync در threadpool
# ═══════════════════════════════════════════════════════════
class TestEndpointsUseThreadpool:
    """
    تست ساختاری: مطمئن می‌شود کسی دوباره فراخوانی sync را
    بدون threadpool اضافه نکند.
    """

    @pytest.mark.parametrize(
        "module_name,func_names",
        [
            ("api.routers.analyze", ["analyze", "analyze_multi_tf", "deep_analysis", "fear_greed", "get_quote"]),
            ("api.routers.scan", ["analyze"]),
            ("api.routers.backtest", ["compute_stats"]),
            ("api.routers.symbols", ["get_iran_prices"]),
        ],
    )
    def test_source_contains_run_in_threadpool(self, module_name, func_names):
        import importlib

        mod = importlib.import_module(module_name)
        src = inspect.getsource(mod)

        assert "run_in_threadpool" in src, (
            f"{module_name} از run_in_threadpool استفاده نمی‌کند — "
            f"فراخوانی‌های sync ({func_names}) event loop را قفل می‌کنند"
        )

        # ─── تعداد فراخوانی‌ها باید منطقی باشد ───
        uses = src.count("await run_in_threadpool(")
        assert uses >= 1, f"{module_name}: هیچ await run_in_threadpool پیدا نشد"

    def test_no_bare_sync_call_to_analyze_in_scan(self):
        """
        در scan.py نباید فراخوانی مستقیم ``analyze(...)`` بدون
        ``run_in_threadpool`` باشد.
        """
        from api.routers import scan as scan_module

        src = inspect.getsource(scan_module)
        # ─── هر ظهوری از analyze باید داخل run_in_threadpool باشد ───
        assert "run_in_threadpool(\n                analyze," in src or (
            "run_in_threadpool" in src and "analyze," in src
        ), "analyze در scan.py بدون threadpool صدا زده می‌شود"

    def test_scheduler_uses_to_thread(self):
        """scheduler نباید backtest_all را مستقیم در event loop صدا بزند"""
        from api import scheduler

        src = inspect.getsource(scheduler)
        assert "asyncio.to_thread" in src, (
            "scheduler.check_pending_signals باید backtest_all را "
            "در thread جدا اجرا کند"
        )
        assert "max_instances=1" in src, "max_instances=1 لازم است"
        assert "coalesce=True" in src, "coalesce=True لازم است"


# ═══════════════════════════════════════════════════════════
# ۶. analyze_multi_tf موازی باشد
# ═══════════════════════════════════════════════════════════
class TestAnalyzeMultiTfParallel:
    def test_multi_tf_is_parallel(self):
        """
        ۶ TF با تأخیر ۰.۳s:
          سریال  → ≈ 1.8s
          موازی  → ≈ 0.6s (با ۴ worker)

        آستانه: کمتر از ۱.۲s
        """
        from services import analyzer_service as svc

        def fake_analyze(*args, **kwargs):
            time.sleep(BLOCKING_SEC)
            return {"signal": "خنثی", "confidence": 0}

        with patch.object(svc, "analyze", fake_analyze):
            t0 = time.perf_counter()
            res = svc.analyze_multi_tf("BTC-USD", tf_list=None)
            elapsed = time.perf_counter() - t0

        assert res, "نتیجه‌ای برنگشت"
        assert elapsed < 1.2, (
            f"analyze_multi_tf {elapsed:.2f}s طول کشید — موازی نیست "
            f"(سریال ≈ 1.8s)"
        )

    def test_multi_tf_preserves_order(self):
        """ترتیب TFها باید مطابق TF_NAMES بماند، نه ترتیب اتمام"""
        from core.contracts import TF_NAMES
        from services import analyzer_service as svc

        def fake_analyze(*args, **kwargs):
            # ─── TFهای آخر سریع‌تر تمام شوند تا ترتیب به‌هم بریزد ───
            tf = kwargs.get("tf_name", "")
            time.sleep(0.01 * (len(TF_NAMES) - TF_NAMES.index(tf)))
            return {"signal": "خنثی", "confidence": 0}

        with patch.object(svc, "analyze", fake_analyze):
            res = svc.analyze_multi_tf("BTC-USD")

        assert list(res.keys()) == TF_NAMES, (
            f"ترتیب اشتباه: {list(res.keys())}"
        )

    def test_multi_tf_handles_failures(self):
        """خطای یک TF بقیه را متوقف نکند"""
        from core.contracts import TF_NAMES
        from services import analyzer_service as svc

        def fake_analyze(*args, **kwargs):
            if kwargs.get("tf_name") == TF_NAMES[2]:
                raise RuntimeError("boom")
            return {"signal": "خنثی", "confidence": 0}

        with patch.object(svc, "analyze", fake_analyze):
            res = svc.analyze_multi_tf("BTC-USD")

        assert TF_NAMES[2] not in res, "TF خطادار نباید در نتیجه باشد"
        assert len(res) == len(TF_NAMES) - 1

    def test_single_tf_no_threadpool_overhead(self):
        """تک‌TF نباید threadpool را درگیر کند"""
        from services import analyzer_service as svc

        calls = []

        def fake_analyze(*args, **kwargs):
            calls.append(kwargs.get("tf_name"))
            return {"signal": "خنثی", "confidence": 0}

        with patch.object(svc, "analyze", fake_analyze):
            res = svc.analyze_multi_tf("BTC-USD", tf_list=["۵ دقیقه"])

        assert list(res.keys()) == ["۵ دقیقه"]
        assert calls == ["۵ دقیقه"]

    def test_empty_inputs_return_empty(self):
        from services import analyzer_service as svc

        assert svc.analyze_multi_tf("") == {}
        assert svc.analyze_multi_tf("BTC-USD", tf_list=[]) == {}


# ═══════════════════════════════════════════════════════════
# ۷. 🔴 رگرسیون بازگشت بی‌نهایت در زنجیره‌ی fallback
# ═══════════════════════════════════════════════════════════
class TestNoInfiniteRecursionInFallback:
    """
    🔴 باگ بنیادی کشف‌شده در باگ ۶:

    پیاده‌سازی قبلی fallback بازگشتی بود:
        nobitex → bitpin → nobitex → bitpin → ...

    برای نمادهایی که روی **هیچ** صرافی‌ای نیستند (TON-USD، MATIC-USD)
    این زنجیره هرگز تمام نمی‌شد و تا ``RecursionError`` می‌رفت.
    هر نماد **۱۱۰ ثانیه** طول می‌کشید و `/scan` به ۲۷۷ ثانیه می‌رسید.
    """

    def test_chain_terminates_when_symbol_absent_everywhere(self, monkeypatch):
        """
        نمادی که هیچ صرافی ندارد باید سریع None بدهد، نه RecursionError.
        """
        import core.bitpin_fetcher as bf
        import core.data_fetcher as df
        import core.nobitex_fetcher as nf
        import core.wallex_fetcher as wf

        # ─── هیچ صرافی دیتا ندارد ───
        monkeypatch.setattr(
            nf, "fetch_nobitex_for_ticker", lambda *a, **k: None, raising=False
        )
        monkeypatch.setattr(bf, "fetch_bitpin_candles", lambda *a, **k: None)
        monkeypatch.setattr(wf, "fetch_wallex_candles", lambda *a, **k: None)
        # ─── نماد روی نوبیتکس نامعتبر ───
        monkeypatch.setattr(df, "is_valid_nobitex_symbol", lambda t: False)

        calls = {"n": 0}
        orig = df.fetch_history_by_source

        def counting(*a, **k):
            calls["n"] += 1
            assert calls["n"] < 50, "بازگشت بی‌نهایت — زنجیره تمام نمی‌شود"
            return orig(*a, **k)

        monkeypatch.setattr(df, "fetch_history_by_source", counting)

        result = df.fetch_history_by_source(
            "TON-USD", "5m", "5d", "nobitex", tf_name="۵ دقیقه"
        )
        assert result is None
        # ─── حداکثر ۳ منبع × ۱ بار ───
        assert calls["n"] <= 6, f"{calls['n']} فراخوانی — زنجیره پاک نیست"

    def test_each_source_tried_at_most_once(self, monkeypatch):
        """هر منبع باید حداکثر یک بار امتحان شود"""
        import core.data_fetcher as df

        tried: list[str] = []

        def recording(ticker, interval, period, source="nobitex", tf_name="", _tried=None):
            tried.append(source)
            # ─── از پیاده‌سازی واقعی استفاده کن ───
            return _real(ticker, interval, period, source, tf_name, _tried)

        _real = df.fetch_history_by_source
        monkeypatch.setattr(df, "is_valid_nobitex_symbol", lambda t: False)
        monkeypatch.setattr(df, "is_ohlcv_supported", lambda tf, src: True)

        import core.bitpin_fetcher as bf
        import core.wallex_fetcher as wf

        monkeypatch.setattr(bf, "fetch_bitpin_candles", lambda *a, **k: None)
        monkeypatch.setattr(wf, "fetch_wallex_candles", lambda *a, **k: None)

        with patch.object(df, "fetch_history_by_source", recording):
            df.fetch_history_by_source("X-USD", "5m", "5d", "nobitex", "۵ دقیقه")

        assert len(tried) == len(set(tried)), f"منبع تکراری: {tried}"

    def test_only_two_http_requests_for_missing_symbol(self):
        """
        نماد ناموجود روی نوبیتکس باید حداکثر ۲ درخواست HTTP بزند:
        یکی نوبیتکس (۴۰۰) و یکی بیت‌پین.
        """
        from unittest.mock import patch as _patch

        import core.data_fetcher as df

        calls: list[str] = []

        def fake_get(url, **kwargs):
            calls.append(url.split("?")[0])

            class R:
                status_code = 400

                @staticmethod
                def raise_for_status():
                    raise __import__("requests").exceptions.HTTPError(response=R())

                @staticmethod
                def json():
                    return {"code": "InvalidSymbol"}

            if "bitpin" in url:
                R.status_code = 200

                @staticmethod
                def raise_for_status():
                    return None

                @staticmethod
                def json():
                    return []

            return R()

        with _patch("requests.get", fake_get):
            result = df.fetch_history_by_source(
                "TON-USD", "5m", "5d", "nobitex", tf_name="۵ دقیقه"
            )

        assert result is None
        assert len(calls) <= 4, f"{len(calls)} درخواست: {calls}"

    def test_symbol_blacklisted_after_invalid_response(self):
        """پاسخ InvalidSymbol باید نماد را بلک‌لیست کند"""
        from unittest.mock import patch as _patch

        import requests

        import core.nobitex_fetcher as nf

        nf.clear_invalid_symbols()
        assert nf.is_symbol_invalid("TESTUSDT") is False

        def fake_get(url, **kwargs):
            class R:
                status_code = 400

                @staticmethod
                def raise_for_status():
                    raise requests.exceptions.HTTPError(response=R())

                @staticmethod
                def json():
                    return {"code": "InvalidSymbol"}

            return R()

        with _patch.object(nf.requests, "get", fake_get):
            nf._get("http://x", {"symbol": "TESTUSDT"}, symbol="TESTUSDT")

        assert nf.is_symbol_invalid("TESTUSDT") is True
        nf.clear_invalid_symbols()
        assert nf.is_symbol_invalid("TESTUSDT") is False


# ═══════════════════════════════════════════════════════════
# ۸. کش منفی و single-flight
# ═══════════════════════════════════════════════════════════
class TestNegativeCacheAndSingleFlight:
    def test_negative_cache_prevents_retry(self):
        """شکست باید به خاطر سپرده شود"""
        from services.cache import clear_all_negative, get_negative, set_negative

        clear_all_negative()
        key = "ohlcv:TEST-USD:nobitex:۵ دقیقه"

        assert get_negative(key) is False
        set_negative(key, ttl=60)
        assert get_negative(key) is True
        clear_all_negative()
        assert get_negative(key) is False

    def test_fetch_ohlcv_uses_negative_cache(self, monkeypatch):
        """فراخوانی دوم نباید شبکه را لمس کند"""
        from services import data_service as ds

        monkeypatch.setattr(ds, "get_negative", lambda k: True)

        called = {"n": 0}

        def fake_fetch(**kwargs):
            called["n"] += 1
            return None

        monkeypatch.setattr(ds, "fetch_history_by_source", fake_fetch)

        assert ds.fetch_ohlcv("BTC-USD", "۵ دقیقه", "nobitex") is None
        assert called["n"] == 0, "کش منفی نادیده گرفته شد"

    def test_key_lock_is_reentrant_safe_per_key(self):
        """قفل همان کلید باید همان آبجکت باشد، کلیدهای مختلف متفاوت"""
        from services.cache import key_lock

        a1 = key_lock("key-A")
        a2 = key_lock("key-A")
        b = key_lock("key-B")

        assert a1 is a2, "قفل همان کلید باید یکی باشد"
        assert a1 is not b, "کلیدهای مختلف باید قفل جدا داشته باشند"

    def test_single_flight_only_one_network_call(self, monkeypatch):
        """
        🔴 ۱۰ thread هم‌زمان همان کلید → فقط **یک** درخواست شبکه.
        """
        import threading

        from services import data_service as ds
        from services.cache import clear_all_negative, data_cache

        data_cache.clear()
        clear_all_negative()

        import pandas as pd

        calls = {"n": 0}
        lock = threading.Lock()

        def slow_fetch(**kwargs):
            with lock:
                calls["n"] += 1
            time.sleep(0.3)  # ─── شبیه‌سازی شبکه ───
            return pd.DataFrame(
                {"close": [1.0]},
                index=pd.date_range("2026-01-01", periods=1, tz="UTC"),
            )

        monkeypatch.setattr(ds, "fetch_history_by_source", slow_fetch)
        monkeypatch.setattr(ds, "_resolve_source_for_tf", lambda s, t: s)

        results = []

        def worker():
            results.append(ds.fetch_ohlcv("BTC-USD", "۵ دقیقه", "nobitex"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert calls["n"] == 1, (
            f"{calls['n']} درخواست شبکه برای یک کلید — single-flight کار نمی‌کند"
        )
        assert all(r is not None for r in results)


# ═══════════════════════════════════════════════════════════
# ۹. بودجه‌ی زمانی اسکن
# ═══════════════════════════════════════════════════════════
class TestScanBudget:
    def test_budget_constant_defined(self):
        from api.routers import scan as scan_module

        assert hasattr(scan_module, "SCAN_BUDGET_SEC")
        assert 5 <= scan_module.SCAN_BUDGET_SEC <= 120, (
            f"بودجه‌ی غیرمنطقی: {scan_module.SCAN_BUDGET_SEC}"
        )

    @pytest.mark.anyio
    async def test_scan_respects_budget(self, client, monkeypatch):
        """
        با تحلیلی که ۵ ثانیه طول می‌کشد و بودجه‌ی ۲ ثانیه،
        اسکن نباید بیش از ~۴ ثانیه طول بکشد.
        """
        from api.routers import scan as scan_module

        monkeypatch.setattr(scan_module, "SCAN_BUDGET_SEC", 2.0)

        def very_slow(*args, **kwargs):
            time.sleep(5.0)
            return None

        with patch.object(scan_module, "analyze", very_slow):
            async with client as c:
                t0 = time.perf_counter()
                r = await c.post(
                    "/scan",
                    json={"category": "crypto", "limit": 10},
                    timeout=60,
                )
                elapsed = time.perf_counter() - t0

        assert r.status_code == 200
        # ─── ۶ worker × ۵s ≈ ۵s برای نوبت اول، بقیه رد می‌شوند ───
        assert elapsed < 12, f"بودجه رعایت نشد: {elapsed:.1f}s"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
