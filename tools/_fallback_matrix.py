"""
tools/_fallback_matrix.py
جدول fallback — (ticker × source × tf)
============================================================
قبل (نسخه ۱.۶): آبان‌تتر به نوبیتکس fallback می‌زد → قیمت یکسان
بعد (نسخه ۱.۷): قیمت مستقل + source_used شفاف
"""

import logging
import time

logging.basicConfig(level=logging.CRITICAL)

from services.analyzer_service import analyze
from services.cache import clear_all_negative, data_cache
from services.data_service import fetch_quote

TICKERS = ["BTC-USD", "ETH-USD", "PAXG-USD", "PAXG-IRT", "USDT-IRT", "XAUT-USD"]
SOURCES = ["nobitex", "bitpin", "wallex", "abantether"]
TFS = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]

SEP = "=" * 96

data_cache.clear()
clear_all_negative()

# ═══════════════════════════════════════════════════════════
print(SEP)
print("جدول تحلیل — (ticker × source × tf)")
print("  ✅ = تحلیل گرفت | ✅(xxx) = fallback به xxx | ─ = صرافی این بازار را ندارد")
print(SEP)
print()
print(f"{'صرافی':<11} {'نماد':<11} " + " ".join(f"{t:^9}" for t in TFS))
print("-" * 96)

stats = {"ok": 0, "fb": 0, "none": 0, "na": 0}
t0 = time.perf_counter()

for source in SOURCES:
    for ticker in TICKERS:
        cells = []
        for tf in TFS:
            try:
                r = analyze(
                    ticker, source, tf,
                    market_type="futures",
                    risk_profile="aggressive",
                    ticker_name=ticker,
                    use_cache=True,
                )
            except Exception:
                r = None

            if r:
                used = r.get("source_used", source)
                if used != source:
                    cells.append(f"✅{used[:3]}")
                    stats["fb"] += 1
                else:
                    cells.append("✅")
                    stats["ok"] += 1
            else:
                # ─── آیا صرافی این بازار را ساختاراً ندارد؟ ───
                upper = ticker.upper()
                is_usdt = upper.endswith("-USD")
                if source == "abantether" and is_usdt:
                    cells.append("─")  # ─── بازار ندارد ───
                    stats["na"] += 1
                else:
                    cells.append("❌")
                    stats["none"] += 1
        print(f"{source:<11} {ticker:<11} " + " ".join(f"{c:^9}" for c in cells))

el = time.perf_counter() - t0
print("-" * 96)
total = sum(stats.values())
print(f"  ✅ مستقیم: {stats['ok']}  |  ✅ fallback: {stats['fb']}  |  "
      f"─ ندارد: {stats['na']}  |  ❌ خالی: {stats['none']}")
print(f"  مجموع: {total} ترکیب در {el:.1f}s")
success = stats["ok"] + stats["fb"]
print(f"  📊 نرخ موفقیت تحلیل: {success}/{total} = {success/total*100:.0f}٪")
print()

# ═══════════════════════════════════════════════════════════
print(SEP)
print("جدول قیمت — استقلال صرافی‌ها (تست کاربر)")
print(SEP)
print()
print(f"{'نماد':<11} " + " ".join(f"{s:>16}" for s in SOURCES))
print("-" * 96)

for ticker in ["PAXG-USD", "PAXG-IRT", "BTC-USD", "BTC-IRT"]:
    prices = {}
    for s in SOURCES:
        try:
            q = fetch_quote(ticker, s)
        except Exception:
            q = None
        prices[s] = q["price"] if q else None

    row = " ".join(
        f"{(f'{p:,.0f}' if p else '—'):>16}" for p in prices.values()
    )
    print(f"{ticker:<11} {row}")

print("-" * 96)

# ─── چک استقلال ───
print()
print("بررسی استقلال قیمت‌ها:")
issues = 0
for ticker in ["PAXG-USD", "BTC-USD", "ETH-USD"]:
    np_ = fetch_quote(ticker, "nobitex")
    ap = fetch_quote(ticker, "abantether")
    if np_ and ap:
        print(f"  ❌ {ticker}: نوبیتکس و آبان‌تتر هر دو قیمت دارند!")
        issues += 1
    elif ap is None:
        print(f"  ✅ {ticker}: آبان‌تتر None (بازار تتری ندارد)")
    else:
        print(f"  ⚠️ {ticker}: نوبیتکس None ولی آبان‌تتر قیمت دارد")

if issues == 0:
    print("\n  ✅ همه‌ی قیمت‌ها مستقل‌اند — هیچ ادغامی نیست")
else:
    print(f"\n  ❌ {issues} مورد ادغام قیمت")

print()
print(SEP)
