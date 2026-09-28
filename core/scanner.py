"""
core/scanner.py
اسکنر بازارها — نسخه ۵.۰
================================================
- اسکنر مستقل از پروفایل کاربر (پیش‌فرض: aggressive)
- موازی‌سازی با ThreadPoolExecutor
- پشتیبانی از لیست خودکار نوبیتکس (فقط کریپتو)
- پشتیبانی از market_lists.py برای بقیه بازارها
- حذف نمادهای مرده (فیلتر نقدینگی)

⚠️ توجه: آبان‌تتر OHLCV نداره — در اسکنر استفاده نمی‌شه.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.data_fetcher import fetch_history, TIMEFRAMES
from core.analyzer import analyze_symbol
from core.market_lists import get_categories_with_tickers


# ═══════════════════════════════════════════════════════════
# دریافت لیست نمادهای خودکار از نوبیتکس
# ═══════════════════════════════════════════════════════════
def _get_nobitex_symbols_for_scanner() -> list[tuple]:
    """
    دریافت لیست نمادهای نقدشونده نوبیتکس برای اسکنر.
    
    Returns:
        لیست تاپل‌ها: [(ticker, name), ...]
        مثال: [("BTC-USD", "بیت‌کوین"), ...]
    """
    try:
        from core.nobitex_fetcher import (
            fetch_all_nobitex_symbols,
            filter_liquid_symbols,
            NOBITEX_SYMBOLS,
        )
        
        # دریافت همه نمادها از نوبیتکس
        all_syms = fetch_all_nobitex_symbols(dst_currency="usdt")
        
        if not all_syms:
            print("[Scanner] لیست نوبیتکس خالیه — fallback به market_lists")
            return []
        
        # فیلتر نقدینگی
        liquid = filter_liquid_symbols(
            all_syms,
            min_volume=10000.0,   # حداقل ۱۰,۰۰۰ تتر حجم ۲۴ ساعته
            min_trades=100,       # حداقل ۱۰۰ معامله
            max_count=50,
        )
        
        # نگاشت معکوس: BTCUSDT → BTC-USD
        reverse_map = {v: k for k, v in NOBITEX_SYMBOLS.items()}
        
        # فیلتر: فقط نمادهایی که توی NOBITEX_SYMBOLS هستن
        result = []
        for s in liquid:
            nobitex_sym = s["symbol"]  # مثل BTCUSDT
            our_ticker = reverse_map.get(nobitex_sym)  # مثل BTC-USD
            
            if our_ticker:
                # اسم نمایشی: base + quote
                display_name = f"{s['base']}/{s['quote']}"
                result.append((our_ticker, display_name))
        
        return result
    
    except Exception as e:
        print(f"[Scanner] خطا در دریافت لیست نوبیتکس: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# اسکن یه دسته
# ═══════════════════════════════════════════════════════════
def scan_markets(
    category: str,
    tf_index: int = 0,
    top_n: int = 5,
    risk_profile: str = "aggressive",
) -> dict:
    """
    اسکن یه دسته از بازارها با یه تایم‌فریم مشخص.
    
    Args:
        category: کلید دسته — "crypto" / "forex" / "us_stocks" / ...
        tf_index: ایندکس تایم‌فریم
        top_n: تعداد نتایج برتر
        risk_profile: پروفایل ریسک
    
    Returns:
        dict با نتایج اسکن
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

    # ═══ انتخاب لیست نمادها ═══
    source_label = ""
    if category == "crypto":
        # برای کریپتو، از لیست خودکار نوبیتکس استفاده کن
        auto_tickers = _get_nobitex_symbols_for_scanner()
        
        if auto_tickers:
            tickers = auto_tickers
            source_label = "🟠 نوبیتکس (خودکار)"
        else:
            # fallback به market_lists
            tickers = cat.get("tickers", [])
            source_label = "📋 لیست پیش‌فرض"
    else:
        # برای بقیه بازارها، از market_lists استفاده کن
        tickers = cat.get("tickers", [])
        source_label = "📋 لیست پیش‌فرض"

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

    if tf_index < 0 or tf_index >= len(TIMEFRAMES):
        tf_index = 0

    interval, period, tf_name = TIMEFRAMES[tf_index]

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

            df = fetch_history(symbol, interval, period)
            if df is None or df.empty:
                return None

            analysis = analyze_symbol(
                df,
                risk_profile=risk_profile,
                tf_name=tf_name,
                tfs_data=None,
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
                print(f"[Scanner] خطا در future: {e}")

    total_success = len(results)

    def sort_key(item):
        sig = item.get("signal", "")
        score = item.get("score", 0)
        if "LONG" in sig and "ضعیف" not in sig:
            prio = 3
        elif "SHORT" in sig and "ضعیف" not in sig:
            prio = 3
        elif "LONG" in sig or "SHORT" in sig:
            prio = 2
        else:
            prio = 1
        if "LONG" in sig:
            return (prio, score)
        elif "SHORT" in sig:
            return (prio, -score)
        else:
            return (prio, abs(score))

    results.sort(key=sort_key, reverse=True)

    empty_msg = None
    if total_success == 0:
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