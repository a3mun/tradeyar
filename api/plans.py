"""
api/plans.py
تعریف پلن‌های اشتراک — فاز ۱۲
"""

from datetime import datetime, timezone, timedelta


def calculate_new_end_date(
    current_end_date: datetime | None, days_to_add: int
) -> datetime:
    """
    محاسبه تاریخ انقضای جدید.

    - اگر اشتراک فعاله (تاریخ انقضا > الان): از تاریخ انقضا اضافه می‌شه.
    - اگر اشتراک منقضی شده یا نداره: از همین الان اضافه می‌شه.
    - همیشه ساعت ۲۳:۵۹:۵۹ روز آخر تموم می‌شه.
    """
    now = datetime.now(timezone.utc)

    # تعیین نقطه شروع
    if current_end_date and current_end_date > now:
        # اشتراک فعاله: از تاریخ انقضای فعلی اضافه کن
        start_date = current_end_date
    else:
        # اشتراک منقضی شده یا نداره: از الان اضافه کن
        start_date = now

    # محاسبه تاریخ پایان (روز + ساعت 23:59:59)
    new_end = start_date + timedelta(days=days_to_add)

    # تنظیم ساعت به 23:59:59
    new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)

    return new_end


PLANS = {
    "1_month": {
        "id": "1_month",
        "title": "اشتراک یک ماهه",
        "price": 390000,  # ⬅️ قیمت جدید (تخفیف‌خورده)
        "old_price": 590000,
        "days": 30,
    },
    "3_months": {
        "id": "3_months",
        "title": "اشتراک سه ماهه",
        "price": 1050000,
        "old_price": 1770000,
        "days": 90,
    },
    "6_months": {
        "id": "6_months",
        "title": "اشتراک شش ماهه",
        "price": 1870000,
        "old_price": 3540000,
        "days": 180,
    },
    "12_months": {
        "id": "12_months",
        "title": "اشتراک یک ساله",
        "price": 3270000,
        "old_price": 7080000,
        "days": 365,
    },
}
