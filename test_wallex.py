from core.wallex_fetcher import fetch_wallex_candles
import pandas as pd

for tf in ["۵ دقیقه", "۱۵ دقیقه"]:
    print(f"--- Testing {tf} ---")
    df = fetch_wallex_candles("ETH-USDT", tf)
    if df is None or df.empty:
        print(f"  ❌ No data")
    else:
        print(f"  ✅ Got {len(df)} candles")
        # محاسبه فاصله زمانی بین دو کندل آخر (به دقیقه)
        time_diff = (df.index[-1] - df.index[-2]).total_seconds() / 60
        print(f"  Time between last two candles: {time_diff} minutes")
        print(f"  First candle: {df.index[0]}")
        print(f"  Last candle: {df.index[-1]}")
