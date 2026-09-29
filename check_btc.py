"""
check_btc.py — نسخه ۲
تشخیص دقیق BTC-USD — چرا خنثی شده؟
"""

from core.data_fetcher import fetch_history_by_source
from core.analyzer import (
    analyze_symbol,
    RISK_PROFILES,
    _confidence_tier,
)

print("=" * 70)
print("تشخیص BTC-USD — نسخه ۲")
print("=" * 70)
print()

# ─── دریافت دیتا ───
df = fetch_history_by_source("BTC-USD", "5m", "5d", "nobitex")
if df is None or df.empty:
    print("❌ دیتا خالیه")
    exit(1)

print(f"✅ کندل‌ها: {len(df)}")
print(f"   آخرین قیمت: ${df['close'].iloc[-1]:,.2f}")
print()

# ─── تحلیل ───
result = analyze_symbol(
    df,
    risk_profile="aggressive",
    tf_name="۵ دقیقه",
    tfs_data=None,
    market_type="futures",
)

if not result:
    print("❌ تحلیل None برگشت")
    exit(1)

print("─" * 70)
print("نتیجه تحلیل")
print("─" * 70)
print(f"سیگنال:     {result['signal']}")
print(f"confidence: {result['confidence']}%")
print(f"direction:  {result['direction']}")
print(f"regime:     {result['regime']}")
print(f"ADX:        {result['adx']:.1f}")
print(f"raw_score:  {result['raw_score']:.3f}")
print(f"score:      {result['score']:.3f}")
print(f"consensus:  {result['consensus']}")
print()

# ─── محاسبه دستی confidence ───
print("─" * 70)
print("محاسبه دستی confidence")
print("─" * 70)

consensus = result["consensus"]
final_score = abs(result["raw_score"])
adx = result["adx"]
divergence = result.get("divergence", {})

# base
if consensus == "strong":
    base = 85
elif consensus == "normal":
    base = 65
elif consensus == "weak":
    base = 45
else:
    base = 0

# score_bonus
score_bonus = min(10, final_score * 15)

# adx_bonus
if adx > 40:
    adx_bonus = 5
elif adx > 25:
    adx_bonus = 3
elif adx > 20:
    adx_bonus = 0
else:
    adx_bonus = -5

# divergence penalty
div_penalty = divergence.get("penalty", 0) if divergence.get("has_divergence") else 0

manual_confidence = int(base + score_bonus + adx_bonus - div_penalty)

print(f"consensus = {consensus}")
print(f"base = {base}")
print(f"final_score = {final_score:.3f}")
print(f"score_bonus = min(10, {final_score:.3f} × 15) = {score_bonus:.2f}")
print(f"ADX = {adx:.1f} → adx_bonus = {adx_bonus}")
print(f"divergence = {divergence.get('has_divergence', False)}")
print(f"div_penalty = {div_penalty}")
print()
print(
    f"محاسبه: {base} + {score_bonus:.2f} + {adx_bonus} - {div_penalty} = {manual_confidence}"
)
print(f"کد برگردوند: {result['confidence']}%")
print()

# ─── اطلاعات پروفایل ───
print("─" * 70)
print("پروفایل")
print("─" * 70)
profile_key = "aggressive_futures"
profile = RISK_PROFILES.get(profile_key)
if profile:
    print(f"پروفایل: {profile_key}")
    print(f"min_confidence: {profile['min_confidence']}%")
    print(f"sl_mult: {profile['sl_mult']}")
    print(f"tp_mult: {profile['tp_mult']}")
    print(f"allow_short: {profile['allow_short']}")
    print()
    if result["confidence"] < profile["min_confidence"]:
        print(f"❌ خنثی شد چون {result['confidence']}% < {profile['min_confidence']}%")
    else:
        print(f"✅ پاس شد")
print()

# ─── گروه‌ها ───
print("─" * 70)
print("جزئیات گروه‌ها")
print("─" * 70)
for g_name, g_data in result["groups"].items():
    vote = g_data.get("vote", 0)
    score = g_data.get("score", 0.0)
    strength = g_data.get("strength_fa", "")
    reasons = g_data.get("reasons", [])

    vote_icon = "🟢" if vote > 0 else ("🔴" if vote < 0 else "⚪")
    print(f"{vote_icon} {g_name:12} vote={vote:+d} score={score:+.3f} ({strength})")
    for r in reasons[:3]:
        print(f"     • {r}")
    print()

# ─── پیام خنثی ───
print("─" * 70)
print("پیام خنثی")
print("─" * 70)
ne = result.get("neutral_explain", {})
if ne:
    print(f"short: {ne.get('short', '—')}")
    print(f"long:  {ne.get('long', '—')}")
    print(f"hint:  {ne.get('hint', '—')}")
else:
    print("(خالی)")
print()

print("=" * 70)
print("پایان")
print("=" * 70)
