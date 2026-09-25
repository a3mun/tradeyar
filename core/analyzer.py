"""
core/analyzer.py
تحلیل تکنیکال — اندیکاتورها، سیگنال، SL/TP
نسخه ۳.۱ — با پشتیبانی تایم‌فریم در تحلیل
"""

import pandas as pd
import pandas_ta_classic as ta

from .utils import safe_num


# ═══════════════════════════════════════════════════════════
# پروفایل‌های ریسک
# ═══════════════════════════════════════════════════════════
RISK_PROFILES = {
    "low": {
        "name": "کم",
        "sl_mult": 1.0,
        "tp_mult": 2.0,
        "min_score": 2,
        "color": "#3FB950",
        "advice": "سرمایه کم داری؟ فقط سیگنال‌های قوی رو بگیر. حداکثر ۱-۲٪ سرمایه.",
    },
    "medium": {
        "name": "متوسط",
        "sl_mult": 1.5,
        "tp_mult": 3.0,
        "min_score": 1,
        "color": "#D29922",
        "advice": "تعادل بین ریسک و بازده. ۳-۵٪ سرمایه در هر معامله.",
    },
    "high": {
        "name": "زیاد",
        "sl_mult": 2.0,
        "tp_mult": 4.0,
        "min_score": 0.5,
        "color": "#DB6D28",
        "advice": "ریسک‌پذیر هستی؟ می‌تونی SHORT هم بزنی. ولی حتماً حد ضرر بذار.",
    },
}


# ═══════════════════════════════════════════════════════════
# محاسبه اندیکاتورها
# ═══════════════════════════════════════════════════════════
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """محاسبه تمام اندیکاتورهای لازم روی دیتافریم"""
    if df is None or df.empty or len(df) < 50:
        return df

    df["rsi"] = ta.rsi(df["close"], length=14)
    df["willr"] = ta.willr(df["high"], df["low"], df["close"], length=14)

    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd_df is not None and len(macd_df.columns) >= 3:
        df["macd_hist"] = macd_df.iloc[:, 2]
    else:
        df["macd_hist"] = 0.0

    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["ema200"] = ta.ema(df["close"], length=200)

    stoch_df = ta.stoch(df["high"], df["low"], df["close"],
                        k=5, d=3, smooth_k=3)
    if stoch_df is not None and len(stoch_df.columns) >= 2:
        df["stoch_k"] = stoch_df.iloc[:, 0]
        df["stoch_d"] = stoch_df.iloc[:, 1]
    else:
        df["stoch_k"] = 50.0
        df["stoch_d"] = 50.0

    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx_df is not None and len(adx_df.columns) >= 1:
        df["adx"] = adx_df.iloc[:, 0]
    else:
        df["adx"] = 20.0

    bb_df = ta.bbands(df["close"], length=20, std=2)
    if bb_df is not None and len(bb_df.columns) >= 3:
        df["bb_lower"] = bb_df.iloc[:, 0]
        df["bb_mid"] = bb_df.iloc[:, 1]
        df["bb_upper"] = bb_df.iloc[:, 2]

    try:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        if "volume" in df.columns and df["volume"].sum() > 0:
            vwap = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
            df["vwap"] = vwap
    except Exception:
        pass

    return df


# ═══════════════════════════════════════════════════════════
# تحلیل نماد
# ═══════════════════════════════════════════════════════════
def analyze_symbol(
    df: pd.DataFrame,
    risk_profile: str = "medium",
) -> dict | None:
    """
    تحلیل کامل یک نماد.
    
    Args:
        df: دیتافریم با open, high, low, close, volume
        risk_profile: "low" | "medium" | "high"
    
    Returns:
        dict کامل تحلیل یا None
    """
    if df is None or df.empty or len(df) < 50:
        return None

    try:
        df = compute_indicators(df)
        if df is None or df.empty:
            return None

        last20 = df.tail(20)
        resistance = safe_num(last20["high"].max())
        support = safe_num(last20["low"].min())

        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        price = safe_num(last["close"])
        atr = safe_num(last.get("atr"))
        rsi = safe_num(last.get("rsi"), 50)
        willr = safe_num(last.get("willr"), -50)
        stoch_k = safe_num(last.get("stoch_k"), 50)
        stoch_d = safe_num(last.get("stoch_d"), 50)
        adx = safe_num(last.get("adx"), 20)
        macd_h = safe_num(last.get("macd_hist"))
        prev_macd_h = safe_num(prev.get("macd_hist"))
        ema200 = safe_num(last.get("ema200"))
        bb_upper = safe_num(last.get("bb_upper"))
        bb_lower = safe_num(last.get("bb_lower"))
        vwap_last = safe_num(last.get("vwap")) if "vwap" in df.columns else None

        # ─── محاسبه امتیاز ───
        score = 0.0
        reasons = []

        if ema200 > 0:
            if price > ema200:
                score += 1.0
                reasons.append("قیمت بالای EMA200 — روند بلندمدت صعودی")
            else:
                score -= 1.0
                reasons.append("قیمت زیر EMA200 — روند بلندمدت نزولی")

        if rsi < 30:
            score += 1.5
            reasons.append(f"RSI={rsi:.0f} اشباع فروش")
        elif rsi > 70:
            score -= 1.5
            reasons.append(f"RSI={rsi:.0f} اشباع خرید")

        if willr < -80:
            score += 0.5
            reasons.append(f"Williams %R={willr:.0f} اشباع فروش")
        elif willr > -20:
            score -= 0.5
            reasons.append(f"Williams %R={willr:.0f} اشباع خرید")

        if prev_macd_h <= 0 and macd_h > 0:
            score += 1.0
            reasons.append("MACD کراس صعودی")
        elif prev_macd_h >= 0 and macd_h < 0:
            score -= 1.0
            reasons.append("MACD کراس نزولی")

        if stoch_k < 20 and stoch_d < 20:
            score += 0.5
            reasons.append("Stochastic اشباع فروش")
        elif stoch_k > 80 and stoch_d > 80:
            score -= 0.5
            reasons.append("Stochastic اشباع خرید")

        if bb_upper > 0 and bb_lower > 0:
            if price <= bb_lower * 1.005:
                score += 0.5
                reasons.append("نزدیک باند پایین Bollinger")
            elif price >= bb_upper * 0.995:
                score -= 0.5
                reasons.append("نزدیک باند بالا Bollinger")

        if vwap_last and vwap_last > 0:
            if price > vwap_last * 1.02:
                score -= 0.5
                reasons.append("قیمت بالای VWAP — ورود دیرهنگام")
            elif price < vwap_last * 0.98:
                score += 0.5
                reasons.append("قیمت زیر VWAP — فرصت ورود")

        if resistance > 0 and price >= resistance * 0.995:
            score -= 0.3
            reasons.append("نزدیک مقاومت")
        elif support > 0 and price <= support * 1.005:
            score += 0.3
            reasons.append("نزدیک حمایت")

        is_ranging = adx < 20
        if is_ranging:
            score *= 0.5
            reasons.append(f"ADX={adx:.0f} بازار رنج")

        # ─── تعیین سیگنال ───
        if is_ranging and abs(score) < 1:
            signal = "خنثی"
            explanation = "صبر کن، بازار بی‌جهته"
        elif score >= 2:
            signal = "LONG"
            explanation = "خرید خوب، با حد ضرر"
        elif score >= 1:
            signal = "LONG ضعیف"
            explanation = "خرید با احتیاط"
        elif score <= -2:
            signal = "SHORT"
            explanation = "فروش خوب، مراقب"
        elif score <= -1:
            signal = "SHORT ضعیف"
            explanation = "فروش با احتیاط"
        else:
            signal = "خنثی"
            explanation = "بدون سیگنال واضح"

        confidence = min(100, int(abs(score) * 25 + len(reasons) * 5))

        # ─── SL/TP ───
        profile = RISK_PROFILES.get(risk_profile, RISK_PROFILES["medium"])
        sl_tp = None
        rr = None

        if atr > 0 and abs(score) >= profile["min_score"]:
            if score > 0:
                sl = price - atr * profile["sl_mult"]
                tp_price = price + atr * profile["tp_mult"]
                sl_tp = {"sl": sl, "tp": tp_price, "type": "LONG"}
                if abs(price - sl) > 0:
                    rr = abs(tp_price - price) / abs(price - sl)
            else:
                sl = price + atr * profile["sl_mult"]
                tp_price = price - atr * profile["tp_mult"]
                sl_tp = {"sl": sl, "tp": tp_price, "type": "SHORT"}
                if abs(sl - price) > 0:
                    rr = abs(price - tp_price) / abs(sl - price)

        return {
            "price": price,
            "rsi": rsi,
            "willr": willr,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "adx": adx,
            "macd_hist": macd_h,
            "atr": atr,
            "ema200": ema200,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "vwap": vwap_last,
            "support": support,
            "resistance": resistance,
            "score": score,
            "signal": signal,
            "explanation": explanation,
            "confidence": confidence,
            "reasons": reasons,
            "sl_tp": sl_tp,
            "rr": rr,
            "is_ranging": is_ranging,
            "close_series": df["close"].tail(30).tolist(),
        }

    except Exception as e:
        print(f"[Analyzer] خطا در تحلیل: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# Fear & Greed
# ═══════════════════════════════════════════════════════════
def compute_fear_greed(df: pd.DataFrame) -> float:
    try:
        if df is None or df.empty or len(df) < 20:
            return 50.0

        df = compute_indicators(df)
        if df is None or df.empty:
            return 50.0

        rsi = safe_num(df["rsi"].iloc[-1], 50)
        price = safe_num(df["close"].iloc[-1])
        atr = safe_num(df["atr"].iloc[-1]) if "atr" in df.columns else 0
        macd_h = safe_num(df["macd_hist"].iloc[-1]) if "macd_hist" in df.columns else 0

        ema50_series = ta.ema(df["close"], length=50)
        if ema50_series is not None and len(ema50_series) > 0:
            ema50 = safe_num(ema50_series.iloc[-1], price)
        else:
            ema50 = price

        rsi_score = max(0, min(100, rsi))

        if atr > 0:
            stretch = ((price - ema50) / atr) * 10 + 50
            stretch = max(0, min(100, stretch))
        else:
            stretch = 50.0

        macd_score = 50 + (macd_h * 10)
        macd_score = max(0, min(100, macd_score))

        fg = rsi_score * 0.45 + stretch * 0.30 + macd_score * 0.25
        return max(0.0, min(100.0, float(fg)))

    except Exception:
        return 50.0


# ═══════════════════════════════════════════════════════════
# چک‌لیست وزن‌دار
# ═══════════════════════════════════════════════════════════
def build_checklist_weighted(tfs: dict) -> tuple[list, int, str, str]:
    items = []
    total_weight = 0
    earned_weight = 0

    r1h = tfs.get("۱ ساعت")
    r5 = tfs.get("۵ دقیقه")
    r15 = tfs.get("۱۵ دقیقه")
    r30 = tfs.get("۳۰ دقیقه")
    r1d = tfs.get("روزانه")

    if r1d:
        s = r1d.get("score", 0)
        if s >= 1:
            items.append(("✅ روند بلندمدت صعودی", "green", 15))
            earned_weight += 15
        elif s <= -1:
            items.append(("❌ روند بلندمدت نزولی", "red", 15))
        else:
            items.append(("⚠️ روند بلندمدت خنثی", "yellow", 15))
            earned_weight += 7
        total_weight += 15

    if r1h:
        adx = safe_num(r1h.get("adx"))
        if adx > 25:
            items.append((f"✅ روند قوی (ADX={adx:.0f})", "green", 10))
            earned_weight += 10
        elif adx > 20:
            items.append((f"⚠️ روند ضعیف (ADX={adx:.0f})", "yellow", 10))
            earned_weight += 5
        else:
            items.append((f"❌ بدون روند (ADX={adx:.0f})", "red", 10))
        total_weight += 10

    if r1h:
        rr = safe_num(r1h.get("rr"))
        if rr >= 1.5:
            items.append((f"✅ نسبت سود/ضرر مناسب ({rr:.1f})", "green", 10))
            earned_weight += 10
        elif rr > 0:
            items.append((f"⚠️ نسبت سود/ضرر پایین ({rr:.1f})", "yellow", 10))
            earned_weight += 5
        else:
            items.append(("❌ سیگنال معاملاتی وجود نداره", "red", 10))
        total_weight += 10

    if r1h:
        conf = r1h.get("confidence", 0)
        if conf >= 70:
            items.append((f"✅ اطمینان بالا ({conf}%)", "green", 10))
            earned_weight += 10
        elif conf >= 40:
            items.append((f"⚠️ اطمینان متوسط ({conf}%)", "yellow", 10))
            earned_weight += 5
        else:
            items.append((f"❌ اطمینان پایین ({conf}%)", "red", 10))
        total_weight += 10

    if r1h:
        rsi = safe_num(r1h.get("rsi"), 50)
        if 40 <= rsi <= 60:
            items.append((f"✅ RSI متعادل ({rsi:.0f})", "green", 10))
            earned_weight += 10
        elif 30 <= rsi <= 70:
            items.append((f"⚠️ RSI نرمال ({rsi:.0f})", "yellow", 10))
            earned_weight += 7
        else:
            items.append((f"❌ RSI اشباع ({rsi:.0f})", "red", 10))
        total_weight += 10

    if r1h:
        willr = safe_num(r1h.get("willr"), -50)
        if -70 <= willr <= -30:
            items.append((f"✅ Williams %R متعادل ({willr:.0f})", "green", 5))
            earned_weight += 5
        else:
            items.append((f"⚠️ Williams %R اشباع ({willr:.0f})", "yellow", 5))
            earned_weight += 2
        total_weight += 5

    tfs_to_check = [r5, r15, r30, r1h, r1d]
    scores_tf = [r.get("score", 0) for r in tfs_to_check if r]
    if scores_tf:
        pos = sum(1 for s in scores_tf if s > 0)
        neg = sum(1 for s in scores_tf if s < 0)
        total = len(scores_tf)
        if pos >= total - 1 and pos > neg:
            items.append((f"✅ {pos}/{total} تایم‌فریم هم‌جهت صعودی", "green", 15))
            earned_weight += 15
        elif neg >= total - 1 and neg > pos:
            items.append((f"✅ {neg}/{total} تایم‌فریم هم‌جهت نزولی", "green", 15))
            earned_weight += 15
        else:
            items.append((f"⚠️ تایم‌فریم‌ها ناهماهنگ ({pos}↑/{neg}↓)", "yellow", 15))
            earned_weight += 7
        total_weight += 15

    if r1h:
        mh = safe_num(r1h.get("macd_hist"))
        if mh > 0:
            items.append(("✅ MACD مثبت (صعودی)", "green", 5))
            earned_weight += 5
        elif mh < 0:
            items.append(("⚠️ MACD منفی (نزولی)", "yellow", 5))
            earned_weight += 2
        else:
            items.append(("❌ MACD خنثی", "red", 5))
        total_weight += 5

    if r1h:
        price = safe_num(r1h.get("price"))
        support = safe_num(r1h.get("support"))
        resistance = safe_num(r1h.get("resistance"))
        if support > 0 and resistance > 0 and price > 0:
            dist_support = abs(price - support) / price * 100
            dist_resistance = abs(resistance - price) / price * 100
            if dist_support < 1.5:
                items.append(("✅ نزدیک حمایت — ورود مناسب", "green", 10))
                earned_weight += 10
            elif dist_resistance < 1.5:
                items.append(("⚠️ نزدیک مقاومت — احتیاط", "yellow", 10))
                earned_weight += 3
            else:
                items.append(("✅ قیمت در میانه کانال", "green", 10))
                earned_weight += 7
        total_weight += 10

    if r1h:
        sl_tp = r1h.get("sl_tp")
        if sl_tp:
            items.append(("✅ حد ضرر و هدف سود تعریف شده", "green", 10))
            earned_weight += 10
        else:
            items.append(("❌ حد ضرر تعریف نشده", "red", 10))
        total_weight += 10

    percentage = int(earned_weight / total_weight * 100) if total_weight > 0 else 0

    r1h_signal = r1h.get("signal", "") if r1h else ""

    if percentage >= 80:
        if "SHORT" in r1h_signal:
            final, final_color = f"🔴 سیگنال فروش قوی — {percentage}%", "red"
        elif "LONG" in r1h_signal:
            final, final_color = f"🟢 سیگنال خرید قوی — {percentage}%", "green"
        else:
            final, final_color = f"⚪ شرایط خنثی — {percentage}%", "yellow"
    elif percentage >= 60:
        if "SHORT" in r1h_signal:
            final, final_color = f"🔴 سیگنال فروش — {percentage}%", "red"
        elif "LONG" in r1h_signal:
            final, final_color = f"🟢 سیگنال خرید — {percentage}%", "green"
        else:
            final, final_color = f"⚪ خنثی — {percentage}%", "yellow"
    elif percentage >= 40:
        final, final_color = f"⚠️ احتیاط — {percentage}% (شرایط متوسط)", "yellow"
    elif percentage >= 20:
        final, final_color = f"🟠 ضعیف — {percentage}% (بهتره صبر کنی)", "orange"
    else:
        final, final_color = f"🔴 توصیه نمی‌شه — {percentage}%", "red"

    return items, percentage, final, final_color


# ═══════════════════════════════════════════════════════════
# پاراگراف تحلیل — با تایم‌فریم
# ═══════════════════════════════════════════════════════════
def build_analysis_paragraph(
    ticker: str,
    name: str,
    tfs: dict,
    gsr: float | None = None,
    risk_profile: str = "medium",
    tf_name: str = "۱ ساعت",
) -> str:
    """
    ساخت پاراگراف تحلیل کامل به فارسی.
    
    Args:
        ticker: نماد
        name: نام فارسی
        tfs: dict تحلیل‌های همه TFها
        gsr: نسبت طلا به نقره
        risk_profile: سطح ریسک
        tf_name: تایم‌فریم مرجع تحلیل (جدید)
    """
    lines = []

    # ─── خط اول: تایم‌فریم مرجع ───
    lines.append(f"📊 تحلیل بر اساس تایم‌فریم: {tf_name}")
    lines.append(f"📍 این تحلیل با تمرکز روی تایم‌فریم {tf_name} نوشته شده.")
    lines.append("")

    r1h = tfs.get("۱ ساعت")
    r1d = tfs.get("روزانه")
    r5 = tfs.get("۵ دقیقه")
    r15 = tfs.get("۱۵ دقیقه")

    if not r1h:
        return "\n".join(lines) + "\n\nداده کافی نیست. لطفاً صبر کنید..."

    lines.append("◈ روند کلی")
    lines.append("─" * 30)
    if r1d:
        s = r1d.get("score", 0)
        if s >= 1:
            lines.append("• بلندمدت (روزانه): صعودی")
        elif s <= -1:
            lines.append("• بلندمدت (روزانه): نزولی")
        else:
            lines.append("• بلندمدت (روزانه): خنثی")

    if r5 and r15:
        avg_short = (r5.get("score", 0) + r15.get("score", 0)) / 2
        if avg_short >= 1:
            lines.append("• کوتاه‌مدت: صعودی — فشار خرید")
        elif avg_short <= -1:
            lines.append("• کوتاه‌مدت: نزولی — فشار فروش")
        else:
            lines.append("• کوتاه‌مدت: خنثی — نوسان بی‌جهت")

    r = safe_num(r1h.get("resistance"))
    s = safe_num(r1h.get("support"))
    if r > 0:
        lines.append(f"• مقاومت نزدیک: {r:,.2f}$")
    if s > 0:
        lines.append(f"• حمایت نزدیک: {s:,.2f}$")

    lines.append("")

    if r1h.get("reasons"):
        lines.append("◈ دلایل تحلیل")
        lines.append("─" * 30)
        for reason in r1h["reasons"]:
            lines.append(f"• {reason}")
        lines.append("")

    sl_tp = r1h.get("sl_tp")
    rr = safe_num(r1h.get("rr"))
    conf = r1h.get("confidence", 0)
    entry = safe_num(r1h.get("price"))

    if sl_tp:
        sl = safe_num(sl_tp.get("sl"))
        tp = safe_num(sl_tp.get("tp"))
        if sl_tp["type"] == "LONG":
            lines.append("◈ پیشنهاد خرید (LONG)")
        else:
            lines.append("◈ پیشنهاد فروش (SHORT)")
        lines.append("─" * 30)
        lines.append(f"• ورود: {entry:,.2f}$")
        lines.append(f"• حد ضرر: {sl:,.2f}$")
        lines.append(f"• هدف سود: {tp:,.2f}$")
        if rr:
            lines.append(f"• نسبت سود به ضرر: {rr:.1f}")
        lines.append(f"• اطمینان: {conf}%")
    else:
        lines.append("◈ پیشنهاد")
        lines.append("─" * 30)
        lines.append("• صبر کن تا سیگنال واضح‌تر بشه")
    lines.append("")

    prof = RISK_PROFILES.get(risk_profile, RISK_PROFILES["medium"])
    lines.append(f"◈ توصیه برای ریسک {prof['name']}")
    lines.append("─" * 30)
    lines.append(f"• {prof['advice']}")
    lines.append("")

    if gsr and "طلا" in name:
        lines.append("◈ نسبت طلا به نقره")
        lines.append("─" * 30)
        lines.append(f"• نسبت: {gsr:.1f}")
        if gsr > 80:
            lines.append("• بالای ۸۰: نقره ارزونه")
        elif gsr < 60:
            lines.append("• زیر ۶۰: طلا ارزونه")
        else:
            lines.append("• در محدوده نرمال (۶۰-۸۰)")

    return "\n".join(lines)