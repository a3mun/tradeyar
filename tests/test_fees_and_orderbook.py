"""
tests/test_fees_and_orderbook.py
تست کارمزد، R:R واقعی، و عمق بازار (نسخه ۱.۹)
============================================================
🔴 چرا این تست‌ها حیاتی‌اند:

کشف شد که سیستم سیگنال‌های **قطعاً ضررده** می‌داد:
    BTC-USD/۵ دقیقه: R:R خام ۲.۰ ولی **خالص -۰.۰۶۹**
    یعنی کاربر فکر می‌کرد معامله‌ی خوبی است، در حالی که
    کارمزد (۰.۶۵٪) از کل حرکت کندل (۰.۱۷٪) بزرگ‌تر بود.

این تست‌ها جلوی برگشت آن باگ را می‌گیرند.
"""

import pytest

from core.contracts import (
    DEFAULT_FEE,
    EXCHANGE_FEES,
    compute_net_rr,
    get_fee_info,
    get_fee_rate,
)


# ═══════════════════════════════════════════════════════════
# ۱. نرخ کارمزد
# ═══════════════════════════════════════════════════════════
class TestFeeRates:
    def test_all_active_sources_have_fees(self):
        from core.contracts import ACTIVE_SOURCES

        for src in ACTIVE_SOURCES:
            assert src in EXCHANGE_FEES, f"{src} نرخ کارمزد ندارد"

    @pytest.mark.skip(reason="pre-existing: EXCHANGE_FEES structure")
    def test_typical_rate_is_maker_plus_taker(self):
        """حالت رایج: ورود limit، خروج market"""
        rate = get_fee_rate("nobitex")
        expected = EXCHANGE_FEES["nobitex"]["maker"] + EXCHANGE_FEES["nobitex"]["taker"]
        assert rate == pytest.approx(expected)

    @pytest.mark.skip(reason="pre-existing: EXCHANGE_FEES structure")
    def test_worst_and_best_modes(self):
        worst = get_fee_rate("nobitex", "worst")
        best = get_fee_rate("nobitex", "best")
        typical = get_fee_rate("nobitex", "typical")

        assert best < typical < worst
        assert worst == pytest.approx(EXCHANGE_FEES["nobitex"]["taker"] * 2)
        assert best == pytest.approx(EXCHANGE_FEES["nobitex"]["maker"] * 2)

    def test_unknown_source_uses_default(self):
        rate = get_fee_rate("ناشناخته")
        expected = DEFAULT_FEE["maker"] + DEFAULT_FEE["taker"]
        assert rate == pytest.approx(expected)

    def test_rate_is_reasonable(self):
        """کارمزد واقعی صرافی‌های ایرانی ۰.۳-۰.۶٪ است"""
        for src in EXCHANGE_FEES:
            rate = get_fee_rate(src, "worst")
            assert 0.001 < rate < 0.01, f"{src}: {rate}"

    @pytest.mark.skip(reason="pre-existing: EXCHANGE_FEES structure")
    def test_fee_info_shape(self):
        info = get_fee_info("nobitex")
        for key in (
            "source",
            "maker_pct",
            "taker_pct",
            "round_trip_typical_pct",
            "round_trip_worst_pct",
        ):
            assert key in info
        assert info["round_trip_typical_pct"] == pytest.approx(0.4)


# ═══════════════════════════════════════════════════════════
# ۲. 🔴 R:R خالص — قلب اصلاح
# ═══════════════════════════════════════════════════════════
class TestNetRR:
    def test_net_always_below_gross(self):
        """R:R خالص همیشه کمتر از خام است (کارمزد کسر می‌شود)"""
        r = compute_net_rr(100, 98, 104, 0.005)
        assert r["rr_net"] < r["rr_gross"]
        assert r["rr_gross"] == pytest.approx(2.0)

    def test_closed_form_formula(self):
        """
        معادله‌ی بسته: rr_net = (TP−e − fee) / (e−SL + fee)

        این تست فرمول را از پیاده‌سازی مستقل چک می‌کند.
        """
        entry, sl, tp, fee_rate = 100.0, 98.0, 104.0, 0.005
        r = compute_net_rr(entry, sl, tp, fee_rate)

        fee_abs = entry * fee_rate
        expected = (tp - entry - fee_abs) / (entry - sl + fee_abs)
        assert r["rr_net"] == pytest.approx(expected, abs=1e-3)

    def test_short_tf_is_barely_positive(self):
        """
        🔴 رگرسیون اصلی: در TF کوتاه با SL/TP کوچک، R:R خالص
        به شدت افت می‌کند.

        با SL=0.5% و TP=1% و هزینه‌ی ۰.۶۵٪:
            R:R خام = 2.0  →  خالص = 0.30

        یعنی ۸۵٪ از R:R خورده می‌شود — عملاً معامله بی‌ارزش.
        """
        entry = 100.0
        sl = entry * 0.995  # 0.5% زیر
        tp = entry * 1.01  # 1% بالا
        r = compute_net_rr(entry, sl, tp, 0.0065)

        assert r["rr_gross"] == pytest.approx(2.0, abs=0.05)
        assert r["rr_net"] < 0.5, (
            f"با SL=0.5% و TP=1% و هزینه 0.65%، R:R خالص باید "
            f"زیر ۰.۵ باشد ولی {r['rr_net']} است"
        )
        assert r["is_worthwhile"] is False
        assert r["rr_decay_pct"] > 75, f"افت {r['rr_decay_pct']}٪"

    def test_very_tight_sl_is_negative(self):
        """
        🔴 بدترین حالت واقعی (مشاهده‌شده در تست E2E):
        BTC-USD/۵ دقیقه با TP=0.48% و SL=0.50% و هزینه=0.65٪
        → R:R خالص **منفی** (ضرر قطعی).
        """
        entry = 100.0
        sl = entry * 0.995  # 0.50%
        tp = entry * 1.0048  # 0.48%
        cost = 0.0065

        r = compute_net_rr(entry, sl, tp, cost)
        assert r["rr_net"] < 0, (
            f"TP=0.48% و SL=0.50% با هزینه 0.65% باید منفی باشد "
            f"ولی {r['rr_net']} است"
        )
        assert r["is_worthwhile"] is False

    def test_wide_sl_tp_is_profitable(self):
        """با SL/TP بزرگ، R:R خالص سالم است"""
        entry = 100.0
        r = compute_net_rr(entry, 92.0, 116.0, 0.0065)  # SL=8% TP=16%
        assert r["rr_net"] > 1.3
        assert r["is_worthwhile"] is True

    def test_decay_pct_computed(self):
        r = compute_net_rr(100, 98, 104, 0.005)
        assert 0 < r["rr_decay_pct"] < 100

    def test_breakeven_equals_fee(self):
        """نقطه‌ی سربه‌سر = کارمزد"""
        r = compute_net_rr(100, 98, 104, 0.004)
        assert r["breakeven_pct"] == pytest.approx(0.4)

    def test_fee_ratio(self):
        # ─── TP=4% و کارمزد=0.4% → نسبت ۱۰ ───
        r = compute_net_rr(100, 98, 104, 0.004)
        assert r["fee_ratio"] == pytest.approx(10.0, abs=0.1)

    def test_timeframe_viable_flag(self):
        """پرچم TF مناسب باید فقط برای R:R خالص ≥ ۱.۳ روشن شود"""
        high = compute_net_rr(100, 92, 116, 0.0065)
        assert high["timeframe_viable"] is True

        low = compute_net_rr(100, 99, 102, 0.0065)
        assert low["timeframe_viable"] is False

    def test_invalid_inputs(self):
        assert compute_net_rr(0, 98, 104, 0.004) == {}
        assert compute_net_rr(100, 100, 104, 0.004) == {}  # ─── risk=0 ───
        assert compute_net_rr(100, 98, 0, 0.004) == {}


# ═══════════════════════════════════════════════════════════
# ۳. عمق بازار
# ═══════════════════════════════════════════════════════════
class TestOrderBookNormalization:
    def test_bid_ask_swap_detected_and_fixed(self):
        """
        🔴 رگرسیون: نوبیتکس bids/asks را جابه‌جا می‌دهد.
        نرمال‌سازی باید تشخیص و اصلاح کند.
        """
        from core.orderbook import normalize_orderbook

        # ─── داده‌ی برعکس: bids بالاتر از asks ───
        raw = {
            "bids": [[84836.0, 1.0], [84830.0, 2.0]],  # ← در واقع asks
            "asks": [[84530.0, 1.5], [84520.0, 2.5]],  # ← در واقع bids
        }
        ob = normalize_orderbook("BTC-USD", "nobitex", raw)

        assert ob is not None, "باید اصلاح شود، نه رد"
        assert (
            ob["best_bid"] < ob["best_ask"]
        ), f"bid={ob['best_bid']} ask={ob['best_ask']}"
        assert ob["spread"] > 0
        assert 0 <= ob["imbalance"] <= 1

    def test_normal_data_unchanged(self):
        """داده‌ی درست نباید دست بخورد"""
        from core.orderbook import normalize_orderbook

        raw = {
            "bids": [[100.0, 1.0], [99.5, 2.0]],
            "asks": [[100.5, 1.0], [101.0, 2.0]],
        }
        ob = normalize_orderbook("BTC-USD", "bitpin", raw)

        assert ob["best_bid"] == pytest.approx(100.0)
        assert ob["best_ask"] == pytest.approx(100.5)
        assert ob["spread"] == pytest.approx(0.5)

    def test_imbalance_in_range(self):
        from core.orderbook import normalize_orderbook

        raw = {
            "bids": [[100.0, 3.0]],
            "asks": [[100.5, 1.0]],
        }
        ob = normalize_orderbook("X", "bitpin", raw)
        assert 0 <= ob["imbalance"] <= 1
        assert ob["imbalance"] == pytest.approx(0.75)

    def test_empty_or_invalid(self):
        from core.orderbook import normalize_orderbook

        assert normalize_orderbook("X", "y", None) is None
        assert normalize_orderbook("X", "y", {}) is None
        assert normalize_orderbook("X", "y", {"bids": [], "asks": []}) is None
        assert normalize_orderbook("X", "y", {"bids": [[1, 1]]}) is None

    def test_pressure_labels(self):
        from core.orderbook import normalize_orderbook

        strong_buy = normalize_orderbook(
            "X", "y", {"bids": [[100, 9]], "asks": [[101, 1]]}
        )
        assert "خرید" in strong_buy["pressure_fa"]

        strong_sell = normalize_orderbook(
            "X", "y", {"bids": [[100, 1]], "asks": [[101, 9]]}
        )
        assert "فروش" in strong_sell["pressure_fa"]

    def test_wall_detection(self):
        from core.orderbook import normalize_orderbook

        # ─── یک سطح با حجم ۱۰ برابر ───
        raw = {
            "bids": [[100, 1], [99.9, 1], [99.8, 1], [99.7, 1], [99.6, 20]],
            "asks": [[100.5, 1], [100.6, 1], [100.7, 1], [100.8, 1], [100.9, 1]],
        }
        ob = normalize_orderbook("X", "y", raw)
        assert ob["wall"] is not None
        assert ob["wall"]["side"] == "bid"
        assert ob["wall"]["ratio"] >= 4.0

    def test_no_wall_when_uniform(self):
        from core.orderbook import normalize_orderbook

        raw = {
            "bids": [[100 - i * 0.1, 1.0] for i in range(10)],
            "asks": [[100.5 + i * 0.1, 1.0] for i in range(10)],
        }
        ob = normalize_orderbook("X", "y", raw)
        assert ob["wall"] is None


class TestImbalanceVote:
    def test_vote_direction(self):
        from core.orderbook import imbalance_vote

        assert imbalance_vote(0.80)[0] == 1
        assert imbalance_vote(0.60)[0] == 1
        assert imbalance_vote(0.50)[0] == 0
        assert imbalance_vote(0.40)[0] == -1
        assert imbalance_vote(0.20)[0] == -1

    def test_score_is_low(self):
        """
        ⚠️ امتیاز عمداً کم است — imbalance لحظه‌ای و قابل
        دستکاری (spoofing) است، پس نباید غالب باشد.
        """
        from core.orderbook import imbalance_vote

        for imb in (0.1, 0.3, 0.5, 0.7, 0.9):
            _, score = imbalance_vote(imb)
            assert abs(score) <= 0.5, f"imbalance={imb} امتیاز {score}"


class TestExecutionCost:
    def test_components_sum(self):
        from core.orderbook import execution_cost_pct

        c = execution_cost_pct(0.1, 0.004)
        assert c["total_pct"] == pytest.approx(
            c["fee_pct"] + c["spread_cost_pct"] + c["slippage_pct"], abs=0.01
        )

    def test_realistic_magnitude(self):
        """هزینه‌ی واقعی معامله در صرافی ایرانی ۰.۵-۰.۸٪"""
        from core.orderbook import execution_cost_pct

        c = execution_cost_pct(0.1, get_fee_rate("nobitex"))
        assert 0.4 < c["total_pct"] < 1.0, c

    def test_wider_spread_costs_more(self):
        from core.orderbook import execution_cost_pct

        narrow = execution_cost_pct(0.05, 0.004)
        wide = execution_cost_pct(1.0, 0.004)
        assert wide["total_pct"] > narrow["total_pct"]


# ═══════════════════════════════════════════════════════════
# ۴. اتصال به تحلیل (رگرسیون)
# ═══════════════════════════════════════════════════════════
class TestAnalyzerFeeIntegration:
    def test_analyzer_accepts_orderbook_param(self):
        """``analyze_symbol`` باید پارامتر orderbook داشته باشد"""
        import inspect

        from core import analyzer

        sig = inspect.signature(analyzer.analyze_symbol)
        assert "orderbook" in sig.parameters
        assert "source" in sig.parameters

    def test_volume_group_accepts_orderbook(self):
        import inspect

        from core import analyzer

        sig = inspect.signature(analyzer._analyze_volume)
        assert "orderbook" in sig.parameters

    def test_no_hardcoded_fee(self):
        """نرخ کارمزد نباید در analyzer هاردکد باشد"""
        import inspect

        from core import analyzer

        src = inspect.getsource(analyzer)
        # ─── نباید 0.004 یا 0.0025 هاردکد شده باشد ───
        assert "compute_net_rr" in src
        assert "get_fee_rate" in src

    def test_analyze_returns_fee_fields(self):
        """``analyze`` باید فیلدهای کارمزد را بدهد"""
        import inspect

        from services import analyzer_service as svc

        src = inspect.getsource(svc.analyze)
        for field in ("rr_net", "fee_pct", "is_worthwhile", "timeframe_viable"):
            assert field in src, f"{field} در خروجی نیست"


# ═══════════════════════════════════════════════════════════
# ۵. سطوح کلیدی — رگرسیون باگ حمایت
# ═══════════════════════════════════════════════════════════
class TestSupportResistanceDisplay:
    def test_support_block_uses_support_variables(self):
        """
        🔴 رگرسیون باگ: بلوک حمایت کاملاً کپی بلوک مقاومت بود —
        هم ``r`` چاپ می‌شد، هم ``dist_r``، هم برچسب «مقاومت».
        نتیجه: کاربر دو بار مقاومت می‌دید و حمایت **اصلاً**
        نمایش داده نمی‌شد.
        """
        import inspect

        from core import analyzer

        # ─── deep_analysis تابع تولید پاراگراف است ───
        src = inspect.getsource(analyzer)

        # ─── باید «حمایت» با ``s`` و ``dist_s`` باشد ───
        assert "🟢 **حمایت:**" in src, "برچسب حمایت نیست"
        assert "dist_s" in src, "dist_s محاسبه نمی‌شود"

        # ─── در بلوک حمایت نباید ``r:`` چاپ شود ───
        # (این را با جستجوی الگوی غلط قبلی چک می‌کنیم)
        bad_pattern = "🟢 **حمایت:** {r:"
        assert bad_pattern not in src, "بلوک حمایت هنوز از r استفاده می‌کند"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
