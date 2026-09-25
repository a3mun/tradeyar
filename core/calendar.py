"""
core/calendar.py
تقویم اقتصادی — ایران‌بروکر
نسخه ۲.۰ — با دو سناریو (بالاتر/پایین‌تر از انتظار)
"""

import re
from datetime import datetime, timedelta

import cloudscraper
from bs4 import BeautifulSoup

from .utils import get_iran_time, to_english_digits


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

TIMEOUT = 20
CALENDAR_URL = "https://iranbroker.net/economic-calendar/?irbc_view=month&irbc_offset=this"


CURRENCY_INFO = {
    "USD": {"country": "آمریکا", "flag": "🇺🇸", "priority": 1},
    "EUR": {"country": "اروپا", "flag": "🇪🇺", "priority": 1},
    "CNY": {"country": "چین", "flag": "🇨🇳", "priority": 1},
    "GBP": {"country": "انگلیس", "flag": "🇬🇧", "priority": 2},
    "JPY": {"country": "ژاپن", "flag": "🇯🇵", "priority": 2},
    "CHF": {"country": "سوئیس", "flag": "🇨🇭", "priority": 3},
    "CAD": {"country": "کانادا", "flag": "🇨🇦", "priority": 3},
    "AUD": {"country": "استرالیا", "flag": "🇦🇺", "priority": 4},
    "NZD": {"country": "نیوزلند", "flag": "🇳🇿", "priority": 4},
}


CATEGORY_MAP = {
    "interest-rate": "🏦 نرخ بهره",
    "inflation": "💰 تورم",
    "employment": "👥 اشتغال",
    "gdp": "📊 تولید ناخالص",
    "trade": "📦 تجارت",
    "energy": "🛢 انرژی",
    "consumer": "🛍 مصرف",
    "housing": "🏠 مسکن",
    "business": "💼 کسب‌وکار",
    "misc": "📰 سایر",
}


# ═══════════════════════════════════════════════════════════
# MARKET_IMPACT — با دو سناریو
# ═══════════════════════════════════════════════════════════
MARKET_IMPACT = {
    "interest-rate": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
    },
    "inflation": {
        "high": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "employment": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "gdp": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "trade": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "energy": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
    },
    "consumer": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "housing": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
        },
    },
    "business": {
        "high": {
            "gold":   {"dir": "down", "label": "نزولی", "icon": "📉"},
            "dollar": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "crypto": {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "oil":    {"dir": "up",   "label": "صعودی", "icon": "📈"},
        },
        "low": {
            "gold":   {"dir": "up",   "label": "صعودی", "icon": "📈"},
            "dollar": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "crypto": {"dir": "down", "label": "نزولی", "icon": "📉"},
            "oil":    {"dir": "down", "label": "نزولی", "icon": "📉"},
        },
    },
    "misc": {
        "high": {
            "gold":   {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "dollar": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
        },
        "low": {
            "gold":   {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "dollar": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "crypto": {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
            "oil":    {"dir": "warn", "label": "بی‌تأثیر", "icon": "•"},
        },
    },
}


def fetch_html(url: str, timeout: int = TIMEOUT):
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        r = scraper.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"[Calendar] خطا در fetch: {e}")
    return None


def extract_events(html: str) -> list:
    events = []
    if not html:
        return events

    try:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr", attrs={"data-event-id": True})

        for row in rows:
            try:
                event_id = row.get("data-event-id", "")
                currency = row.get("data-currency", "").upper()
                impact = row.get("data-impact", "low").lower()
                category = row.get("data-category", "misc").lower()
                timestamp_raw = row.get("data-timestamp-raw", "")

                title_fa = ""
                title_en = ""
                title_td = row.find("td", class_="ibwEventTitle")
                if title_td:
                    en_span = title_td.find("span", class_="ibwTooltipText")
                    if en_span:
                        title_en = en_span.get_text(strip=True)
                    a_tag = title_td.find("a")
                    if a_tag:
                        for span in a_tag.find_all("span"):
                            span.decompose()
                        title_fa = a_tag.get_text(strip=True)
                    else:
                        title_fa = title_td.get_text(strip=True)

                time_str = ""
                time_td = row.find("td", class_="ibwTime")
                if time_td:
                    time_str = time_td.get_text(strip=True)
                    time_str = to_english_digits(time_str)
                    time_str = re.sub(r"[^\d:]", "", time_str)

                event_date = None
                if timestamp_raw:
                    try:
                        event_date = datetime.strptime(timestamp_raw, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

                if not time_str or not currency or not title_fa:
                    continue

                events.append({
                    "event_id": event_id,
                    "time": time_str,
                    "date": event_date,
                    "currency": currency,
                    "country": CURRENCY_INFO.get(currency, {}).get("country", currency),
                    "flag": CURRENCY_INFO.get(currency, {}).get("flag", "🌍"),
                    "priority": CURRENCY_INFO.get(currency, {}).get("priority", 5),
                    "title_fa": title_fa,
                    "title_en": title_en,
                    "impact": impact,
                    "category": category,
                    "category_fa": CATEGORY_MAP.get(category, "📰 سایر"),
                    "market_impact": MARKET_IMPACT.get(category, MARKET_IMPACT["misc"]),
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[Calendar] خطا در استخراج: {e}")

    return events


def filter_by_hours(events, hours_ahead=24):
    now = get_iran_time().replace(tzinfo=None)
    cutoff = now + timedelta(hours=hours_ahead)
    return [e for e in events if e["date"] and now <= e["date"] <= cutoff]


def filter_by_days(events, days_ahead=7):
    now = get_iran_time().replace(tzinfo=None)
    cutoff = now + timedelta(days=days_ahead)
    return [e for e in events if e["date"] and now <= e["date"] <= cutoff]


def fetch_calendar(hours_ahead=24, days_ahead=7, include_medium=True):
    html = fetch_html(CALENDAR_URL)
    all_events = extract_events(html)
    major = [e for e in all_events if e["priority"] <= 2]

    critical_pool = [e for e in major if e["impact"] == "high"]
    critical = filter_by_hours(critical_pool, hours_ahead)
    critical.sort(key=lambda x: (x["date"] or datetime.max, x["time"]))

    if include_medium:
        weekly_pool = [e for e in major if e["impact"] in ("high", "medium")]
    else:
        weekly_pool = [e for e in major if e["impact"] == "high"]

    weekly = filter_by_days(weekly_pool, days_ahead)
    critical_ids = {e["event_id"] for e in critical}
    weekly = [e for e in weekly if e["event_id"] not in critical_ids]
    weekly.sort(key=lambda x: (x["date"] or datetime.max, x["time"]))

    all_filtered = critical + weekly

    by_category = {}
    for ev in all_filtered:
        cat = ev["category_fa"]
        by_category.setdefault(cat, []).append(ev)

    return {
        "critical": critical,
        "weekly": weekly,
        "all": all_filtered,
        "by_category": by_category,
        "total_critical": len(critical),
        "total_weekly": len(weekly),
        "total_all": len(all_filtered),
        "timestamp": get_iran_time().strftime("%Y-%m-%d %H:%M:%S"),
    }


if __name__ == "__main__":
    print("=" * 65)
    print("تست core/calendar.py")
    print("=" * 65)
    result = fetch_calendar()
    print(f"هشدار فوری: {result['total_critical']}")
    print(f"هفته: {result['total_weekly']}")
    for ev in result["weekly"][:3]:
        print(f"\n🔴 {ev['time']} | {ev['flag']} {ev['title_fa']}")
        impact = ev.get("market_impact", {})
        high = impact.get("high", {}).get("gold", {})
        low = impact.get("low", {}).get("gold", {})
        print(f"   طلا اگه بالا بیاد: {high.get('label')}")
        print(f"   طلا اگه پایین بیاد: {low.get('label')}")