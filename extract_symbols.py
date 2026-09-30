"""
extract_symbols.py
استخراج لیست کامل نمادهای نوبیتکس
"""

import json
from pathlib import Path

from core.nobitex_fetcher import fetch_all_nobitex_symbols

print("دریافت نمادهای نوبیتکس...")

# USDT pairs
usdt_syms = fetch_all_nobitex_symbols("usdt")
print(f"USDT pairs: {len(usdt_syms)}")

# RLS pairs (تومانی)
rls_syms = fetch_all_nobitex_symbols("rls")
print(f"RLS pairs: {len(rls_syms)}")

# ساخت نگاشت
mapping = {}
for s in usdt_syms:
    base = s.get("base", "").upper()
    quote = s.get("quote", "").upper()
    if base and quote:
        our_ticker = f"{base}-USD" if quote == "USDT" else f"{base}-{quote}"
        nobitex_sym = s.get("symbol", "")
        if nobitex_sym:
            mapping[our_ticker] = nobitex_sym

for s in rls_syms:
    base = s.get("base", "").upper()
    quote = s.get("quote", "").upper()
    if base and quote:
        our_ticker = f"{base}-IRT"
        nobitex_sym = s.get("symbol", "")
        if nobitex_sym:
            mapping[our_ticker] = nobitex_sym

print(f"کل نگاشت: {len(mapping)}")

# ذخیره
out_path = Path("data/symbols_master.json")
out_path.parent.mkdir(exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print(f"ذخیره شد: {out_path}")
