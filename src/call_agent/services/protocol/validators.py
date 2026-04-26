from __future__ import annotations

import re
from datetime import date, datetime

from call_agent.domain.protocol import (
    Branch,
    ExistingAction,
    RescheduleChangeField,
    TimeWindow,
    VisitType,
    WhenPreference,
)


def is_valid_israeli_id(value: str) -> bool:
    """Validate a 9-digit Israeli teudat zehut by its checksum digit.

    Algorithm: multiply each digit alternately by 1 and 2 (left-to-right);
    if the product is two digits, sum its digits; sum all products; valid iff
    the total mod 10 equals 0.
    """
    s = value.strip()
    if not s.isdigit() or len(s) != 9:
        return False
    total = 0
    for i, ch in enumerate(s):
        d = int(ch) * ((i % 2) + 1)
        if d > 9:
            d -= 9
        total += d
    return total % 10 == 0


def parse_int_choice(message: str, max_choice: int) -> int | None:
    """Extract a digit 1..max_choice from the user's message.

    Accepts plain digits and Hebrew number words for 1-3.
    """
    s = message.strip()
    hebrew_words = {
        "אחד": 1, "ראשון": 1, "ראשונה": 1,
        "שניים": 2, "שני": 2, "שתיים": 2, "שנייה": 2,
        "שלושה": 3, "שלוש": 3, "שלישי": 3,
    }
    if s in hebrew_words and hebrew_words[s] <= max_choice:
        return hebrew_words[s]
    match = re.search(r"\b([1-9])\b", s)
    if match:
        n = int(match.group(1))
        if 1 <= n <= max_choice:
            return n
    return None


def parse_yes_no(message: str) -> bool | None:
    s = message.strip().lower()
    yes_tokens = {"כן", "yes", "y", "1", "אישור", "מאשר", "מאשרת", "אוקיי", "ok", "כמובן"}
    no_tokens = {"לא", "no", "n", "2", "ביטול", "מבטל", "מבטלת"}
    if s in yes_tokens:
        return True
    if s in no_tokens:
        return False
    if any(t in s for t in ("כן", "yes", "אישור")):
        return True
    if any(t in s for t in ("לא", "no")):
        return False
    return None


def parse_intent(message: str) -> Branch | None:
    """Parse the opening intent: existing / new / leave-message."""
    choice = parse_int_choice(message, 3)
    if choice == 1:
        return Branch.EXISTING
    if choice == 2:
        return Branch.NEW
    if choice == 3:
        return Branch.MESSAGE

    s = message.strip()
    if any(kw in s for kw in ("קיים", "יש לי תור", "התור שלי")):
        return Branch.EXISTING
    if any(kw in s for kw in ("חדש", "לקבוע", "לקבע", "תור חדש")):
        return Branch.NEW
    if any(kw in s for kw in ("הודעה", "להשאיר", "להעביר")):
        return Branch.MESSAGE
    return None


def parse_visit_type(message: str) -> VisitType | None:
    choice = parse_int_choice(message, 2)
    if choice == 1:
        return VisitType.PHONE
    if choice == 2:
        return VisitType.IN_PERSON
    s = message.strip()
    if any(kw in s for kw in ("טלפ", "phone", "וידאו")):
        return VisitType.PHONE
    if any(kw in s for kw in ("פרונט", "פיזי", "במרפאה", "פנים", "in person", "in-person")):
        return VisitType.IN_PERSON
    return None


def parse_time_window(message: str) -> TimeWindow | None:
    choice = parse_int_choice(message, 2)
    if choice == 1:
        return TimeWindow.MORNING
    if choice == 2:
        return TimeWindow.AFTERNOON
    s = message.strip()
    if any(kw in s for kw in ("בוקר", "morning")):
        return TimeWindow.MORNING
    if any(kw in s for kw in ("צהריים", "ערב", "אחרי", "afternoon", "evening")):
        return TimeWindow.AFTERNOON
    return None


def parse_when_preference(message: str) -> WhenPreference | None:
    choice = parse_int_choice(message, 3)
    if choice == 1:
        return WhenPreference.SOONEST
    if choice == 2:
        return WhenPreference.THIS_WEEK
    if choice == 3:
        return WhenPreference.SPECIFIC_DATE
    s = message.strip()
    if any(kw in s for kw in ("הקרוב", "מהר", "asap", "soonest")):
        return WhenPreference.SOONEST
    if any(kw in s for kw in ("השבוע", "שבוע", "this week")):
        return WhenPreference.THIS_WEEK
    if any(kw in s for kw in ("ספציפי", "תאריך", "יום")):
        return WhenPreference.SPECIFIC_DATE
    return None


def parse_existing_action(message: str) -> ExistingAction | None:
    choice = parse_int_choice(message, 3)
    if choice == 1:
        return ExistingAction.MORE_INFO
    if choice == 2:
        return ExistingAction.RESCHEDULE
    if choice == 3:
        return ExistingAction.CANCEL
    s = message.strip()
    if any(kw in s for kw in ("פרטים", "מידע", "לדעת")):
        return ExistingAction.MORE_INFO
    if any(kw in s for kw in ("שנה", "לשנות", "שינוי", "להזיז")):
        return ExistingAction.RESCHEDULE
    if any(kw in s for kw in ("בטל", "לבטל", "ביטול")):
        return ExistingAction.CANCEL
    return None


def parse_reschedule_change_field(message: str) -> RescheduleChangeField | None:
    choice = parse_int_choice(message, 2)
    if choice == 1:
        return RescheduleChangeField.VISIT_TYPE
    if choice == 2:
        return RescheduleChangeField.KUPAT_CHOLIM
    s = message.strip()
    if any(kw in s for kw in ("טלפ", "פרונט", "סוג", "ביקור")):
        return RescheduleChangeField.VISIT_TYPE
    if any(kw in s for kw in ("קופ", "kupah")):
        return RescheduleChangeField.KUPAT_CHOLIM
    return None


_DATE_PATTERNS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%Y-%m-%d", "%Y/%m/%d",
]


def parse_date(message: str) -> date | None:
    """Parse a date in common Israeli formats (day-first)."""
    s = message.strip()
    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(s, pattern).date()
        except ValueError:
            continue
    return None


def match_kupah(message: str, accepted: list[str]) -> str | None:
    """Match a user's kupah string against the doctor's accepted list.

    Case-insensitive substring match; also accepts a 1-based numeric choice.
    """
    s = message.strip().lower()
    if not s:
        return None
    choice = parse_int_choice(message, len(accepted))
    if choice is not None:
        return accepted[choice - 1]
    for kupah in accepted:
        if kupah.lower() in s or s in kupah.lower():
            return kupah
    return None
