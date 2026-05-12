from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Literal

from call_agent.domain.models import Route
from call_agent.domain.protocol import HistoryEntry, ProtocolContext, ProtocolState
from call_agent.repositories import ConversationRepositoryProtocol, SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he

logger = logging.getLogger(__name__)


HandlerResult = tuple[ProtocolState, ProtocolContext, str]
HandlerFn = Callable[
    [ProtocolContext, str, str, Route, SchedulingAPIProtocol],
    Awaitable[HandlerResult],
]

# Navigation hint appended to every prompt that's awaiting a user response.
_NAV_HINT = "(99 = חזור, 0 = התחל מחדש)"

# Tokens that mean "back" / "restart" regardless of the current state.
_BACK_TOKENS = {"99", "חזור", "אחורה", "back"}
_RESTART_TOKENS = {"0", "התחל מחדש", "התחלה", "restart"}

# States where the hint is suppressed (terminals + the very first greeting).
_NO_HINT_STATES = {
    ProtocolState.ASK_INTENT,
    ProtocolState.DONE,
    ProtocolState.STUCK,
}


def _parse_nav(text: str) -> Literal["back", "restart"] | None:
    s = text.strip().lower()
    if s in _BACK_TOKENS:
        return "back"
    if s in _RESTART_TOKENS:
        return "restart"
    return None


def _with_hint(state: ProtocolState, reply: str) -> str:
    if state in _NO_HINT_STATES:
        return reply
    return f"{reply}\n\n{_NAV_HINT}"


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

        nav = _parse_nav(text)
        if nav == "restart":
            next_state = ProtocolState.ASK_INTENT
            next_ctx = ProtocolContext()
            reply = prompts_he.GREETING_AND_INTENT_MENU
        elif nav == "back":
            if context.state_history:
                entry = context.state_history.pop()
                next_state = entry.state
                next_ctx = context
                reply = entry.prompt
            else:
                # Nothing to go back to — re-show the current prompt.
                next_state = state
                next_ctx = context
                reply = context.last_prompt or prompts_he.GREETING_AND_INTENT_MENU
        else:
            next_state, next_ctx, reply = await self._dispatch(
                state, context, text, patient_phone, route
            )
            # Record the state we *left* (with the prompt that was shown there)
            # so '99' can return the user to it. Re-prompts (same state) and
            # transitions away from STUCK don't get pushed.
            if (
                next_state != state
                and state != ProtocolState.STUCK
                and next_ctx.last_prompt is not None
            ):
                next_ctx.state_history.append(
                    HistoryEntry(state=state, prompt=next_ctx.last_prompt)
                )

        # Stamp last_prompt with the raw reply (no nav hint) so back-replay is
        # idempotent — the hint is re-applied on the next turn.
        next_ctx.last_prompt = reply

        await self._repo.set_protocol_state(
            patient_phone, route.phone_number, next_state
        )
        await self._repo.set_protocol_context(
            patient_phone, route.phone_number, next_ctx
        )
        return _with_hint(next_state, reply)

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
    # Time-selection sub-FSM (mode → closest|specific → numbered offers)
    ProtocolState.TS_ASK_MODE: time_selection.handle_ask_mode,
    ProtocolState.TS_OFFER_CLOSEST: time_selection.handle_offer_closest,
    ProtocolState.TS_ASK_SPECIFIC_DATE: time_selection.handle_ask_specific_date,
    ProtocolState.TS_OFFER_DATE_SLOTS: time_selection.handle_offer_date_slots,
    ProtocolState.NO_SLOTS_OFFER_MESSAGE: time_selection.handle_no_slots_offer_message,
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
