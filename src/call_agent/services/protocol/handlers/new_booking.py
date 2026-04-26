from __future__ import annotations

import logging

import httpx

from call_agent.domain.enums import BookedBy
from call_agent.domain.models import BookRequest, Route
from call_agent.domain.protocol import (
    ProtocolContext,
    ProtocolState,
    VisitType,
)
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he
from call_agent.services.protocol.handlers.common import KUPOT_CHOLIM, format_when
from call_agent.services.protocol.validators import (
    is_valid_israeli_id,
    match_kupah,
    parse_date,
    parse_visit_type,
    parse_yes_no,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step 1: first visit?
# ---------------------------------------------------------------------------

async def handle_ask_first_visit(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return ProtocolState.ASK_FIRST_VISIT, context, prompts_he.ASK_FIRST_VISIT
    context.first_visit = answer
    return ProtocolState.ASK_KUPAT_CHOLIM, context, prompts_he.ASK_KUPAT_CHOLIM


# ---------------------------------------------------------------------------
# Step 2: kupat cholim
# ---------------------------------------------------------------------------

async def handle_ask_kupat_cholim(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    matched = match_kupah(message, KUPOT_CHOLIM)
    if matched is None:
        return ProtocolState.ASK_KUPAT_CHOLIM, context, prompts_he.ASK_KUPAT_CHOLIM

    context.kupat_cholim = matched
    if matched == "פרטי":
        context.is_private_path = True
        return ProtocolState.CONFIRM_PRIVATE, context, prompts_he.CONFIRM_PRIVATE

    return ProtocolState.ASK_BIRTH_DATE, context, prompts_he.ASK_BIRTH_DATE


async def handle_confirm_private(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return ProtocolState.CONFIRM_PRIVATE, context, prompts_he.CONFIRM_PRIVATE
    if answer is False:
        # Back to kupah selection
        context.is_private_path = False
        context.kupat_cholim = None
        return ProtocolState.ASK_KUPAT_CHOLIM, context, prompts_he.ASK_KUPAT_CHOLIM
    return ProtocolState.ASK_BIRTH_DATE, context, prompts_he.ASK_BIRTH_DATE


# ---------------------------------------------------------------------------
# Step 3: birth date
# ---------------------------------------------------------------------------

async def handle_ask_birth_date(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    parsed = parse_date(message)
    if parsed is None:
        return ProtocolState.ASK_BIRTH_DATE, context, prompts_he.INVALID_DATE
    context.birth_date = parsed
    return ProtocolState.ASK_VISIT_TYPE, context, prompts_he.ASK_VISIT_TYPE


# ---------------------------------------------------------------------------
# Step 4: visit type
# ---------------------------------------------------------------------------

async def handle_ask_visit_type(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    visit = parse_visit_type(message)
    if visit is None:
        return ProtocolState.ASK_VISIT_TYPE, context, prompts_he.ASK_VISIT_TYPE
    context.visit_type = visit
    # Enter the time-selection sub-FSM
    return ProtocolState.TS_ASK_WINDOW, context, prompts_he.ASK_TIME_WINDOW


# ---------------------------------------------------------------------------
# Step 5: for self?
# ---------------------------------------------------------------------------

async def handle_ask_for_self(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return ProtocolState.ASK_FOR_SELF, context, prompts_he.ASK_FOR_SELF
    context.for_self = answer
    if answer:
        return ProtocolState.ASK_PATIENT_ID, context, prompts_he.ASK_PATIENT_ID
    return ProtocolState.ASK_OTHER_NAME, context, prompts_he.ASK_OTHER_NAME


async def handle_ask_other_name(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    name = message.strip()
    if not name:
        return ProtocolState.ASK_OTHER_NAME, context, prompts_he.ASK_OTHER_NAME
    context.other_name = name
    return ProtocolState.ASK_OTHER_ID, context, prompts_he.ASK_OTHER_ID


async def handle_ask_other_id(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    id_str = message.strip()
    if not is_valid_israeli_id(id_str):
        return ProtocolState.ASK_OTHER_ID, context, prompts_he.INVALID_ID
    context.other_id_number = id_str
    return ProtocolState.ASK_OTHER_RELATION, context, prompts_he.ASK_OTHER_RELATION


async def handle_ask_other_relation(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    relation = message.strip()
    if not relation:
        return ProtocolState.ASK_OTHER_RELATION, context, prompts_he.ASK_OTHER_RELATION
    context.other_relation = relation
    return ProtocolState.ASK_SMS_CONSENT, context, prompts_he.ASK_SMS_CONSENT


# ---------------------------------------------------------------------------
# Step 6: own ID + name (if patient lookup fails)
# ---------------------------------------------------------------------------

async def handle_ask_patient_id(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    id_str = message.strip()
    if not is_valid_israeli_id(id_str):
        return ProtocolState.ASK_PATIENT_ID, context, prompts_he.INVALID_ID
    context.patient_id_number = id_str

    # Try to find the patient by phone — if missing, we'll need their name
    patient = await api.find_patient_by_phone(patient_phone)
    if patient is None:
        return ProtocolState.ASK_NAME, context, prompts_he.ASK_NAME
    context.patient_name = f"{patient.first_name} {patient.last_name}".strip()
    return ProtocolState.ASK_SMS_CONSENT, context, prompts_he.ASK_SMS_CONSENT


async def handle_ask_name(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    name = message.strip()
    if not name:
        return ProtocolState.ASK_NAME, context, prompts_he.ASK_NAME
    context.patient_name = name
    return ProtocolState.ASK_SMS_CONSENT, context, prompts_he.ASK_SMS_CONSENT


# ---------------------------------------------------------------------------
# Step 7: SMS consent
# ---------------------------------------------------------------------------

async def handle_ask_sms_consent(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return ProtocolState.ASK_SMS_CONSENT, context, prompts_he.ASK_SMS_CONSENT
    context.sms_consent = answer
    summary = _format_summary(context)
    reply = prompts_he.SUMMARY_CONFIRM_NEW_TEMPLATE.format(summary=summary)
    return ProtocolState.SUMMARIZE_AND_CONFIRM, context, reply


# ---------------------------------------------------------------------------
# Step 8: summarize & confirm → book
# ---------------------------------------------------------------------------

async def handle_summarize_and_confirm(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        # Re-show the summary
        summary = _format_summary(context)
        reply = prompts_he.SUMMARY_CONFIRM_NEW_TEMPLATE.format(summary=summary)
        return ProtocolState.SUMMARIZE_AND_CONFIRM, context, reply
    if answer is False:
        return ProtocolState.DONE, context, prompts_he.GENERIC_GOODBYE

    # Confirmed — book
    try:
        await _book_appointment(context, patient_phone, route, api)
    except httpx.HTTPStatusError:
        logger.exception("booking call failed")
        return ProtocolState.DONE, context, prompts_he.BOOKING_FAILED

    when = (
        format_when(context.offered_slot_start)
        if context.offered_slot_start else ""
    )
    return ProtocolState.DONE, context, f"{prompts_he.BOOKING_DONE} {when}".strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_summary(context: ProtocolContext) -> str:
    lines: list[str] = []
    if context.offered_slot_start is not None:
        lines.append(f"מועד: {format_when(context.offered_slot_start)}")
    if context.visit_type is not None:
        kind = "טלפוני" if context.visit_type == VisitType.PHONE else "פרונטלי"
        lines.append(f"סוג ביקור: {kind}")
    if context.kupat_cholim:
        lines.append(f"קופת חולים: {context.kupat_cholim}")
    if context.for_self is False and context.other_name:
        lines.append(f"עבור: {context.other_name}")
    return "\n".join(lines)


async def _book_appointment(
    context: ProtocolContext,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> None:
    if route.doctor_id is None or context.offered_slot_start is None:
        raise RuntimeError("missing doctor or slot at booking time")

    patient = await api.find_patient_by_phone(patient_phone)
    if patient is None:
        full_name = (context.patient_name or "מטופל").split(" ", 1)
        first = full_name[0]
        last = full_name[1] if len(full_name) > 1 else ""
        patient = await api.create_patient(
            first_name=first, last_name=last, phone=patient_phone
        )

    appt_types = await api.list_appointment_types(route.doctor_id)
    target_name = "ביקור ראשון" if context.first_visit else "ביקור חוזר"
    chosen = next(
        (t for t in appt_types if target_name in t.name),
        appt_types[0] if appt_types else None,
    )
    if chosen is None:
        raise RuntimeError("no appointment types configured")

    notes_parts: list[str] = []
    if context.for_self is False:
        notes_parts.append(
            f"הוזמן עבור: {context.other_name} (תז {context.other_id_number}, "
            f"קרבה: {context.other_relation})"
        )
    if context.is_private_path:
        notes_parts.append("מסלול פרטי")
    if context.sms_consent:
        notes_parts.append("שלח SMS אישור")

    await api.book_appointment(
        BookRequest(
            doctor_id=route.doctor_id,
            patient_id=patient.id,
            appointment_type_id=chosen.id,
            start_time=context.offered_slot_start,
            booked_by=BookedBy.AGENT,
            notes="; ".join(notes_parts) or None,
        )
    )
