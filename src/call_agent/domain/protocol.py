from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class Branch(StrEnum):
    NEW = "new"
    EXISTING = "existing"
    MESSAGE = "message"


class ProtocolState(StrEnum):
    # Entry
    ASK_INTENT = "ask_intent"

    # New-booking branch
    ASK_FIRST_VISIT = "ask_first_visit"
    ASK_KUPAT_CHOLIM = "ask_kupat_cholim"
    CONFIRM_PRIVATE = "confirm_private"
    ASK_BIRTH_DATE = "ask_birth_date"
    ASK_VISIT_TYPE = "ask_visit_type"
    ASK_FOR_SELF = "ask_for_self"
    ASK_OTHER_NAME = "ask_other_name"
    ASK_OTHER_ID = "ask_other_id"
    ASK_OTHER_RELATION = "ask_other_relation"
    ASK_PATIENT_ID = "ask_patient_id"
    ASK_NAME = "ask_name"  # conditional: only if patient lookup by phone fails
    ASK_SMS_CONSENT = "ask_sms_consent"
    SUMMARIZE_AND_CONFIRM = "summarize_and_confirm"

    # Existing-appointment branch
    ASK_EXISTING_ACTION = "ask_existing_action"
    MORE_INFO = "more_info"
    RESCHEDULE_OFFER_SLOT = "reschedule_offer_slot"
    RESCHEDULE_CHANGE_MENU = "reschedule_change_menu"
    SUMMARIZE_RESCHEDULE = "summarize_reschedule"
    CONFIRM_CANCEL = "confirm_cancel"

    # Leave-message branch
    COLLECT_MESSAGE = "collect_message"

    # Time-selection sub-FSM (reused by new-booking and reschedule)
    TS_ASK_WINDOW = "ts_ask_window"
    TS_ASK_WHEN = "ts_ask_when"
    TS_ASK_SPECIFIC_DATE = "ts_ask_specific_date"
    TS_OFFER_SLOT = "ts_offer_slot"

    # Terminal
    DONE = "done"

    # Designed-in escape hatch for future hybrid LLM fallback. Not triggered in v1.
    STUCK = "stuck"


class VisitType(StrEnum):
    PHONE = "phone"
    IN_PERSON = "in_person"


class TimeWindow(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"


class WhenPreference(StrEnum):
    SOONEST = "soonest"
    THIS_WEEK = "this_week"
    SPECIFIC_DATE = "specific_date"


class ExistingAction(StrEnum):
    MORE_INFO = "more_info"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"


class RescheduleChangeField(StrEnum):
    VISIT_TYPE = "visit_type"
    KUPAT_CHOLIM = "kupat_cholim"


class ProtocolContext(BaseModel):
    """All data collected across a single protocol session.

    Persisted alongside ProtocolState in the conversation store.
    """

    branch: Branch | None = None

    # New-booking — collected progressively
    first_visit: bool | None = None
    kupat_cholim: str | None = None
    is_private_path: bool = False
    birth_date: date | None = None
    visit_type: VisitType | None = None

    # Time-selection (used by new-booking and reschedule sub-flow)
    time_window: TimeWindow | None = None
    when_pref: WhenPreference | None = None
    specific_date: date | None = None
    offered_slot_start: datetime | None = None
    offered_slot_end: datetime | None = None
    offered_appt_type_id: UUID | None = None

    # Patient identity
    for_self: bool | None = None
    other_name: str | None = None
    other_id_number: str | None = None
    other_relation: str | None = None
    patient_id_number: str | None = None
    patient_name: str | None = None  # filled by ASK_NAME when lookup fails
    sms_consent: bool | None = None

    # Existing-appointment branch
    existing_appt_id: UUID | None = None

    # Leave-message branch
    message_body: str | None = None
