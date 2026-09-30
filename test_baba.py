"""
test_baba.py
"""

import json
from pathlib import Path

# ۱. BABA توی JSON هست؟
path = Path("data/symbols_master.json")
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

baba_keys = [k for k in data.keys() if "BABA" in k.upper()]
print(f"BABA در JSON: {baba_keys}")
print()

# ۲. sample از کلیدها
all_keys = list(data.keys())
print(f"کلیدهای نمونه (۲۰):")
for k in all_keys[:20]:
    print(f"  {k} → {data[k]}")
print()

# ۳. توی NOBITEX_SYMBOLS چک
from core.nobitex_fetcher import NOBITEX_SYMBOLS, is_in_nobitex

print(f"BABA در NOBITEX_SYMBOLS:")
for k in NOBITEX_SYMBOLS.keys():
    if "BABA" in k.upper():
        print(f"  {k} → {NOBITEX_SYMBOLS[k]}")
print()

print(f"is_in_nobitex('BABA-USD'): {is_in_nobitex('BABA-USD')}")
