"""
core/strategies.py
سه استراتژی معاملاتی — نسخه ۲.۰ (فاز ۱۴.۷.۳)
============================================================
🔴 تغییرات ۲.۰:
  • min_confidence_by_risk — آستانه پویا بر اساس ریسک
  • get_min_confidence() — تابع کمکی
  • get_strong_trend_threshold() — آستانه‌ی override per-strategy
  • min_votes_by_risk — تعداد رأی مورد نیاز per-strategy+risk
  • هم‌راستا با UX جدید (۵ سطح: 30/40/50/50/60)
"""

STRATEGIES = {
    "scalp": {
        "name": "⚡ اسکالپ",
        "name_full": "اسکالپ (نوسان‌گیری لحظه‌ای)",
        "name_en": "Scalp",
        "description": "معاملات سریع فیوچرز — ورود و خروج در چند دقیقه",
        "recommended_tfs": ["۱ دقیقه", "۵ دقیقه"],
        "recommended_market": "futures",
        "min_confidence": 30,  # fallback (قدیمی)
        # 🔴 فاز ۱۴.۷.۳ — آستانه‌ی پویا بر اساس ریسک
        "min_confidence_by_risk": {
            "aggressive": 30,
            "conservative": 50,  # بلاک شده در UI ولی اگر مستقیم بیاد
        },
        "min_confidence_default": 30,
        "min_votes": 2,
        "min_votes_by_risk": {
            "aggressive": 2,
            "conservative": 3,
        },
        "strong_trend_threshold": 0.80,  # فقط روند خیلی قوی بلاک
        "tp_multiplier": 0.7,
        "sl_multiplier": 0.8,
        "timeout_candles": 4,
        "cooldown_candles": 3,
        "leverage_suggestion": 3,
        "risk_per_trade_pct": 2.5,
        "force_profile": "aggressive",
        "force_market": "futures",
        "group_weights": {
            "momentum": 1.5,
            "trend": 0.8,
            "volume": 1.5,
            "volatility": 1.0,
            "structure": 0.9,
        },
    },
    "swing": {
        "name": "🌊 سوئینگ",
        "name_full": "سوئینگ تریدینگ (میان‌مدت)",
        "name_en": "Swing",
        "description": "معاملات میان‌مدت — از چند ساعت تا چند روز",
        "recommended_tfs": [
            "۱ دقیقه",
            "۵ دقیقه",
            "۱۵ دقیقه",
            "۳۰ دقیقه",
            "۱ ساعت",
            "روزانه",
        ],  # 🔴 همه ۶ TF (هم‌راستا با TFTable)
        "recommended_market": "both",
        "min_confidence": 45,  # fallback
        "min_confidence_by_risk": {
            "aggressive": 40,
            "conservative": 50,
        },
        "min_confidence_default": 45,
        "min_votes": 2,
        "min_votes_by_risk": {
            "aggressive": 2,
            "conservative": 3,
        },
        "strong_trend_threshold": 0.55,
        "tp_multiplier": 1.0,
        "sl_multiplier": 1.0,
        "timeout_candles": 10,
        "cooldown_candles": 3,
        "leverage_suggestion": 2,
        "risk_per_trade_pct": 2.0,
        "force_profile": None,
        "force_market": None,
        "group_weights": {
            "momentum": 1.2,
            "trend": 1.3,
            "volume": 1.1,
            "volatility": 1.0,
            "structure": 1.2,
        },
    },
    "position": {
        "name": "🏛 پوزیشن",
        "name_full": "پوزیشن تریدینگ (بلندمدت)",
        "name_en": "Position",
        "description": "سرمایه‌گذاری بلندمدت — چند روز تا چند هفته",
        "recommended_tfs": ["۳۰ دقیقه", "۱ ساعت", "روزانه"],
        "recommended_market": "spot",
        "min_confidence": 55,  # fallback
        "min_confidence_by_risk": {
            "aggressive": 50,
            "conservative": 60,
        },
        "min_confidence_default": 55,
        "min_votes": 3,
        "min_votes_by_risk": {
            "aggressive": 3,
            "conservative": 3,
        },
        "strong_trend_threshold": 0.45,
        "tp_multiplier": 1.2,
        "sl_multiplier": 1.2,
        "timeout_candles": 21,
        "cooldown_candles": 3,
        "leverage_suggestion": None,
        "risk_per_trade_pct": 1.0,
        "force_profile": "conservative",
        "force_market": "spot",
        "group_weights": {
            "momentum": 0.8,
            "trend": 1.8,
            "volume": 0.9,
            "volatility": 0.9,
            "structure": 1.5,
        },
    },
}

DEFAULT_STRATEGY = "swing"


def get_strategy(strategy_key):
    if not strategy_key:
        return STRATEGIES[DEFAULT_STRATEGY]
    return STRATEGIES.get(strategy_key, STRATEGIES[DEFAULT_STRATEGY])


def get_min_confidence(strategy_key: str, risk_profile: str = "aggressive") -> int:
    """
    🔴 فاز ۱۴.۷.۳ — آستانه‌ی نمایش = ترکیب استراتژی + ریسک.

    Examples:
        >>> get_min_confidence("scalp", "aggressive")    # 30
        >>> get_min_confidence("scalp", "conservative")  # 50
        >>> get_min_confidence("swing", "aggressive")    # 40
        >>> get_min_confidence("swing", "conservative")  # 50
        >>> get_min_confidence("position", "aggressive") # 50
        >>> get_min_confidence("position", "conservative") # 60
    """
    s = get_strategy(strategy_key)
    by_risk = s.get("min_confidence_by_risk", {})
    if risk_profile in by_risk:
        return int(by_risk[risk_profile])
    return int(s.get("min_confidence_default", s.get("min_confidence", 50)))


def get_min_votes(strategy_key: str, risk_profile: str = "aggressive") -> int:
    """🔴 فاز ۱۴.۷.۳ — تعداد رأی مورد نیاز (per-strategy+risk)"""
    s = get_strategy(strategy_key)
    by_risk = s.get("min_votes_by_risk", {})
    if risk_profile in by_risk:
        return int(by_risk[risk_profile])
    return int(s.get("min_votes", 2))


def get_strong_trend_threshold(strategy_key: str) -> float:
    """🔴 فاز ۱۴.۷.۳ — آستانه‌ی trend override (per-strategy)"""
    s = get_strategy(strategy_key)
    return float(s.get("strong_trend_threshold", 0.45))


def get_strategy_timeout(strategy_key, tf_name):
    _TF_MINUTES = {
        "۱ دقیقه": 1,
        "۵ دقیقه": 5,
        "۱۵ دقیقه": 15,
        "۳۰ دقیقه": 30,
        "۱ ساعت": 60,
        "روزانه": 1440,
    }
    strategy = get_strategy(strategy_key)
    candles = strategy.get("timeout_candles", 7)
    tf_min = _TF_MINUTES.get(tf_name, 5)
    return candles * tf_min


def get_cooldown_minutes(strategy_key, tf_name):
    """cooldown به دقیقه: cooldown_candles × TF"""
    _TF_MINUTES = {
        "۱ دقیقه": 1,
        "۵ دقیقه": 5,
        "۱۵ دقیقه": 15,
        "۳۰ دقیقه": 30,
        "۱ ساعت": 60,
        "روزانه": 1440,
    }
    strategy = get_strategy(strategy_key)
    candles = strategy.get("cooldown_candles", 3)
    tf_min = _TF_MINUTES.get(tf_name, 5)
    return candles * tf_min


def get_group_weights(strategy_key, regime):
    """وزن گروه‌ها = وزن استراتژی × وزن رژیم"""
    from core.analyzer import _regime_weights

    strategy = get_strategy(strategy_key)
    strategy_weights = strategy.get("group_weights", {})
    regime_weights = _regime_weights(regime)

    result = {}
    for group in ["momentum", "trend", "volume", "volatility", "structure"]:
        sw = strategy_weights.get(group, 1.0)
        rw = regime_weights.get(group, 1.0)
        result[group] = (sw + rw) / 2.0

    return result


def list_strategies():
    return [
        {
            "key": key,
            "name": s["name"],
            "name_full": s["name_full"],
            "name_en": s["name_en"],
            "description": s["description"],
            "recommended_tfs": s["recommended_tfs"],
            "min_confidence": s["min_confidence"],
            "min_confidence_by_risk": s.get("min_confidence_by_risk", {}),
            "risk_per_trade_pct": s["risk_per_trade_pct"],
        }
        for key, s in STRATEGIES.items()
    ]


__all__ = [
    "STRATEGIES",
    "DEFAULT_STRATEGY",
    "get_strategy",
    "get_min_confidence",
    "get_min_votes",
    "get_strong_trend_threshold",
    "get_strategy_timeout",
    "get_cooldown_minutes",
    "get_group_weights",
    "list_strategies",
]
