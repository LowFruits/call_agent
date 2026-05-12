from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx

from call_agent.domain.models import (
    AppointmentType,
    Route,
    TimeSlot,
)
from call_agent.domain.protocol import (
    Branch,
    ProtocolContext,
    ProtocolState,
    TimeWindow,
    WhenMode,
)
from call_agent.repositories import SchedulingAPIProtocol
from call_agent.services.protocol import prompts_he
from call_agent.services.protocol.handlers.common import (
    format_slot_line,
    format_when,
    format_working_days,
    is_date_blocked,
    slot_window,
    working_weekdays,
)
from call_agent.services.protocol.validators import (
    parse_date,
    parse_int_choice,
    parse_when_mode,
    parse_yes_no,
)

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Jerusalem")
_LOOKAHEAD_DAYS_MAX = 180  # 6-month safety ceiling
_SLOTS_PER_WINDOW = 3
_SPREAD_SLOTS_PER_DATE = 3


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------

async def handle_ask_mode(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    mode = parse_when_mode(message)
    if mode is None:
        return ProtocolState.TS_ASK_MODE, context, prompts_he.ASK_TIME_MODE

    context.when_mode = mode
    if mode == WhenMode.CLOSEST:
        return await _collect_and_offer_closest(context, route, api)

    # SPECIFIC_DATE — show working days then ask for the date.
    if route.doctor_id is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD
    avail = await api.get_doctor_availability(route.doctor_id)
    days = format_working_days(avail.rules)
    return (
        ProtocolState.TS_ASK_SPECIFIC_DATE,
        context,
        prompts_he.WORKING_DAYS_TEMPLATE.format(days=days),
    )


# ---------------------------------------------------------------------------
# Specific-date entry
# ---------------------------------------------------------------------------

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

    if route.doctor_id is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    avail = await api.get_doctor_availability(route.doctor_id)
    working = working_weekdays(avail.rules)
    if parsed.weekday() not in working or is_date_blocked(parsed, avail.exceptions):
        return (
            ProtocolState.TS_ASK_SPECIFIC_DATE,
            context,
            prompts_he.DATE_NOT_WORKING_DAY,
        )

    context.specific_date = parsed
    return await _collect_and_offer_date(context, route, api)


# ---------------------------------------------------------------------------
# Offer handlers
# ---------------------------------------------------------------------------

async def handle_offer_closest(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    # 1) Try numeric pick first (so "2" reads as slot 2, not yes/no "no").
    max_choice = max(context.offered_slots) if context.offered_slots else 0
    choice = parse_int_choice(message, max_choice) if max_choice else None
    if choice is not None and choice in context.offered_slots:
        _commit_pick(context, choice)
        return _next_after_slot_chosen(context)

    # 2) Word-based decline → next batch.
    if _is_decline_word(message) or parse_yes_no(message) is False:
        for start in context.offered_slots.values():
            if start not in context.declined_slot_starts:
                context.declined_slot_starts.append(start)
        context.offered_slots = {}
        context.offered_slots_end = {}
        return await _collect_and_offer_closest(context, route, api)

    # 3) Unrecognised — re-render the current menu.
    return ProtocolState.TS_OFFER_CLOSEST, context, _format_closest_menu(context)


async def handle_offer_date_slots(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    max_choice = max(context.offered_slots) if context.offered_slots else 0
    choice = parse_int_choice(message, max_choice) if max_choice else None
    if choice is not None and choice in context.offered_slots:
        _commit_pick(context, choice)
        return _next_after_slot_chosen(context)

    if _is_decline_word(message) or parse_yes_no(message) is False:
        for start in context.offered_slots.values():
            if start not in context.declined_slot_starts:
                context.declined_slot_starts.append(start)
        context.offered_slots = {}
        context.offered_slots_end = {}
        return await _collect_and_offer_date(context, route, api)

    return ProtocolState.TS_OFFER_DATE_SLOTS, context, _format_date_menu(context)


# ---------------------------------------------------------------------------
# 6-month fallback
# ---------------------------------------------------------------------------

async def handle_no_slots_offer_message(
    context: ProtocolContext,
    message: str,
    patient_phone: str,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    answer = parse_yes_no(message)
    if answer is None:
        return (
            ProtocolState.NO_SLOTS_OFFER_MESSAGE,
            context,
            prompts_he.NO_SLOTS_HALF_YEAR_OFFER_MESSAGE,
        )
    if answer is False:
        return ProtocolState.DONE, context, prompts_he.GENERIC_GOODBYE
    # Yes — switch branches into leave-message.
    context.branch = Branch.MESSAGE
    return ProtocolState.COLLECT_MESSAGE, context, prompts_he.ASK_MESSAGE_BODY


# ---------------------------------------------------------------------------
# Internals — gathering offers
# ---------------------------------------------------------------------------

async def _collect_and_offer_closest(
    context: ProtocolContext,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    appt_type = await _resolve_appt_type(context, route, api)
    if appt_type is None or route.doctor_id is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    try:
        avail = await api.get_doctor_availability(route.doctor_id)
    except httpx.HTTPStatusError:
        logger.exception("availability fetch failed")
        return ProtocolState.TS_ASK_MODE, context, (
            prompts_he.BOOKING_SLOT_GONE + "\n\n" + prompts_he.ASK_TIME_MODE
        )

    working = working_weekdays(avail.rules)
    today = datetime.now(_TZ).date()
    buckets: dict[TimeWindow, list[TimeSlot]] = {
        TimeWindow.MORNING: [],
        TimeWindow.NOON: [],
        TimeWindow.EVENING: [],
    }

    try:
        for offset in range(_LOOKAHEAD_DAYS_MAX):
            d = today + timedelta(days=offset)
            if working and d.weekday() not in working:
                continue
            if is_date_blocked(d, avail.exceptions):
                continue
            slots = await api.get_available_slots(
                doctor_id=route.doctor_id,
                slot_date=d,
                appointment_type_id=appt_type.id,
            )
            for s in slots:
                if s.start_time in context.declined_slot_starts:
                    continue
                w = slot_window(s.start_time)
                if len(buckets[w]) < _SLOTS_PER_WINDOW:
                    buckets[w].append(s)
            if all(len(b) == _SLOTS_PER_WINDOW for b in buckets.values()):
                break
    except httpx.HTTPStatusError:
        logger.exception("slots fetch failed (likely doctor/type mismatch)")
        return ProtocolState.TS_ASK_MODE, context, (
            prompts_he.BOOKING_SLOT_GONE + "\n\n" + prompts_he.ASK_TIME_MODE
        )

    _populate_offers(context, buckets, appt_type.id)

    if not context.offered_slots:
        return (
            ProtocolState.NO_SLOTS_OFFER_MESSAGE,
            context,
            prompts_he.NO_SLOTS_HALF_YEAR_OFFER_MESSAGE,
        )

    return ProtocolState.TS_OFFER_CLOSEST, context, _format_closest_menu(context)


async def _collect_and_offer_date(
    context: ProtocolContext,
    route: Route,
    api: SchedulingAPIProtocol,
) -> tuple[ProtocolState, ProtocolContext, str]:
    appt_type = await _resolve_appt_type(context, route, api)
    if appt_type is None or route.doctor_id is None or context.specific_date is None:
        return ProtocolState.STUCK, context, prompts_he.GENERIC_NOT_UNDERSTOOD

    try:
        slots = await api.get_available_slots(
            doctor_id=route.doctor_id,
            slot_date=context.specific_date,
            appointment_type_id=appt_type.id,
        )
    except httpx.HTTPStatusError:
        logger.exception("slots fetch failed for specific date")
        return ProtocolState.TS_ASK_MODE, context, (
            prompts_he.BOOKING_SLOT_GONE + "\n\n" + prompts_he.ASK_TIME_MODE
        )

    available = [s for s in slots if s.start_time not in context.declined_slot_starts]
    if not available:
        return (
            ProtocolState.TS_ASK_SPECIFIC_DATE,
            context,
            prompts_he.NO_MORE_DATE_SLOTS,
        )

    spread = _spread_pick(available, _SPREAD_SLOTS_PER_DATE)
    context.offered_slots = {i + 1: s.start_time for i, s in enumerate(spread)}
    context.offered_slots_end = {i + 1: s.end_time for i, s in enumerate(spread)}
    context.offered_appt_type_id = appt_type.id

    return ProtocolState.TS_OFFER_DATE_SLOTS, context, _format_date_menu(context)


async def _resolve_appt_type(
    context: ProtocolContext,
    route: Route,
    api: SchedulingAPIProtocol,
) -> AppointmentType | None:
    if route.doctor_id is None:
        return None
    appt_types = await api.list_appointment_types(route.doctor_id)
    target_name = "ביקור ראשון" if context.first_visit else "ביקור חוזר"
    return next(
        (t for t in appt_types if target_name in t.name),
        appt_types[0] if appt_types else None,
    )


def _populate_offers(
    context: ProtocolContext,
    buckets: dict[TimeWindow, list[TimeSlot]],
    appt_type_id: UUID,
) -> None:
    n = 1
    starts: dict[int, datetime] = {}
    ends: dict[int, datetime] = {}
    for window in (TimeWindow.MORNING, TimeWindow.NOON, TimeWindow.EVENING):
        for slot in buckets[window]:
            starts[n] = slot.start_time
            ends[n] = slot.end_time
            n += 1
    context.offered_slots = starts
    context.offered_slots_end = ends
    context.offered_appt_type_id = appt_type_id


def _spread_pick(slots: list[TimeSlot], count: int) -> list[TimeSlot]:
    """Pick up to `count` slots spread evenly across the input list."""
    n = len(slots)
    if n <= count:
        return list(slots)
    indices = sorted({round(i * (n - 1) / (count - 1)) for i in range(count)})
    return [slots[i] for i in indices]


def _format_closest_menu(context: ProtocolContext) -> str:
    """Render the numbered closest-slot menu, grouped by window header."""
    lines: list[str] = []
    by_window: dict[TimeWindow, list[tuple[int, datetime]]] = {
        TimeWindow.MORNING: [],
        TimeWindow.NOON: [],
        TimeWindow.EVENING: [],
    }
    for n, start in sorted(context.offered_slots.items()):
        by_window[slot_window(start)].append((n, start))

    labels = {
        TimeWindow.MORNING: prompts_he.WINDOW_LABEL_MORNING,
        TimeWindow.NOON: prompts_he.WINDOW_LABEL_NOON,
        TimeWindow.EVENING: prompts_he.WINDOW_LABEL_EVENING,
    }
    for window in (TimeWindow.MORNING, TimeWindow.NOON, TimeWindow.EVENING):
        items = by_window[window]
        if not items:
            continue
        lines.append(f"{labels[window]}:")
        for n, start in items:
            lines.append(format_slot_line(n, start))
        lines.append("")

    listing = "\n".join(lines).rstrip()
    return prompts_he.OFFER_CLOSEST_TEMPLATE.format(listing=listing)


def _format_date_menu(context: ProtocolContext) -> str:
    date_str = (
        context.specific_date.strftime("%d/%m/%Y")
        if context.specific_date else ""
    )
    listing = "\n".join(
        format_slot_line(n, start)
        for n, start in sorted(context.offered_slots.items())
    )
    return prompts_he.OFFER_DATE_SLOTS_TEMPLATE.format(
        date_str=date_str, listing=listing
    )


def _commit_pick(context: ProtocolContext, choice: int) -> None:
    # Keep offered_slots populated so that "back" to TS_OFFER_* can re-render
    # the menu without re-querying the API. The map is overwritten next batch.
    context.offered_slot_start = context.offered_slots[choice]
    context.offered_slot_end = context.offered_slots_end[choice]


def _next_after_slot_chosen(
    context: ProtocolContext,
) -> tuple[ProtocolState, ProtocolContext, str]:
    if context.branch == Branch.EXISTING:
        when = (
            format_when(context.offered_slot_start)
            if context.offered_slot_start else ""
        )
        reply = prompts_he.RESCHEDULE_OFFER_MENU_TEMPLATE.format(when=when)
        return ProtocolState.RESCHEDULE_OFFER_SLOT, context, reply
    # NEW branch
    return ProtocolState.ASK_FOR_SELF, context, prompts_he.ASK_FOR_SELF


def _is_decline_word(message: str) -> bool:
    """Reserved 'show me more' tokens, distinct from numeric picks."""
    s = message.strip().lower()
    return s in {"לא", "no", "n", "עוד", "אחר", "more"}


__all__ = [
    "handle_ask_mode",
    "handle_ask_specific_date",
    "handle_no_slots_offer_message",
    "handle_offer_closest",
    "handle_offer_date_slots",
]
