from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

import httpx

from call_agent.domain.models import Route, TimeSlot
from call_agent.domain.protocol import (
    Branch,
    ProtocolContext,
    ProtocolState,
    TimeWindow,
    WhenPreference,
)
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he
from call_agent.services.protocol.handlers.common import (
    format_when,
    slot_in_window,
)
from call_agent.services.protocol.validators import (
    parse_date,
    parse_time_window,
    parse_when_preference,
    parse_yes_no,
)

logger = logging.getLogger(__name__)

_LOOKAHEAD_DAYS = 14


async def handle_ask_window(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    window = parse_time_window(message)
    if window is None:
        return ProtocolState.TS_ASK_WINDOW, context, prompts_he.ASK_TIME_WINDOW
    context.time_window = window
    return ProtocolState.TS_ASK_WHEN, context, prompts_he.ASK_WHEN


async def handle_ask_when(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    when = parse_when_preference(message)
    if when is None:
        return ProtocolState.TS_ASK_WHEN, context, prompts_he.ASK_WHEN
    context.when_pref = when
    if when == WhenPreference.SPECIFIC_DATE:
        return ProtocolState.TS_ASK_SPECIFIC_DATE, context, prompts_he.ASK_SPECIFIC_DATE

    return await _find_and_offer_slot(context, route, api)


async def handle_ask_specific_date(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    parsed = parse_date(message)
    if parsed is None:
        return ProtocolState.TS_ASK_SPECIFIC_DATE, context, prompts_he.INVALID_DATE
    context.specific_date = parsed
    return await _find_and_offer_slot(context, route, api)


async def handle_offer_slot(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        when_str = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        return ProtocolState.TS_OFFER_SLOT, context, (
            prompts_he.OFFER_SLOT_TEMPLATE.format(when=when_str)
        )
    if answer is False:
        # User rejected — restart time selection
        context.offered_slot_start = None
        context.offered_slot_end = None
        context.offered_appt_type_id = None
        return ProtocolState.TS_ASK_WHEN, context, prompts_he.ASK_WHEN

    # Confirmed — branch to next step
    if context.branch == Branch.EXISTING:
        when = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        reply = prompts_he.RESCHEDULE_OFFER_MENU_TEMPLATE.format(when=when)
        return ProtocolState.RESCHEDULE_OFFER_SLOT, context, reply
    # NEW branch
    return ProtocolState.ASK_FOR_SELF, context, prompts_he.ASK_FOR_SELF


# ---------------------------------------------------------------------------
# Internals — slot search
# ---------------------------------------------------------------------------

async def _find_and_offer_slot(
    context: ProtocolContext,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    if route.doctor_id is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    appt_types = await api.list_appointment_types(route.doctor_id)
    target_name = "ביקור ראשון" if context.first_visit else "ביקור חוזר"
    appt_type = next(
        (t for t in appt_types if target_name in t.name),
        appt_types[0] if appt_types else None,
    )
    if appt_type is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    candidate_dates = _candidate_dates(context)
    chosen: TimeSlot | None = None
    try:
        for d in candidate_dates:
            slots = await api.get_available_slots(
                doctor_id=route.doctor_id,
                slot_date=d,
                appointment_type_id=appt_type.id,
            )
            for s in slots:
                if context.time_window is None or slot_in_window(s.start_time, context.time_window):
                    chosen = s
                    break
            if chosen is not None:
                break
    except httpx.HTTPStatusError:
        logger.exception("slots fetch failed (likely doctor/type mismatch)")
        context.time_window = None
        context.when_pref = None
        context.specific_date = None
        context.offered_appt_type_id = None
        return ProtocolState.TS_ASK_WINDOW, context, (
            prompts_he.BOOKING_SLOT_GONE + "\n\n" + prompts_he.ASK_TIME_WINDOW
        )

    if chosen is None:
        # Reset window/when so user can adjust
        context.time_window = None
        context.when_pref = None
        context.specific_date = None
        return ProtocolState.TS_ASK_WINDOW, context, (
            prompts_he.NO_SLOTS_AVAILABLE + "\n\n" + prompts_he.ASK_TIME_WINDOW
        )

    context.offered_slot_start = chosen.start_time
    context.offered_slot_end = chosen.end_time
    context.offered_appt_type_id = appt_type.id
    when_str = format_when(chosen.start_time)
    reply = prompts_he.OFFER_SLOT_TEMPLATE.format(when=when_str)
    return ProtocolState.TS_OFFER_SLOT, context, reply


def _candidate_dates(context: ProtocolContext) -> list[date]:
    today = datetime.now(UTC).date()
    if context.when_pref == WhenPreference.SPECIFIC_DATE and context.specific_date:
        return [context.specific_date]
    if context.when_pref == WhenPreference.THIS_WEEK:
        return [today + timedelta(days=i) for i in range(7)]
    # SOONEST or fallback
    return [today + timedelta(days=i) for i in range(_LOOKAHEAD_DAYS)]


# Used in tests to verify the window helper
__all__ = [
    "handle_ask_specific_date",
    "handle_ask_when",
    "handle_ask_window",
    "handle_offer_slot",
]


# Suppress unused-import warning for TimeWindow (used implicitly via slot_in_window)
_ = TimeWindow
