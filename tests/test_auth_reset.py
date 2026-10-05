"""
tests/test_auth_reset.py
تست باگ ۴ — احراز هویت DELETE /backtest/reset
============================================================
پوشش:
  ۱. بدون هدر → 401
  ۲. هدر غلط → 403
  ۳. ADMIN_API_KEY تنظیم‌نشده → 503 (fail-closed)
  ۴. هدر درست → 200 و حذف واقعی
  ۵. مقایسه‌ی زمان-ثابت (ساختار کد)
  ۶. audit log
  ۷. endpointهای دیگر دست‌نخورده (فقط reset محافظت‌شده)
"""

import logging

import httpx
import pytest
from sqlmodel import Session, select

from api.config import settings
from api.database import engine
from api.deps import reset_rate_limits
from api.main import app
from api.models import SignalLog

ADMIN_KEY = "test-admin-key-12345"


@pytest.fixture(autouse=True)
def _clean_state():
    """دیتابیس و rate limit را قبل هر تست پاک می‌کند"""
    reset_rate_limits()
    with Session(engine) as s:
        for row in s.exec(select(SignalLog)).all():
            s.delete(row)
        s.commit()
    yield
    with Session(engine) as s:
        for row in s.exec(select(SignalLog)).all():
            s.delete(row)
        s.commit()
    reset_rate_limits()


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def seeded():
    """۳ سیگنال نمونه در دیتابیس"""
    with Session(engine) as s:
        for i in range(3):
            s.add(
                SignalLog(
                    ticker=f"TST{i}-USD",
                    name=f"Test {i}",
                    signal="LONG",
                    direction="long",
                    price=100.0,
                    sl=95.0,
                    tp=110.0,
                    tf="۵ دقیقه",
                    source="nobitex",
                )
            )
        s.commit()
    return 3


def _count() -> int:
    with Session(engine) as s:
        return len(s.exec(select(SignalLog)).all())


# ═══════════════════════════════════════════════════════════
# ۱. بدون هدر
# ═══════════════════════════════════════════════════════════
class TestResetRequiresHeader:
    @pytest.mark.anyio
    async def test_no_header_returns_401(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete("/backtest/reset")

        assert r.status_code == 401, f"انتظار 401، گرفت {r.status_code}"
        assert "X-API-Key" in r.json()["detail"]
        assert _count() == seeded, "بدون احراز هویت نباید چیزی حذف شود"

    @pytest.mark.anyio
    async def test_empty_header_returns_401(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete("/backtest/reset", headers={"X-API-Key": ""})

        assert r.status_code == 401
        assert _count() == seeded


# ═══════════════════════════════════════════════════════════
# ۲. هدر غلط
# ═══════════════════════════════════════════════════════════
class TestResetWrongKey:
    @pytest.mark.anyio
    async def test_wrong_key_returns_403(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": "wrong-key"}
            )

        assert r.status_code == 403
        assert _count() == seeded, "با کلید غلط نباید چیزی حذف شود"

    @pytest.mark.anyio
    async def test_prefix_of_correct_key_rejected(self, client, seeded, monkeypatch):
        """کلید ناقص نباید قبول شود"""
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": ADMIN_KEY[:-1]}
            )
        assert r.status_code == 403

    @pytest.mark.anyio
    async def test_case_sensitive(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": ADMIN_KEY.upper()}
            )
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════
# ۳. ADMIN_API_KEY تنظیم‌نشده → fail-closed
# ═══════════════════════════════════════════════════════════
class TestFailClosed:
    @pytest.mark.anyio
    async def test_unset_key_blocks_everyone(self, client, seeded, monkeypatch):
        """
        🔴 مهم‌ترین تست امنیتی:
        اگر ادمین کلید را تنظیم نکرده باشد، endpoint باید کاملاً
        مسدود باشد — نه اینکه برای همه باز بماند.
        """
        monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
        async with client as c:
            # حتی با ارسال هر کلیدی
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": "anything"}
            )

        assert r.status_code == 503, f"انتظار 503، گرفت {r.status_code}"
        assert _count() == seeded

    @pytest.mark.anyio
    async def test_unset_key_without_header_also_blocked(
        self, client, seeded, monkeypatch
    ):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
        async with client as c:
            r = await c.delete("/backtest/reset")
        assert r.status_code == 503


# ═══════════════════════════════════════════════════════════
# ۴. کلید درست → حذف واقعی
# ═══════════════════════════════════════════════════════════
class TestResetSuccess:
    @pytest.mark.anyio
    async def test_correct_key_deletes(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": ADMIN_KEY}
            )

        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["deleted"] == seeded
        assert _count() == 0, "همه‌ی سیگنال‌ها باید حذف شده باشند"

    @pytest.mark.anyio
    async def test_reset_on_empty_db(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"X-API-Key": ADMIN_KEY}
            )
        assert r.status_code == 200
        assert r.json()["deleted"] == 0

    @pytest.mark.anyio
    async def test_header_name_case_insensitive(self, client, seeded, monkeypatch):
        """HTTP headerها case-insensitive هستند"""
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.delete(
                "/backtest/reset", headers={"x-api-key": ADMIN_KEY}
            )
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# ۵. audit log
# ═══════════════════════════════════════════════════════════
class TestAuditLog:
    @pytest.mark.anyio
    async def test_failed_attempt_is_logged(
        self, client, seeded, monkeypatch, caplog
    ):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        with caplog.at_level(logging.WARNING, logger="api.deps"):
            async with client as c:
                await c.delete("/backtest/reset", headers={"X-API-Key": "bad"})

        assert any("کلید اشتباه" in r.message for r in caplog.records), (
            f"تلاش ناموفق لاگ نشد: {[r.message for r in caplog.records]}"
        )

    @pytest.mark.anyio
    async def test_success_is_logged(self, client, seeded, monkeypatch, caplog):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        with caplog.at_level(logging.INFO, logger="api.deps"):
            async with client as c:
                await c.delete(
                    "/backtest/reset", headers={"X-API-Key": ADMIN_KEY}
                )

        assert any("تأیید شد" in r.message for r in caplog.records)


# ═══════════════════════════════════════════════════════════
# ۶. ساختار کد — مقایسه‌ی زمان-ثابت
# ═══════════════════════════════════════════════════════════
class TestConstantTimeComparison:
    def test_uses_secrets_compare_digest(self):
        """
        مقایسه‌ی کلید باید با secrets.compare_digest باشد،
        نه `==` که در برابر timing attack آسیب‌پذیر است.
        """
        import inspect

        from api import deps

        src = inspect.getsource(deps.require_admin)
        assert "compare_digest" in src, (
            "باید از secrets.compare_digest استفاده کند"
        )
        assert "x_api_key ==" not in src, "مقایسه‌ی مستقیم ناامن است"

    def test_dependency_is_async(self):
        import inspect

        from api import deps

        assert inspect.iscoroutinefunction(deps.require_admin)


# ═══════════════════════════════════════════════════════════
# ۷. بقیه‌ی endpointها دست‌نخورده
# ═══════════════════════════════════════════════════════════
class TestOtherEndpointsStillOpen:
    @pytest.mark.anyio
    async def test_history_does_not_need_key(self, client, seeded, monkeypatch):
        """GET /backtest/history نباید احراز هویت بخواهد (فقط خواندن)"""
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.get("/backtest/history")

        assert r.status_code == 200
        assert len(r.json()["items"]) == seeded

    @pytest.mark.anyio
    async def test_stats_does_not_need_key(self, client, seeded, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.get("/backtest")

        assert r.status_code == 200
        assert "stats" in r.json()

    @pytest.mark.anyio
    async def test_health_does_not_need_key(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
        async with client as c:
            r = await c.get("/health")
        assert r.status_code == 200


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
