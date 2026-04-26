from __future__ import annotations

from call_agent.domain.models import Route
from call_agent.domain.protocol import (
    ExistingAction,
    ProtocolContext,
    ProtocolState,
    RescheduleChangeField,
    VisitType,
)
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he
from call_agent.services.protocol.handlers.common import (
    KUPOT_CHOLIM,
    format_when,
)
from call_agent.services.protocol.validators import (
    match_kupah,
    parse_existing_action,
    parse_int_choice,
    parse_reschedule_change_field,
    parse_visit_type,
    parse_yes_no,
)


async def handle_ask_existing_action(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    action = parse_existing_action(message)
    if action is None:
        # Re-prompt — we no longer have the appt summary, so just ask the menu
        return ProtocolState.ASK_EXISTING_ACTION, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    if action == ExistingAction.MORE_INFO:
        return ProtocolState.MORE_INFO, context, prompts_he.ASK_MORE_INFO_QUESTION

    if action == ExistingAction.CANCEL:
        return ProtocolState.CONFIRM_CANCEL, context, prompts_he.CONFIRM_CANCEL

    # RESCHEDULE — enter time-selection sub-FSM
    return ProtocolState.TS_ASK_WINDOW, context, prompts_he.ASK_TIME_WINDOW


async def handle_more_info(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    body = message.strip()
    if not body:
        return ProtocolState.MORE_INFO, context, prompts_he.ASK_MORE_INFO_QUESTION
    context.message_body = body
    if route.doctor_id is not None:
        await api.create_message(
            doctor_id=route.doctor_id,
            patient_phone=patient_phone,
            body=f"[שאלה על תור קיים] {body}",
            patient_name=context.patient_name,
        )
    return ProtocolState.DONE, context, prompts_he.MESSAGE_SAVED


async def handle_confirm_cancel(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return ProtocolState.CONFIRM_CANCEL, context, prompts_he.CONFIRM_CANCEL
    if answer is False:
        return ProtocolState.DONE, context, prompts_he.CANCEL_ABORTED
    if context.existing_appt_id is None:
        return ProtocolState.DONE, context, prompts_he.CANCEL_ABORTED
    await api.cancel_appointment(context.existing_appt_id, reason="patient request")
    return ProtocolState.DONE, context, prompts_he.CANCELLED_CONFIRMATION


async def handle_reschedule_offer_slot(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    choice = parse_int_choice(message, 3)
    if choice is None:
        when = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        reply = prompts_he.RESCHEDULE_OFFER_MENU_TEMPLATE.format(when=when)
        return ProtocolState.RESCHEDULE_OFFER_SLOT, context, reply
    if choice == 1:
        # Confirm → summarize
        when = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        summary = f"מועד חדש: {when}"
        reply = prompts_he.SUMMARY_CONFIRM_RESCHEDULE_TEMPLATE.format(summary=summary)
        return ProtocolState.SUMMARIZE_RESCHEDULE, context, reply
    if choice == 2:
        # Pick a different time → loop back
        context.offered_slot_start = None
        context.offered_slot_end = None
        return ProtocolState.TS_ASK_WINDOW, context, prompts_he.ASK_TIME_WINDOW
    # choice == 3 — change something else
    return (
        ProtocolState.RESCHEDULE_CHANGE_MENU,
        context,
        prompts_he.RESCHEDULE_CHANGE_MENU,
    )


async def handle_reschedule_change_menu(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    field = parse_reschedule_change_field(message)
    if field is None:
        return (
            ProtocolState.RESCHEDULE_CHANGE_MENU,
            context,
            prompts_he.RESCHEDULE_CHANGE_MENU,
        )
    if field == RescheduleChangeField.VISIT_TYPE:
        # Re-ask visit type, then re-run time-selection
        return ProtocolState.ASK_VISIT_TYPE, context, prompts_he.ASK_VISIT_TYPE
    # KUPAT_CHOLIM
    return ProtocolState.ASK_KUPAT_CHOLIM, context, prompts_he.ASK_KUPAT_CHOLIM


async def handle_summarize_reschedule(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        when = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        summary = f"מועד חדש: {when}"
        reply = prompts_he.SUMMARY_CONFIRM_RESCHEDULE_TEMPLATE.format(summary=summary)
        return ProtocolState.SUMMARIZE_RESCHEDULE, context, reply
    if answer is False:
        return ProtocolState.DONE, context, prompts_he.GENERIC_GOODBYE

    # Confirmed — execute reschedule. The Scheduling API doesn't have a direct
    # reschedule endpoint, so cancel + book under the new slot.
    if context.existing_appt_id is not None:
        await api.cancel_appointment(
            context.existing_appt_id, reason="rescheduled by patient"
        )

    if (
        route.doctor_id is None
        or context.offered_slot_start is None
        or context.offered_appt_type_id is None
    ):
        return ProtocolState.DONE, context, prompts_he.BOOKING_FAILED

    patient = await api.find_patient_by_phone(patient_phone)
    if patient is None:
        return ProtocolState.DONE, context, prompts_he.BOOKING_FAILED

    from call_agent.domain.enums import BookedBy
    from call_agent.domain.models import BookRequest

    await api.book_appointment(
        BookRequest(
            doctor_id=route.doctor_id,
            patient_id=patient.id,
            appointment_type_id=context.offered_appt_type_id,
            start_time=context.offered_slot_start,
            booked_by=BookedBy.AGENT,
            notes="rescheduled",
        )
    )
    return ProtocolState.DONE, context, prompts_he.RESCHEDULE_DONE


# Suppress unused-import warnings (some imports used implicitly)
_ = (KUPOT_CHOLIM, match_kupah, parse_visit_type, VisitType)
