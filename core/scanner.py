"""
core/scanner.py
اسکنر بازارها — نسخه ۷.۰ (فاز ۵)
============================================================
تغییرات نسخه ۷.۰:
  - پارامتر market_type (spot/futures)
  - پیش‌فرض TF ≥ 5m برای کریپتو (چون 1m داده کمه)
  - fallback هوشمند
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .contracts import TIMEFRAMES, Signal as SigEnum, MarketType
from .data_fetcher import fetch_history_by_source
from .market_lists import get_categories_with_tickers, get_category_source
from .analyzer import analyze_symbol


# ═══════════════════════════════════════════════════════════
# نمادهای خودکار نوبیتکس
# ═══════════════════════════════════════════════════════════
def _get_nobitex_symbols_for_scanner() -> list[tuple]:
    try:
        from .nobitex_fetcher import (
            fetch_all_nobitex_symbols,
            filter_liquid_symbols,
            map_nobitex_to_symbol,
        )

        all_syms = fetch_all_nobitex_symbols(dst_currency="usdt")
        if not all_syms:
            return []

        liquid = filter_liquid_symbols(
            all_syms,
            min_volume=10000.0,
            min_trades=100,
            max_count=50,
        )

        result = []
        for s in liquid:
            nobitex_sym = s["symbol"]
            our_ticker = map_nobitex_to_symbol(nobitex_sym)
            if our_ticker:
                display_name = f"{s['base']}/{s['quote']}"
                result.append((our_ticker, display_name))

        return result
    except Exception as e:
        print(f"[Scanner] خطا در دریافت لیست نوبیتکس: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# انتخاب TF مناسب
# ═══════════════════════════════════════════════════════════
def _resolve_tf_for_market(category: str, tf_index: int) -> int:
    """
    - iran_stocks: روزانه
    - crypto: حداقل ۵ دقیقه (چون ۱ دقیقه داده کمه)
    """
    if category == "iran_stocks":
        for i, (_, _, name) in enumerate(TIMEFRAMES):
            if name == "روزانه":
                return i

    if category == "crypto":
        # اگه TF < 5m بود، 5m بذار
        if tf_index < 1:
            return 1  # 5m

    return tf_index


# ═══════════════════════════════════════════════════════════
# اسکن
# ═══════════════════════════════════════════════════════════
def scan_markets(
    category: str,
    tf_index: int = 0,
    top_n: int = 5,
    risk_profile: str = "aggressive",
    market_type: str = MarketType.FUTURES.value,
) -> dict:
    """
    اسکن یه دسته.

    Args:
        category: کلید دسته
        tf_index: ایندکس TF
        top_n: تعداد نتایج برتر
        risk_profile: پروفایل ریسک
        market_type: spot / futures
    """
    categories = get_categories_with_tickers()

    if category not in categories:
        return {
            "all": [],
            "total_scanned": 0,
            "total_success": 0,
            "category_name": "",
            "category_icon": "📊",
            "empty_message": "دسته یافت نشد",
            "source_label": "",
        }

    cat = categories[category]
    cat_name = cat.get("name", category)
    cat_icon = cat.get("icon", "📊")
    cat_source = get_category_source(category)

    # ─── انتخاب نمادها ───
    source_label = ""

    if category == "crypto":
        auto_tickers = _get_nobitex_symbols_for_scanner()
        if auto_tickers:
            tickers = auto_tickers
            source_label = "🟠 نوبیتکس (خودکار)"
            cat_source = "nobitex"
        else:
            tickers = cat.get("tickers", [])
            source_label = "📋 لیست پیش‌فرض"
    else:
        tickers = cat.get("tickers", [])
        source_label_map = {
            "global": "🌍 yfinance",
            "nobitex": "🟠 نوبیتکس",
            "tsetmc": "🇮🇷 TSETMC",
            "abantether": "🔵 آبان‌تتر",
        }
        source_label = source_label_map.get(cat_source, "📋 لیست پیش‌فرض")

    if not tickers:
        return {
            "all": [],
            "total_scanned": 0,
            "total_success": 0,
            "category_name": cat_name,
            "category_icon": cat_icon,
            "empty_message": "این دسته نمادی نداره",
            "source_label": source_label,
        }

    # ─── TF ───
    if tf_index < 0 or tf_index >= len(TIMEFRAMES):
        tf_index = 0

    actual_tf_index = _resolve_tf_for_market(category, tf_index)
    interval, period, tf_name = TIMEFRAMES[actual_tf_index]

    results = []
    total_scanned = len(tickers)

    def _analyze_one(ticker_info):
        try:
            if isinstance(ticker_info, (list, tuple)):
                symbol = ticker_info[0]
                display_name = ticker_info[1] if len(ticker_info) > 1 else symbol
            else:
                symbol = ticker_info
                display_name = ticker_info

            df = fetch_history_by_source(symbol, interval, period, cat_source)
            if df is None or df.empty:
                return None

            # ← تحلیل با market_type درست
            analysis = analyze_symbol(
                df,
                risk_profile=risk_profile,
                tf_name=tf_name,
                tfs_data=None,
                market_type=market_type,
            )
            if not analysis:
                return None

            return {
                "ticker": symbol,
                "name": display_name,
                "price": analysis.get("price", 0),
                "signal": analysis.get("signal", "خنثی"),
                "confidence": analysis.get("confidence", 0),
                "score": analysis.get("raw_score", 0) * 100,
                "rr": analysis.get("rr"),
                "regime": analysis.get("regime", "range"),
                "adx": analysis.get("adx", 0),
                "groups": analysis.get("groups", {}),
                "votes_long": analysis.get("votes_long", 0),
                "votes_short": analysis.get("votes_short", 0),
                "direction": analysis.get("direction", "neutral"),
                "consensus": analysis.get("consensus", "neutral"),
            }
        except Exception as e:
            print(f"[Scanner] خطا در {ticker_info}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_analyze_one, t) for t in tickers]
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception as e:
                print(f"[Scanner] future: {e}")

    total_success = len(results)

    def sort_key(item):
        sig = item.get("signal", "")
        score = item.get("score", 0)
        if SigEnum.is_directional(sig) and not SigEnum.is_weak(sig):
            prio = 3
        elif SigEnum.is_directional(sig):
            prio = 2
        else:
            prio = 1

        if SigEnum.is_long(sig):
            return (prio, score)
        elif SigEnum.is_short(sig):
            return (prio, -score)
        else:
            return (prio, abs(score))

    results.sort(key=sort_key, reverse=True)

    empty_msg = None
    if total_success == 0:
        if cat_source == "tsetmc":
            empty_msg = "⚠️ TSETMC فقط از IP ایران در دسترسه"
        else:
            empty_msg = "هیچ نمادی تحلیل نشد (شاید API محدودیت داره)"

    return {
        "all": results,
        "total_scanned": total_scanned,
        "total_success": total_success,
        "category_name": cat_name,
        "category_icon": cat_icon,
        "empty_message": empty_msg,
        "source_label": source_label,
    }


__all__ = ["scan_markets"]


if __name__ == "__main__":
    print("=" * 70)
    print("تست core/scanner.py — نسخه ۷.۰")
    print("=" * 70)
    print()

    print("۱) اسکن crypto (futures):")
    result = scan_markets("crypto", tf_index=1, top_n=3, market_type="futures")
    print(f"   منبع: {result['source_label']}")
    print(f"   اسکن‌شده: {result['total_scanned']}, موفق: {result['total_success']}")
    for r in result["all"][:3]:
        print(f"   • {r['ticker']:12} {r['signal']:15} conf={r['confidence']}%")

    print()
    print("[OK] تست کامل شد.")
