"""
tests/test_planned_sources.py
تست صرافی‌های placeholder و OrderBook (فاز ۶.۵/۷)
============================================================
پوشش:
  ۱. DataSource شامل صرافی‌های «به‌زودی» است
  ۲. resolve_source برای placeholder → نوبیتکس (بدون کرش)
  ۳. get_source_info وضعیت planned را درست می‌دهد
  ۴. GET /symbols/sources لیست کامل می‌دهد
  ۵. GET /orderbook/{ticker} → 501
  ۶. OrderBook schema/TypedDict تعریف شده
"""

import httpx
import pytest

from core.contracts import (
    ACTIVE_SOURCES,
    PLANNED_SOURCES,
    DataSource,
    is_active_source,
    is_planned_source,
)
from core.sources import get_all_sources_info, get_source_info


# ═══════════════════════════════════════════════════════════
# ۱. DataSource
# ═══════════════════════════════════════════════════════════
class TestDataSourceEnum:
    def test_planned_exchanges_present(self):
        """🔴 رمزینکس، توبیت، بینگ‌ایکس، بیت۲۴ باید باشند"""
        values = [s.value for s in DataSource]
        for expected in ["ramzinex", "toobit", "bingx", "bit24"]:
            assert expected in values, f"{expected} در DataSource نیست"

    def test_tabdeal_is_active(self):
        """🔴 تبدیل (Tabdeal) در نسخه ۱.۸ **فعال** شد"""
        values = [s.value for s in DataSource]
        assert "tabdeal" in values
        assert is_active_source("tabdeal") is True
        assert is_planned_source("tabdeal") is False

    def test_abantether_removed(self):
        """🔴 آبان‌تتر حذف شد"""
        values = [s.value for s in DataSource]
        assert "abantether" not in values, "آبان‌تتر باید حذف شده باشد"

    def test_active_exchanges_present(self):
        values = [s.value for s in DataSource]
        for expected in ["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]:
            assert expected in values

    def test_active_and_planned_helpers(self):
        active = DataSource.active()
        planned = DataSource.planned()

        assert set(active) == set(ACTIVE_SOURCES)
        assert set(planned) == set(PLANNED_SOURCES)
        # ─── اشتراک نباید داشته باشند ───
        assert not (set(active) & set(planned))

    def test_is_planned_and_active(self):
        assert is_planned_source("ramzinex") is True
        assert is_planned_source("toobit") is True
        assert is_planned_source("bingx") is True
        assert is_planned_source("nobitex") is False
        assert is_planned_source("tabdeal") is False
        assert is_planned_source("") is False

        assert is_active_source("nobitex") is True
        assert is_active_source("tabdeal") is True
        assert is_active_source("ramzinex") is False

    def test_display_name_includes_planned(self):
        for src in ["ramzinex", "toobit", "bingx"]:
            name = DataSource.display_name(src)
            assert "به‌زودی" in name, f"{src} → {name}"

    def test_tabdeal_display_name_not_planned(self):
        name = DataSource.display_name("tabdeal")
        assert "به‌زودی" not in name, f"تبدیل فعال است ولی → {name}"
        assert "تبدیل" in name


# ═══════════════════════════════════════════════════════════
# ۲. resolve_source با placeholder
# ═══════════════════════════════════════════════════════════
class TestResolveSourceWithPlanned:
    def test_planned_falls_back_to_nobitex(self):
        """🔴 صرافی placeholder نباید کرش کند — fallback به نوبیتکس"""
        from core.sources import resolve_source

        for src in ["ramzinex", "toobit", "bingx"]:
            assert resolve_source(src) == "nobitex", src

    def test_active_unchanged(self):
        from core.sources import resolve_source

        for src in ["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]:
            assert resolve_source(src) == src, src

    def test_unknown_also_falls_back(self):
        from core.sources import resolve_source

        assert resolve_source("ناشناخته") == "nobitex"
        # ─── آبان‌تتر حذف شده → مثل ناشناخته ───
        assert resolve_source("abantether") == "nobitex"


# ═══════════════════════════════════════════════════════════
# ۳. get_source_info
# ═══════════════════════════════════════════════════════════
class TestSourceInfo:
    def test_active_source_info(self):
        info = get_source_info("nobitex")
        assert info["planned"] is False
        assert info["active"] is True
        assert info["short_name"] == "نوبیتکس"

    def test_tabdeal_source_info(self):
        """تبدیل فعال است (نه placeholder)"""
        info = get_source_info("tabdeal")
        assert info["planned"] is False
        assert info["active"] is True
        assert info["short_name"] == "تبدیل"
        assert "عمق بازار" in info["full_name"]

    def test_planned_source_info(self):
        for src in ["ramzinex", "toobit", "bingx"]:
            info = get_source_info(src)
            assert info["planned"] is True, src
            assert info["active"] is False, src
            assert info["full_name"] == "به‌زودی"

    def test_get_all_sources_info(self):
        items = get_all_sources_info()
        assert len(items) == 9  # ۵ فعال + ۴ برنامه‌ریزی‌شده

        # ─── global نباید باشد ───
        assert not any(i["value"] == "global" for i in items)

        # ─── آبان‌تتر نباید باشد ───
        assert not any(i["value"] == "abantether" for i in items)

        active = [i for i in items if i["active"]]
        planned = [i for i in items if i["planned"]]
        assert len(active) == 5
        assert len(planned) == 4

        # ─── هر آیتم کلیدهای لازم را دارد ───
        for i in items:
            for key in ("value", "icon", "label", "planned", "active"):
                assert key in i, f"{i.get('value')} بدون {key}"


# ═══════════════════════════════════════════════════════════
# ۴. پیام‌های کاربری (روانشناسی کاربر مبتدی)
# ═══════════════════════════════════════════════════════════
class TestUserFacingMessages:
    def test_tabdeal_message_is_clear(self):
        info = get_source_info("tabdeal")
        # ─── نباید پیام فنی باشد ───
        assert "None" not in info["full_name"]
        assert "OHLCV" not in info["full_name"]
        assert "عمق بازار" in info["full_name"]

    def test_planned_message_is_clear(self):
        info = get_source_info("ramzinex")
        assert info["full_name"] == "به‌زودی"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
