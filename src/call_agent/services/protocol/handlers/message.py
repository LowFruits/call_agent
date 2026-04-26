from __future__ import annotations

from call_agent.domain.models import Route
from call_agent.domain.protocol import ProtocolContext, ProtocolState
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he


async def handle_collect_message(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    body = message.strip()
    if not body:
        return ProtocolState.COLLECT_MESSAGE, context, prompts_he.ASK_MESSAGE_BODY
    context.message_body = body
    if route.doctor_id is not None:
        await api.create_message(
            doctor_id=route.doctor_id,
            patient_phone=patient_phone,
            body=body,
            patient_name=context.patient_name,
        )
    return ProtocolState.DONE, context, prompts_he.MESSAGE_SAVED
