"""
core/scanner.py
اسکنر فرصت‌های بازار — پیدا کردن نمادهای مستعد نوسان‌گیری
نسخه ۲.۰ — بازارمحور
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.analyzer import analyze_symbol
from core.data_fetcher import TIMEFRAMES, fetch_history
from core.market_lists import get_category_tickers, get_category
from core.utils import safe_num


# ═══════════════════════════════════════════════════════════
# محاسبه امتیاز نوسان‌گیری (0-100)
# ═══════════════════════════════════════════════════════════
def compute_volatility_score(analysis: dict) -> float:
    """
    محاسبه امتیاز نوسان‌گیری (0-100) برای یه نماد.
    """
    if not analysis:
        return 0.0

    price = safe_num(analysis.get("price"))
    atr = safe_num(analysis.get("atr"))
    adx = safe_num(analysis.get("adx"))
    ema200 = safe_num(analysis.get("ema200"))
    confidence = safe_num(analysis.get("confidence"))
    rr = safe_num(analysis.get("rr"))
    signal = analysis.get("signal", "")

    if price <= 0:
        return 0.0

    # ATR Score
    atr_pct = (atr / price) * 100 if price > 0 else 0
    atr_score = min(100, (atr_pct / 3.0) * 100)

    # ADX Score
    adx_score = min(100, max(0, (adx - 15) / 30 * 100))

    # Trend Score
    if ema200 > 0:
        trend_dist = abs(price - ema200) / ema200 * 100
        trend_score = min(100, 30 + (trend_dist / 5.0) * 70)
    else:
        trend_score = 30

    # Signal Confidence
    if "LONG" in signal or "SHORT" in signal:
        signal_score = confidence
    else:
        signal_score = 20

    # R:R Score
    if rr and rr > 0:
        rr_score = min(100, rr * 50)
    else:
        rr_score = 0

    # ترکیب وزنی
    total = (
        atr_score * 0.25
        + adx_score * 0.20
        + signal_score * 0.20
        + trend_score * 0.15
        + rr_score * 0.10
        + signal_score * 0.10
    )

    return round(min(100, max(0, total)), 1)


# ═══════════════════════════════════════════════════════════
# اسکن یک نماد
# ═══════════════════════════════════════════════════════════
def _scan_one(ticker: str, name: str, tf_index: int = 3) -> dict | None:
    try:
        if tf_index >= len(TIMEFRAMES):
            tf_index = 3

        iv, p, tf_name = TIMEFRAMES[tf_index]

        df = fetch_history(ticker, iv, p)
        if df is None or df.empty:
            return None

        analysis = analyze_symbol(df, "medium")
        if not analysis:
            return None

        score = compute_volatility_score(analysis)

        return {
            "ticker": ticker,
            "name": name,
            "timeframe": tf_name,
            "score": score,
            "signal": analysis.get("signal", "خنثی"),
            "confidence": analysis.get("confidence", 0),
            "price": analysis.get("price", 0),
            "rsi": analysis.get("rsi", 50),
            "adx": analysis.get("adx", 20),
            "atr": analysis.get("atr", 0),
            "rr": analysis.get("rr"),
            "reasons": analysis.get("reasons", []),
        }
    except Exception as e:
        print(f"[Scanner] خطا در {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# اسکن یک بازار خاص
# ═══════════════════════════════════════════════════════════
def scan_markets(
    category: str = "crypto",
    tf_index: int = 3,
    top_n: int = 5,
) -> dict:
    """
    اسکن یه بازار خاص.

    Args:
        category: نام دسته (crypto, forex, us_stocks, commodities, indices, iran_stocks)
        tf_index: ایندکس تایم‌فریم
        top_n: تعداد نتایج برتر

    Returns:
        dict: {
            "top": [...],
            "all": [...],
            "category": str,
            "category_name": str,
            "category_icon": str,
            "timeframe": str,
            "total_scanned": int,
            "total_success": int,
        }
    """
    cat_info = get_category(category) or {}
    tickers = get_category_tickers(category)

    cat_name = cat_info.get("name", category)
    cat_icon = cat_info.get("icon", "📊")
    tf_name = TIMEFRAMES[tf_index][2] if tf_index < len(TIMEFRAMES) else "?"

    # اگه لیست خالیه
    if not tickers:
        return {
            "top": [], "all": [],
            "category": category,
            "category_name": cat_name,
            "category_icon": cat_icon,
            "timeframe": tf_name,
            "total_scanned": 0,
            "total_success": 0,
            "empty_message": cat_info.get("description", "این بازار در دسترس نیست."),
        }

    results = []

    # موازی‌سازی
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_scan_one, tkr, name, tf_index): tkr
            for tkr, name in tickers
        }

        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    results.append(res)
            except Exception as e:
                print(f"[Scanner] خطا در future: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "top": results[:top_n],
        "all": results,
        "category": category,
        "category_name": cat_name,
        "category_icon": cat_icon,
        "timeframe": tf_name,
        "total_scanned": len(tickers),
        "total_success": len(results),
    }


# ═══════════════════════════════════════════════════════════
# خلاصه یک خطی
# ═══════════════════════════════════════════════════════════
def get_scan_summary(item: dict) -> str:
    if not item:
        return "—"

    reasons = []
    adx = safe_num(item.get("adx"))
    if adx >= 30:
        reasons.append("روند قوی")
    elif adx >= 25:
        reasons.append("روند متوسط")

    rsi = safe_num(item.get("rsi"), 50)
    if 30 <= rsi <= 40:
        reasons.append("نزدیک اشباع فروش")
    elif 60 <= rsi <= 70:
        reasons.append("نزدیک اشباع خرید")

    rr = safe_num(item.get("rr"))
    if rr >= 1.5:
        reasons.append(f"R:R={rr:.1f}")

    confidence = safe_num(item.get("confidence"))
    if confidence >= 70:
        reasons.append("اطمینان بالا")

    if not reasons:
        return "بدون ویژگی خاص"

    return " + ".join(reasons[:3])