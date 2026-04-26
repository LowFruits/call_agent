from __future__ import annotations

from datetime import date

import pytest

from call_agent.domain.protocol import (
    Branch,
    ExistingAction,
    RescheduleChangeField,
    TimeWindow,
    VisitType,
    WhenPreference,
)
from call_agent.services.protocol.validators import (
    is_valid_israeli_id,
    match_kupah,
    parse_date,
    parse_existing_action,
    parse_int_choice,
    parse_intent,
    parse_reschedule_change_field,
    parse_time_window,
    parse_visit_type,
    parse_when_preference,
    parse_yes_no,
)

# ---------------------------------------------------------------------------
# is_valid_israeli_id
# ---------------------------------------------------------------------------

# Known-valid IDs (each computed: products mod9-collapsed sum to multiple of 10)
@pytest.mark.parametrize("id_str", ["000000018", "123456782", "111111118"])
def test_valid_israeli_id(id_str: str) -> None:
    assert is_valid_israeli_id(id_str) is True


@pytest.mark.parametrize(
    "id_str",
    [
        "123456789",  # bad checksum
        "987654321",  # bad checksum
        "12345678",  # too short
        "1234567890",  # too long
        "abcdefghi",  # not digits
        "",
    ],
)
def test_invalid_israeli_id(id_str: str) -> None:
    assert is_valid_israeli_id(id_str) is False


def test_id_with_whitespace_is_trimmed() -> None:
    assert is_valid_israeli_id("  123456782  ") is True


# ---------------------------------------------------------------------------
# parse_int_choice
# ---------------------------------------------------------------------------

def test_parse_int_choice_digit() -> None:
    assert parse_int_choice("1", 3) == 1
    assert parse_int_choice("3", 3) == 3
    assert parse_int_choice("4", 3) is None


def test_parse_int_choice_with_text() -> None:
    assert parse_int_choice("אני רוצה אופציה 2", 3) == 2


def test_parse_int_choice_hebrew_word() -> None:
    assert parse_int_choice("אחד", 3) == 1
    assert parse_int_choice("שניים", 3) == 2


# ---------------------------------------------------------------------------
# parse_yes_no
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", ["כן", "yes", "y", "1", "אישור"])
def test_parse_yes(msg: str) -> None:
    assert parse_yes_no(msg) is True


@pytest.mark.parametrize("msg", ["לא", "no", "n", "2", "ביטול"])
def test_parse_no(msg: str) -> None:
    assert parse_yes_no(msg) is False


def test_parse_yes_no_unknown() -> None:
    assert parse_yes_no("maybe") is None


# ---------------------------------------------------------------------------
# parse_intent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "msg, expected",
    [
        ("1", Branch.EXISTING),
        ("2", Branch.NEW),
        ("3", Branch.MESSAGE),
        ("יש לי תור קיים", Branch.EXISTING),
        ("אני רוצה תור חדש", Branch.NEW),
        ("רוצה להשאיר הודעה", Branch.MESSAGE),
    ],
)
def test_parse_intent(msg: str, expected: Branch) -> None:
    assert parse_intent(msg) == expected


def test_parse_intent_unknown() -> None:
    assert parse_intent("hello") is None


# ---------------------------------------------------------------------------
# parse_visit_type / time_window / when_preference
# ---------------------------------------------------------------------------

def test_parse_visit_type() -> None:
    assert parse_visit_type("1") == VisitType.PHONE
    assert parse_visit_type("טלפוני") == VisitType.PHONE
    assert parse_visit_type("פרונטלי") == VisitType.IN_PERSON
    assert parse_visit_type("xyz") is None


def test_parse_time_window() -> None:
    assert parse_time_window("בוקר") == TimeWindow.MORNING
    assert parse_time_window("אחר הצהריים") == TimeWindow.AFTERNOON
    assert parse_time_window("1") == TimeWindow.MORNING


def test_parse_when_preference() -> None:
    assert parse_when_preference("1") == WhenPreference.SOONEST
    assert parse_when_preference("השבוע") == WhenPreference.THIS_WEEK
    assert parse_when_preference("יום ספציפי") == WhenPreference.SPECIFIC_DATE


# ---------------------------------------------------------------------------
# parse_existing_action / reschedule_change_field
# ---------------------------------------------------------------------------

def test_parse_existing_action() -> None:
    assert parse_existing_action("1") == ExistingAction.MORE_INFO
    assert parse_existing_action("לשנות") == ExistingAction.RESCHEDULE
    assert parse_existing_action("בטל") == ExistingAction.CANCEL


def test_parse_reschedule_change_field() -> None:
    assert parse_reschedule_change_field("1") == RescheduleChangeField.VISIT_TYPE
    assert parse_reschedule_change_field("קופת חולים") == RescheduleChangeField.KUPAT_CHOLIM


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "msg, expected",
    [
        ("01/01/2000", date(2000, 1, 1)),
        ("31-12-1999", date(1999, 12, 31)),
        ("15.06.1985", date(1985, 6, 15)),
        ("2000-05-12", date(2000, 5, 12)),
    ],
)
def test_parse_date(msg: str, expected: date) -> None:
    assert parse_date(msg) == expected


def test_parse_date_invalid() -> None:
    assert parse_date("not a date") is None


# ---------------------------------------------------------------------------
# match_kupah
# ---------------------------------------------------------------------------

def test_match_kupah_by_index() -> None:
    accepted = ["Clalit", "Maccabi", "Meuhedet"]
    assert match_kupah("2", accepted) == "Maccabi"


def test_match_kupah_by_name() -> None:
    accepted = ["Clalit", "Maccabi", "Meuhedet"]
    assert match_kupah("Maccabi", accepted) == "Maccabi"
    assert match_kupah("מכבי maccabi", accepted) == "Maccabi"


def test_match_kupah_unknown() -> None:
    assert match_kupah("Unknown", ["Clalit", "Maccabi"]) is None
