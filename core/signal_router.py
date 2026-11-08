"""
core/signal_router.py
توزیع سیگنال بر اساس TF و بازار
"""


def get_strategy(tf_name: str, market_type: str) -> str:
    """تشخیص استراتژی مناسب"""
    if market_type == "futures" and tf_name in ("۱ دقیقه", "۵ دقیقه"):
        return "scalp"
    elif market_type == "spot" and tf_name in ("۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"):
        return "swing"
    elif tf_name == "روزانه":
        return "position"
    else:
        return "classic"
