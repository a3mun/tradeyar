import re
import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://iranbroker.net/economic-calendar/"
SOURCE_NAME = "IranBroker"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

_cache = {
    "current": {
        "events": [],
        "updated_at": None,
        "cache_date": None,
    },
    "next": {
        "events": [],
        "updated_at": None,
        "cache_date": None,
    },
}

_cache_lock = threading.Lock()


def _tehran_now():
    return datetime.now(TEHRAN_TZ)


def _normalize_digits(value: str) -> str:
    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"

    for index, digit in enumerate(persian):
        value = value.replace(digit, str(index))

    for index, digit in enumerate(arabic):
        value = value.replace(digit, str(index))

    return value


def _is_high_impact(row) -> bool:
    markers = []

    for element in [row, *row.find_all(True)]:
        markers.extend(
            [
                element.get("class", []),
                element.get("title", ""),
                element.get("aria-label", ""),
                element.get("data-impact", ""),
            ]
        )

    text = " ".join(
        str(item)
        for group in markers
        for item in (group if isinstance(group, list) else [group])
    ).lower()

    high_markers = (
        "high",
        "impact-red",
        "impact red",
        "زیاد",
        "زیاد تاثیر",
    )

    return any(marker in text for marker in high_markers)


def _extract_event(row, current_day: str):
    cells = row.find_all(["td", "th"], recursive=False)

    values = [cell.get_text(" ", strip=True) for cell in cells]

    values = [value for value in values if value]

    if len(values) < 3:
        return None

    time_pattern = re.compile(
        r"^\d{1,2}:\d{2}(?:\s*[AP]M)?$",
        re.IGNORECASE,
    )

    event_time = ""
    currency = ""
    event_name = ""

    currencies = {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CHF",
        "CAD",
        "AUD",
        "NZD",
        "CNY",
        "XAU",
    }

    candidates = []

    for value in values:
        normalized = _normalize_digits(value).strip()

        if time_pattern.match(normalized):
            event_time = value
            continue

        if normalized.upper() in currencies:
            currency = normalized.upper()
            continue

        if normalized.lower() in {
            "actual",
            "forecast",
            "previous",
            "واقعی",
            "پیش‌بینی",
            "قبلی",
        }:
            continue

        if normalized in {"کم", "متوسط", "زیاد"}:
            continue

        candidates.append(value)

    if not candidates:
        return None

    event_name = candidates[0]

    return {
        "day": current_day,
        "time": event_time,
        "currency": currency,
        "event": event_name,
        "actual": "",
        "forecast": "",
        "previous": "",
    }


def _parse_calendar(html: str):
    soup = BeautifulSoup(html, "html.parser")
    events = []

    current_day = ""

    weekdays = (
        "شنبه",
        "یکشنبه",
        "دوشنبه",
        "سه‌شنبه",
        "چهارشنبه",
        "پنجشنبه",
        "جمعه",
    )

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)

        if not cells:
            continue

        values = [cell.get_text(" ", strip=True) for cell in cells]

        values = [value for value in values if value]

        if not values:
            continue

        first_cell = values[0]

        if any(first_cell.startswith(day) for day in weekdays):
            current_day = first_cell
            continue

        joined = " ".join(values).lower()

        if "تاثیر" in joined and ("واقعی" in joined or "پیش" in joined):
            continue

        if len(cells) < 3 or not _is_high_impact(row):
            continue

        event = _extract_event(row, current_day)

        if event:
            events.append(event)

    # حذف رویدادهای تکراری
    unique_events = []
    seen = set()

    for event in events:
        key = (
            event["day"],
            event["time"],
            event["currency"],
            event["event"],
        )

        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    return unique_events


def get_weekly_calendar(
    week: str = "current",
    force_refresh: bool = False,
):
    if week not in {"current", "next"}:
        raise ValueError("Invalid week")

    today = _tehran_now().date()

    with _cache_lock:
        cached = _cache[week]

        # کش فقط در همان روز معتبر است.
        if not force_refresh and cached["events"] and cached["cache_date"] == today:
            return {
                "ok": True,
                "events": cached["events"],
                "count": len(cached["events"]),
                "updated_at": cached["updated_at"],
                "source": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "week": week,
            }

        params = {
            "irbc_view": "week",
        }

        if week == "next":
            params["irbc_offset"] = "next"

        response = requests.get(
            SOURCE_URL,
            params=params,
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()

        events = _parse_calendar(response.text)

        if not events:
            raise ValueError("No calendar events found")

        updated_at = _tehran_now().isoformat()

        _cache[week] = {
            "events": events,
            "updated_at": updated_at,
            "cache_date": today,
        }

        return {
            "ok": True,
            "events": events,
            "count": len(events),
            "updated_at": updated_at,
            "source": SOURCE_NAME,
            "source_url": response.url,
            "week": week,
        }
