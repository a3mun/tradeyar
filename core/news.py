"""
core/news.py
دریافت اخبار از منابع فارسی و انگلیسی
نسخه ۵.۰ — با cloudscraper + فیلتر دو مرحله‌ای + blacklist
"""

import re

# تلاش برای import
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    print("[News] هشدار: cloudscraper نصب نیست.")

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("[News] هشدار: feedparser نصب نیست.")


# ═══════════════════════════════════════════════════════════
# هدرها
# ═══════════════════════════════════════════════════════════
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

TIMEOUT = 12


# ═══════════════════════════════════════════════════════════
# منابع
# ═══════════════════════════════════════════════════════════
RSS_SOURCES = [
    # ─── فارسی ───
    {
        "name": "دنیای اقتصاد",
        "url": "https://donya-e-eqtesad.com/rss",
        "lang": "fa",
        "category": "اقتصاد کلان",
        "needs_scraper": True,
    },
    {
        "name": "اقتصادنیوز",
        "url": "https://www.eghtesadnews.com/rss",
        "lang": "fa",
        "category": "بازارها",
        "needs_scraper": True,
    },
    {
        "name": "اکوایران",
        "url": "https://ecoiran.com/rss",
        "lang": "fa",
        "category": "تحلیل",
        "needs_scraper": True,
    },
    {
        "name": "صدای بورس",
        "url": "https://www.sedayebourse.ir/rss",
        "lang": "fa",
        "category": "بورس",
        "needs_scraper": False,
    },
    # ─── انگلیسی ───
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "lang": "en",
        "category": "کریپتو",
        "needs_scraper": False,
    },
    {
        "name": "Investing",
        "url": "https://www.investing.com/rss/news_285.rss",
        "lang": "en",
        "category": "اقتصاد جهانی",
        "needs_scraper": False,
    },
]


# ═══════════════════════════════════════════════════════════
# کلیدواژه‌های تخصصی
# ═══════════════════════════════════════════════════════════
KEYWORDS_FA = [
    # طلا و فلزات
    "طلا", "سکه", "نقره", "مثقال", "گرم طلا", "انس جهانی", "انس طلا",
    "سکه امامی", "نیم سکه", "ربع سکه", "طلای ۱۸", "طلای 18",
    # ارز
    "دلار", "یورو", "درهم", "نرخ ارز", "بازار ارز", "تتر", "ارز دیجیتال",
    # انرژی
    "نفت", "برنت", "نفت خام", "گاز طبیعی", "بنزین", "اوپک",
    # کریپتو
    "بیت‌کوین", "اتریوم", "کریپتو", "رمزارز",
    # کلان
    "نرخ بهره", "فدرال رزرو", "بانک مرکزی", "تورم",
    # بورس
    "بورس تهران", "شاخص بورس", "شاخص کل", "فرابورس",
]

# ⚠️ لیست سیاه — اگه خبری این کلمات رو داشت، رد بشه
KEYWORDS_BLACKLIST_FA = [
    "کارگر", "دستمزد", "بیمه", "بازنشستگی", "خودرو", "پلاک",
    "کاتالیست", "پتروشیمی", "فولاد", "سیمان", "دارو", "درمان",
    "آموزش", "دانشگاه", "کنکور", "ورزش", "فوتبال", "سینما",
    "انتخابات شورا", "شهرداری", "کلاهبردار", "دستگیری", "قتل", "سرقت",
]

KEYWORDS_EN = [
    "gold", "silver", "bullion", "precious metal", "spot gold",
    "dollar", "euro", "currency", "forex", "dxy",
    "oil", "brent", "wti", "crude", "opec", "natural gas",
    "bitcoin", "crypto", "ethereum", "btc", "eth",
    "inflation", "fed", "federal reserve", "interest rate",
    "s&p 500", "nasdaq", "dow jones", "treasury yield",
]


# ═══════════════════════════════════════════════════════════
# اخبار پشتیبان
# ═══════════════════════════════════════════════════════════
FALLBACK_NEWS = [
    ("Fed", "فدرال رزرو نرخ بهره را ۲۵ واحد افزایش داد"),
    ("Goldman", "گلدمن ساکس: هدف طلا ۵۴۰۰ دلار تا ۲۰۲۷"),
    ("UBS", "UBS: هدف طلا ۴۶۰۰ دلار در ۲۰۲۶"),
    ("WGC", "بانک‌های مرکزی ۲۴۴ تن طلا خریدند"),
    ("Reuters", "بانک مرکزی چین ذخایر طلای خود را افزایش داد"),
]


# ═══════════════════════════════════════════════════════════
# فیلتر دو مرحله‌ای
# ═══════════════════════════════════════════════════════════
def matches_keywords(text: str, lang: str = "fa") -> bool:
    """
    فیلتر دو مرحله‌ای:
    1. حداقل ۲ کلیدواژه تخصصی (برای فارسی)
    2. هیچ کلمه‌ای از blacklist نباشه
    """
    if not text or len(text) < 25:
        return False

    text_lower = text.lower()

    if lang == "fa":
        # چک blacklist اول
        for bad in KEYWORDS_BLACKLIST_FA:
            if bad in text:
                return False

        # شمارش کلیدواژه‌های تخصصی
        matched = [kw for kw in KEYWORDS_FA if kw in text]
        return len(matched) >= 2  # ← حداقل ۲ تا

    else:
        matched = [kw for kw in KEYWORDS_EN if kw.lower() in text_lower]
        return len(matched) >= 1  # انگلیسی‌ها سخت‌گیرانه نباشن


# ═══════════════════════════════════════════════════════════
# دریافت محتوا
# ═══════════════════════════════════════════════════════════
def fetch_content(url: str, needs_scraper: bool = False, timeout: int = TIMEOUT) -> str | None:
    """دریافت محتوای RSS"""
    if needs_scraper and HAS_CLOUDSCRAPER:
        try:
            scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            r = scraper.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"[News] خطای cloudscraper {url[:40]}: {e}")

    try:
        import requests
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════
# دریافت از منبع
# ═══════════════════════════════════════════════════════════
def fetch_rss(source: dict, max_items: int = 3) -> list:
    """دریافت اخبار از یه منبع"""
    if not HAS_FEEDPARSER:
        return []

    feed = None

    try:
        content = fetch_content(source["url"], source.get("needs_scraper", False))
        if content:
            feed = feedparser.parse(content)
    except Exception:
        pass

    if not feed or not feed.entries:
        try:
            feed = feedparser.parse(source["url"])
        except Exception:
            return []

    if not feed.entries:
        return []

    news = []
    for entry in feed.entries[:max_items * 6]:  # بیشتر بگیر
        try:
            title = entry.get("title", "").strip()
            if not title or len(title) < 20:
                continue

            title = re.sub(r"<[^>]+>", "", title).strip()

            if not matches_keywords(title, source["lang"]):
                continue

            summary = entry.get("summary", "") or entry.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:250]

            news.append({
                "source": source["name"],
                "category": source["category"],
                "title": title,
                "summary": summary,
                "lang": source["lang"],
                "link": entry.get("link", ""),
                "published": entry.get("published", "") or entry.get("updated", ""),
            })

            if len(news) >= max_items:
                break

        except Exception:
            continue

    return news


# ═══════════════════════════════════════════════════════════
# تابع اصلی
# ═══════════════════════════════════════════════════════════
def fetch_news(max_per_source: int = 3, total_max: int = 15) -> list:
    """دریافت اخبار از همه منابع"""
    all_news = []
    seen_titles = set()

    for source in RSS_SOURCES:
        news = fetch_rss(source, max_items=max_per_source)
        for item in news:
            title_key = item["title"][:60].lower().strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            all_news.append(item)

    if len(all_news) < 3:
        for src, title in FALLBACK_NEWS:
            all_news.append({
                "source": src,
                "category": "پشتیبان",
                "title": title,
                "summary": "",
                "lang": "fa",
                "link": "",
                "published": "",
            })

    all_news.sort(key=lambda x: x.get("published", ""), reverse=True)
    return all_news[:total_max]


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("تست core/news.py (نسخه ۵.۰)")
    print("=" * 55)
    print()

    print(f"feedparser:      {'✓' if HAS_FEEDPARSER else '✗'}")
    print(f"cloudscraper:    {'✓' if HAS_CLOUDSCRAPER else '✗'}")
    print()

    print("دریافت اخبار...")
    news = fetch_news(max_per_source=3, total_max=15)
    print(f"تعداد اخبار نهایی: {len(news)}")
    print()

    source_count = {}
    for item in news:
        source_count[item["source"]] = source_count.get(item["source"], 0) + 1

    print("توزیع:")
    for source, count in source_count.items():
        print(f"   {source}: {count}")
    print()

    print("─" * 55)

    for i, item in enumerate(news, 1):
        print(f"{i}. [{item['source']}] ({item['category']})")
        print(f"   {item['title'][:100]}")
        if item.get("summary"):
            print(f"   > {item['summary'][:120]}")
        print()

    print("[OK] تست کامل شد.")