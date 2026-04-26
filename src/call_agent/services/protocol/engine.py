from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from call_agent.domain.models import Route
from call_agent.domain.protocol import ProtocolContext, ProtocolState
from call_agent.repositories import ConversationRepositoryProtocol, SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he

logger = logging.getLogger(__name__)


HandlerResult = tuple[ProtocolState, ProtocolContext, str]
HandlerFn = Callable[
    [ProtocolContext, str, str, Route, SchedulingAPIProtocol],
    Awaitable[HandlerResult],
]


class ProtocolEngine:
    def __init__(
        self,
        scheduling_api: SchedulingAPIProtocol,
        conversation_repo: ConversationRepositoryProtocol,
    ) -> None:
        self._api = scheduling_api
        self._repo = conversation_repo

    async def handle_message(
        self, patient_phone: str, route: Route, text: str
    ) -> str:
        state = await self._repo.get_protocol_state(
            patient_phone, route.phone_number
        )
        context = await self._repo.get_protocol_context(
            patient_phone, route.phone_number
        )

        next_state, next_ctx, reply = await self._dispatch(
            state, context, text, patient_phone, route
        )

        await self._repo.set_protocol_state(
            patient_phone, route.phone_number, next_state
        )
        await self._repo.set_protocol_context(
            patient_phone, route.phone_number, next_ctx
        )
        return reply

    async def _dispatch(
        self,
        state: ProtocolState,
        context: ProtocolContext,
        message: str,
        patient_phone: str,
        route: Route,
    ) -> HandlerResult:
        # DONE means the previous flow ended — start fresh with this message.
        if state == ProtocolState.DONE:
            state = ProtocolState.ASK_INTENT
            context = ProtocolContext()

        handler = _HANDLERS.get(state)
        if handler is None:
            logger.warning("No handler for state %s, returning STUCK", state)
            return (
                ProtocolState.STUCK,
                context,
                prompts_he.GENERIC_NOT_UNDERSTOOD,
            )

        return await handler(context, message, patient_phone, route, self._api)


# Late import to avoid circular dependencies — handlers import the engine module
# only for type names (already covered) and need to reference HANDLERS.
from call_agent.services.protocol.handlers import (  # noqa: E402
    existing,
    intent,
    new_booking,
    time_selection,
)
from call_agent.services.protocol.handlers import (  # noqa: E402
    message as message_handler,
)

_HANDLERS: dict[ProtocolState, HandlerFn] = {
    ProtocolState.ASK_INTENT: intent.handle_ask_intent,
    # New-booking branch
    ProtocolState.ASK_FIRST_VISIT: new_booking.handle_ask_first_visit,
    ProtocolState.ASK_KUPAT_CHOLIM: new_booking.handle_ask_kupat_cholim,
    ProtocolState.CONFIRM_PRIVATE: new_booking.handle_confirm_private,
    ProtocolState.ASK_BIRTH_DATE: new_booking.handle_ask_birth_date,
    ProtocolState.ASK_VISIT_TYPE: new_booking.handle_ask_visit_type,
    ProtocolState.ASK_FOR_SELF: new_booking.handle_ask_for_self,
    ProtocolState.ASK_OTHER_NAME: new_booking.handle_ask_other_name,
    ProtocolState.ASK_OTHER_ID: new_booking.handle_ask_other_id,
    ProtocolState.ASK_OTHER_RELATION: new_booking.handle_ask_other_relation,
    ProtocolState.ASK_PATIENT_ID: new_booking.handle_ask_patient_id,
    ProtocolState.ASK_NAME: new_booking.handle_ask_name,
    ProtocolState.ASK_SMS_CONSENT: new_booking.handle_ask_sms_consent,
    ProtocolState.SUMMARIZE_AND_CONFIRM: new_booking.handle_summarize_and_confirm,
    # Time-selection sub-FSM
    ProtocolState.TS_ASK_WINDOW: time_selection.handle_ask_window,
    ProtocolState.TS_ASK_WHEN: time_selection.handle_ask_when,
    ProtocolState.TS_ASK_SPECIFIC_DATE: time_selection.handle_ask_specific_date,
    ProtocolState.TS_OFFER_SLOT: time_selection.handle_offer_slot,
    # Existing-appointment branch
    ProtocolState.ASK_EXISTING_ACTION: existing.handle_ask_existing_action,
    ProtocolState.MORE_INFO: existing.handle_more_info,
    ProtocolState.RESCHEDULE_OFFER_SLOT: existing.handle_reschedule_offer_slot,
    ProtocolState.RESCHEDULE_CHANGE_MENU: existing.handle_reschedule_change_menu,
    ProtocolState.SUMMARIZE_RESCHEDULE: existing.handle_summarize_reschedule,
    ProtocolState.CONFIRM_CANCEL: existing.handle_confirm_cancel,
    # Leave-message branch
    ProtocolState.COLLECT_MESSAGE: message_handler.handle_collect_message,
}
