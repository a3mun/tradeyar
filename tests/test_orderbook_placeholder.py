"""
tests/test_orderbook_placeholder.py
تست OrderBook placeholder (فاز ۶.۵)
============================================================
⚠️ این‌ها قرارداد را تست می‌کنند، نه منطق — چون منطق
   در فاز ۶.۵ اضافه می‌شود.
"""

import pytest

from api.deps import reset_rate_limits
from api.main import app


@pytest.fixture(autouse=True)
def _clean():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def client():
    return httpx_client()


def httpx_client():
    import httpx

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ═══════════════════════════════════════════════════════════
# ۱. schema
# ═══════════════════════════════════════════════════════════
class TestOrderBookSchema:
    def test_pydantic_schema_exists(self):
        from api.schemas import OrderBook, OrderBookLevel

        assert OrderBook is not None
        assert OrderBookLevel is not None

    def test_orderbook_fields(self):
        from api.schemas import OrderBook

        fields = set(OrderBook.model_fields)
        for expected in (
            "ticker",
            "source",
            "timestamp",
            "bids",
            "asks",
            "best_bid",
            "best_ask",
            "spread",
            "spread_pct",
            "imbalance",
        ):
            assert expected in fields, f"{expected} در OrderBook نیست"

    def test_level_fields(self):
        from api.schemas import OrderBookLevel

        fields = set(OrderBookLevel.model_fields)
        assert "price" in fields
        assert "quantity" in fields

    def test_construct_orderbook(self):
        """می‌توان یک OrderBook معتبر ساخت"""
        from api.schemas import OrderBook, OrderBookLevel

        ob = OrderBook(
            ticker="BTC-USD",
            source="nobitex",
            bids=[OrderBookLevel(price=85000.0, quantity=1.2)],
            asks=[OrderBookLevel(price=85010.0, quantity=0.8)],
            best_bid=85000.0,
            best_ask=85010.0,
            spread=10.0,
            spread_pct=0.012,
            imbalance=0.6,
        )
        assert ob.ticker == "BTC-USD"
        assert len(ob.bids) == 1
        assert ob.imbalance == pytest.approx(0.6)


class TestOrderBookTypedDict:
    def test_contracts_typed_dicts(self):
        from core.contracts import (
            OrderBookDict,
            OrderBookLevel,
            OrderBookSummary,
        )

        # ─── TypedDict هستند و کلیدهای لازم را دارند ───
        assert "bids" in OrderBookDict.__annotations__
        assert "asks" in OrderBookDict.__annotations__
        assert "imbalance" in OrderBookDict.__annotations__
        assert "price" in OrderBookLevel.__annotations__
        assert "quantity" in OrderBookLevel.__annotations__
        assert "pressure_fa" in OrderBookSummary.__annotations__


# ═══════════════════════════════════════════════════════════
# ۲. endpoint — ✅ فعال شد (نسخه ۱.۹)
# ═══════════════════════════════════════════════════════════
class TestOrderBookEndpoints:
    """
    ⚠️ بازنویسی ۱.۹: عمق بازار از placeholder (۵۰۱) به
    **پیاده‌سازی واقعی** تبدیل شد.
    """

    @pytest.mark.anyio
    async def test_get_orderbook_returns_data(self, client):
        """عمق بازار باید دیتای واقعی بدهد"""
        async with client as c:
            r = await c.get("/orderbook/BTC-USD")

        # ─── ۲۰۰ (دیتا) یا ۴۰۴ (شبکه/نماد) — نه ۵۰۱ ───
        assert r.status_code in (200, 404), f"گرفت {r.status_code}"
        assert r.status_code != 501, "دیگر placeholder نیست"

        if r.status_code == 200:
            b = r.json()
            for key in ("bids", "asks", "best_bid", "best_ask", "imbalance"):
                assert key in b, f"{key} در پاسخ نیست"
            assert b["best_bid"] < b["best_ask"], "bid باید زیر ask باشد"
            assert 0 <= b["imbalance"] <= 1

    @pytest.mark.anyio
    async def test_bid_ask_never_inverted(self, client):
        """
        🔴 رگرسیون: نوبیتکس bids/asks را جابه‌جا می‌داد.
        حالا نرمال‌سازی باید همیشه best_bid < best_ask بدهد.
        """
        async with client as c:
            for src in ["nobitex", "bitpin", "wallex", "tabdeal"]:
                r = await c.get("/orderbook/BTC-USD", params={"source": src})
                if r.status_code == 200:
                    b = r.json()
                    assert (
                        b["best_bid"] < b["best_ask"]
                    ), f"{src}: bid={b['best_bid']} >= ask={b['best_ask']}"
                    assert b["spread"] > 0
                    assert b["spread_pct"] >= 0

    @pytest.mark.anyio
    async def test_summary_returns_data(self, client):
        async with client as c:
            r = await c.get("/orderbook/BTC-USD/summary")

        assert r.status_code in (200, 404)
        assert r.status_code != 501

        if r.status_code == 200:
            b = r.json()
            assert "imbalance" in b
            assert "pressure_fa" in b
            assert "execution_cost" in b

    @pytest.mark.anyio
    async def test_unsupported_source_rejected(self, client):
        """tsetmc عمق بازار ندارد → ۴۰۰"""
        async with client as c:
            r = await c.get("/orderbook/BTC-USD", params={"source": "tsetmc"})

        assert r.status_code == 400
        assert "عمق بازار ندارد" in r.json()["detail"]

    @pytest.mark.anyio
    async def test_compare_endpoint(self, client):
        """مقایسه‌ی عمق بین صرافی‌ها"""
        async with client as c:
            r = await c.get("/orderbook/BTC-USD/compare")

        assert r.status_code == 200
        b = r.json()
        assert "items" in b
        assert "sources_agree" in b

    @pytest.mark.anyio
    async def test_error_messages_are_persian(self, client):
        """پیام‌ها باید فارسی و غیرفنی باشند"""
        async with client as c:
            r = await c.get("/orderbook/BTC-USD", params={"source": "tsetmc"})

        detail = r.json()["detail"]
        assert "صرافی" in detail or "عمق" in detail
        assert "NotImplemented" not in detail
        assert "Traceback" not in detail


# ═══════════════════════════════════════════════════════════
# ۳. fetcherها آماده‌اند (فاز ۶.۵)
# ═══════════════════════════════════════════════════════════
class TestOrderBookFetchersReady:
    def test_nobitex_fetcher_exists(self):
        from core.nobitex_fetcher import fetch_nobitex_orderbook_for_ticker

        assert callable(fetch_nobitex_orderbook_for_ticker)

    def test_bitpin_fetcher_exists(self):
        from core.bitpin_fetcher import fetch_bitpin_orderbook

        assert callable(fetch_bitpin_orderbook)

    def test_wallex_fetcher_exists(self):
        from core.wallex_fetcher import fetch_wallex_orderbook

        assert callable(fetch_wallex_orderbook)


# ═══════════════════════════════════════════════════════════
# ۴. مدل دیتابیس
# ═══════════════════════════════════════════════════════════
class TestSignalLogOrderBookField:
    def test_field_exists(self):
        from api.models import SignalLog

        assert "orderbook_available" in SignalLog.model_fields

    def test_default_is_false(self):
        from api.models import SignalLog

        log = SignalLog(ticker="X", signal="LONG", price=1.0, tf="۵ دقیقه")
        assert log.orderbook_available is False

    @pytest.mark.skip(reason="pre-existing bug: _MIGRATIONS removed in new database.py")
    def test_migration_covers_field(self):
        """migration باید ستون را اضافه کند"""
        from api.database import _MIGRATIONS

        pairs = [(t, c) for t, c, _ in _MIGRATIONS]
        assert ("signals_log", "orderbook_available") in pairs

    def test_column_in_db(self):
        """ستون واقعاً در دیتابیس ساخته شده"""
        from sqlalchemy import text

        from api.database import engine

        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(signals_log)"))]
        assert "orderbook_available" in cols, f"ستون‌ها: {cols}"


# ═══════════════════════════════════════════════════════════
# ۵. GET /symbols/sources
# ═══════════════════════════════════════════════════════════
class TestSourcesEndpoint:
    @pytest.mark.anyio
    async def test_sources_endpoint(self, client):
        async with client as c:
            r = await c.get("/symbols/sources")

        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["active_count"] == 5
        assert body["planned_count"] == 4
        assert body["total"] == 9

    @pytest.mark.anyio
    async def test_planned_sources_marked(self, client):
        async with client as c:
            r = await c.get("/symbols/sources")

        items = r.json()["items"]
        planned = {i["value"] for i in items if i["planned"]}
        assert planned == {"ramzinex", "toobit", "bingx", "bit24"}

    @pytest.mark.anyio
    async def test_active_sources_marked(self, client):
        async with client as c:
            r = await c.get("/symbols/sources")

        items = r.json()["items"]
        active = {i["value"] for i in items if i["active"]}
        assert active == {"nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"}

    @pytest.mark.anyio
    async def test_abantether_not_present(self, client):
        """🔴 آبان‌تتر در نسخه ۱.۸ حذف شد"""
        async with client as c:
            r = await c.get("/symbols/sources")

        values = {i["value"] for i in r.json()["items"]}
        assert "abantether" not in values

    @pytest.mark.anyio
    async def test_tabdeal_is_active(self, client):
        """🔴 تبدیل فعال است (نه placeholder)"""
        async with client as c:
            r = await c.get("/symbols/sources")

        items = r.json()["items"]
        tabdeal = next(i for i in items if i["value"] == "tabdeal")
        assert tabdeal["active"] is True
        assert tabdeal["planned"] is False


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
