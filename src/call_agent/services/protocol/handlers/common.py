from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from call_agent.domain.models import AvailabilityRule, CalendarException
from call_agent.domain.protocol import TimeWindow

_TZ = ZoneInfo("Asia/Jerusalem")

# Hebrew kupot list — single source of truth for the menu and matching.
KUPOT_CHOLIM = ["כללית", "מכבי", "מאוחדת", "לאומית", "פרטי"]

# Window boundaries in local Asia/Jerusalem hours.
_MORNING_END_HOUR = 12
_NOON_END_HOUR = 15

# API DayOfWeek -> Python weekday() index (Monday=0..Sunday=6).
_API_DOW_TO_PY: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Hebrew weekday names keyed by Python weekday() (Monday=0..Sunday=6).
_WEEKDAY_NAMES_HE: dict[int, str] = {
    6: "ראשון",
    0: "שני",
    1: "שלישי",
    2: "רביעי",
    3: "חמישי",
    4: "שישי",
    5: "שבת",
}


def slot_in_window(slot_start: datetime, window: TimeWindow) -> bool:
    """Return True if the slot's local hour falls in the chosen window."""
    return slot_window(slot_start) == window


def slot_window(slot_start: datetime) -> TimeWindow:
    """Bucket a slot start into its TimeWindow by local hour."""
    local = slot_start.astimezone(_TZ) if slot_start.tzinfo else slot_start
    h = local.hour
    if h < _MORNING_END_HOUR:
        return TimeWindow.MORNING
    if h < _NOON_END_HOUR:
        return TimeWindow.NOON
    return TimeWindow.EVENING


def working_weekdays(rules: list[AvailabilityRule]) -> set[int]:
    """Return the Python weekday() indices on which the doctor accepts patients."""
    return {
        _API_DOW_TO_PY[r.day_of_week]
        for r in rules
        if r.is_active and r.day_of_week in _API_DOW_TO_PY
    }


def is_date_blocked(d: date, exceptions: list[CalendarException]) -> bool:
    """True if a full-day blocked exception covers this date."""
    return any(
        e.date == d and e.exception_type == "blocked"
        and e.start_time is None and e.end_time is None
        for e in exceptions
    )


def format_working_days(rules: list[AvailabilityRule]) -> str:
    """Render the doctor's working days as a Hebrew list (Sun→Sat order)."""
    weekdays = working_weekdays(rules)
    py_order = [6, 0, 1, 2, 3, 4, 5]  # Sun, Mon, Tue, Wed, Thu, Fri, Sat
    names = [_WEEKDAY_NAMES_HE[w] for w in py_order if w in weekdays]
    return ", ".join(names)


def format_when(slot_start: datetime) -> str:
    """Human-readable Hebrew date+time for a slot.

    Builds the string in Python rather than via strftime — Windows' strftime
    can't encode non-ASCII format characters under some locales.
    """
    local = slot_start.astimezone(_TZ) if slot_start.tzinfo else slot_start
    weekday = _WEEKDAY_NAMES_HE[local.weekday()]
    return (
        f"יום {weekday} {local.strftime('%d/%m/%Y')} בשעה {local.strftime('%H:%M')}"
    )


def format_slot_line(n: int, slot_start: datetime) -> str:
    """Single-line rendering of an offered slot (used in TS_OFFER_* menus)."""
    local = slot_start.astimezone(_TZ) if slot_start.tzinfo else slot_start
    weekday = _WEEKDAY_NAMES_HE[local.weekday()]
    return f"{n}. יום {weekday} {local.strftime('%d/%m/%Y')} - {local.strftime('%H:%M')}"
