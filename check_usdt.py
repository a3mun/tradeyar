"""
check_usdt.py
چک دقیق USDT-IRT
"""

from core.nobitex_fetcher import (
    fetch_nobitex_for_ticker,
    fetch_nobitex_stats_for_ticker,
    fetch_nobitex_history,
    map_symbol_to_nobitex,
)
from core.analyzer import analyze_symbol

print("=" * 70)
print("تشخیص USDT-IRT")
print("=" * 70)
print()

# ۱. نگاشت
print(f"【۱】map_symbol_to_nobitex('USDT-IRT'): {map_symbol_to_nobitex('USDT-IRT')}")
print()

# ۲. Stats
print("【۲】fetch_nobitex_stats_for_ticker('USDT-IRT'):")
stats = fetch_nobitex_stats_for_ticker("USDT-IRT")
if stats:
    print(f"   price: {stats['price']:,.2f}")
    print(f"   best_buy: {stats['best_buy']:,.2f}")
    print(f"   best_sell: {stats['best_sell']:,.2f}")
else:
    print("   ❌ None")
print()

# ۳. OHLCV خام
print("【۳】fetch_nobitex_history('USDTIRT', '5', ...) — خام:")
import time

to_ts = int(time.time())
from_ts = to_ts - 5 * 86400
df_raw = fetch_nobitex_history("USDTIRT", "5", from_ts, to_ts)
if df_raw is not None and not df_raw.empty:
    print(f"   آخرین close: {df_raw['close'].iloc[-1]:,.2f}")
else:
    print("   ❌ خالی")
print()

# ۴. OHLCV از ticker (با تبدیل)
print("【۴】fetch_nobitex_for_ticker('USDT-IRT', '5m', '5d'):")
df = fetch_nobitex_for_ticker("USDT-IRT", "5m", "5d")
if df is not None and not df.empty:
    print(f"   آخرین close: {df['close'].iloc[-1]:,.2f}")
else:
    print("   ❌ خالی")
print()

# ۵. تحلیل
print("【۵】analyze_symbol (بعد از تبدیل):")
if df is not None and not df.empty:
    result = analyze_symbol(
        df,
        risk_profile="aggressive",
        tf_name="۵ دقیقه",
        tfs_data=None,
        market_type="futures",
    )
    if result:
        print(f"   price: {result['price']:,.2f}")
        print(f"   resistance: {result.get('resistance', 0):,.2f}")
        print(f"   support: {result.get('support', 0):,.2f}")
        pivots = result.get("pivots", {})
        for k in ["r3", "r2", "r1", "pivot", "s1", "s2", "s3"]:
            v = pivots.get(k, 0)
            if v:
                print(f"   pivot.{k}: {v:,.2f}")
print()

print("=" * 70)
print("پایان")
print("=" * 70)
