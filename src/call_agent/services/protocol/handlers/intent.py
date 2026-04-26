from __future__ import annotations

from datetime import UTC, datetime

from call_agent.domain.enums import AppointmentStatus
from call_agent.domain.models import Route
from call_agent.domain.protocol import Branch, ProtocolContext, ProtocolState
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he
from call_agent.services.protocol.handlers.common import format_when
from call_agent.services.protocol.validators import parse_intent


async def handle_ask_intent(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    intent = parse_intent(message)

    if intent is None:
        # Treat unrecognised input as the first turn — show the greeting menu.
        if context.branch is None:
            return ProtocolState.ASK_INTENT, context, prompts_he.GREETING_AND_INTENT_MENU
        return ProtocolState.ASK_INTENT, context, prompts_he.INTENT_NOT_UNDERSTOOD

    context.branch = intent

    if intent == Branch.NEW:
        return ProtocolState.ASK_FIRST_VISIT, context, prompts_he.ASK_FIRST_VISIT

    if intent == Branch.MESSAGE:
        return ProtocolState.COLLECT_MESSAGE, context, prompts_he.ASK_MESSAGE_BODY

    # Branch.EXISTING — find the patient's next active appointment
    patient = await api.find_patient_by_phone(patient_phone)
    if patient is None:
        # Reset to NEW flow since they have no record
        context.branch = Branch.NEW
        return ProtocolState.ASK_FIRST_VISIT, context, (
            prompts_he.NO_EXISTING_APPT + "\n\n" + prompts_he.ASK_FIRST_VISIT
        )

    appts = await api.get_patient_appointments(patient.id)
    now = datetime.now(UTC)
    active = [
        a for a in appts
        if a.status == AppointmentStatus.SCHEDULED
        and a.start_time.replace(tzinfo=a.start_time.tzinfo or UTC) > now
    ]
    if not active:
        context.branch = Branch.NEW
        return ProtocolState.ASK_FIRST_VISIT, context, (
            prompts_he.NO_EXISTING_APPT + "\n\n" + prompts_he.ASK_FIRST_VISIT
        )

    upcoming = sorted(active, key=lambda a: a.start_time)[0]
    context.existing_appt_id = upcoming.id

    summary = f"תאריך: {format_when(upcoming.start_time)}"
    reply = prompts_he.EXISTING_ACTION_MENU_TEMPLATE.format(summary=summary)
    return ProtocolState.ASK_EXISTING_ACTION, context, reply
