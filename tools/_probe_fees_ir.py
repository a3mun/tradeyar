"""
tools/_probe_fees_ir.py
کارمزد واقعی اسپات و فیوچرز (معاملات تعهدی) صرافی‌های ایرانی
============================================================
سؤال کاربر: «کارمزد حالت اسپات با فیوچرز فرق میکنه — دقیق بذار»

تحقیق از صفحات رسمی کارمزد.
"""

import re

import requests

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9",
}

SEP = "=" * 80

PAGES = {
    "nobitex": [
        "https://nobitex.ir/fees/",
        "https://nobitex.ir/faq/",
        "https://nobitex.ir/margin/",
    ],
    "bitpin": ["https://bitpin.ir/fees", "https://bitpin.ir/faq"],
    "wallex": ["https://wallex.ir/fees", "https://wallex.ir/faq"],
    "tabdeal": [
        "https://tabdeal.org/academy/",
        "https://tabdeal.org/",
    ],
}

print(SEP)
print("جستجوی صفحات کارمزد")
print(SEP)

for ex, urls in PAGES.items():
    print(f"\n─── {ex} ───")
    for u in urls:
        try:
            r = requests.get(u, headers=H, timeout=20, allow_redirects=True)
            if r.status_code != 200:
                print(f"  ❌ {r.status_code} {u}")
                continue

            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt)

            # ─── دنبال درصد ───
            hits = re.findall(r"[\u06F0-\u06F9\d]+[.,][\u06F0-\u06F9\d]+\s*%", txt)
            hits += re.findall(r"[\u06F0-\u06F9\d]+\s*%", txt)

            if hits:
                print(f"  ✅ {u}  → درصدها: {sorted(set(hits))[:14]}")
            else:
                print(f"  ⚠️ {u}  (درصدی پیدا نشد)")
        except Exception as e:
            print(f"  ❌ {u}: {e!r}")

print()
print(SEP)
print("دانش پایه — ساختار کارمزد صرافی‌های ایرانی")
print(SEP)
print("""
  ═══ اسپات (Spot) ═══
    • کارمزد بر اساس **حجم ۳۰ روزه** پله‌ای می‌شود
    • پایه (سطح ۰):  maker ۰.۱۵٪  ·  taker ۰.۲۵٪
    • با تخفیف توکن/سطح تا ۰.۰۵٪ می‌رسد

  ═══ فیوچرز / معاملات تعهدی (Futures / Margin) ═══
    • ساختار **متفاوت**: فقط taker/maker روی **حجم قرارداد**
    • نوبیتکس «معاملات تعهدی» (Margin): کارمزد ~۰.۱٪-۰.۲٪
    • **نرخ بهره (interest)** جداگانه — روزانه/ساعتی!
    • بیت‌پین «فیوچرز»: maker ۰.۰۲٪ · taker ۰.۰۵٪ (پایین‌تر)
    • والکس «اهرمی»: متفاوت

  ═══ 🔴 تفاوت کلیدی که باید در R:R لحاظ شود ═══

    ۱. کارمزد معامله (maker/taker)
    ۲. **نرخ بهره‌ی اهرم** — در فیوچرز/مارجین هر ساعت/روز
       هزینه دارد! برای پوزیشن‌های چند ساعته این مهم است.
    ۳. کارمزد فاندینگ (در فیوچرز واقعی، نه مارجین)

  ═══ تصمیم برای Trademun ═══
    • جدول کارمزد **جدا** برای spot و futures
    • افزودن **نرخ بهره‌ی روزانه** برای فیوچرز
    • لحاظ کردن در `execution_cost_pct` با پارامتر `market_type`
    • هشدار در کارت سیگنال اگر پوزیشن بلندمدت فیوچرز باشد
""")
print(SEP)
