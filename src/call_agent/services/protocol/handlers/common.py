from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from call_agent.domain.protocol import TimeWindow

_TZ = ZoneInfo("Asia/Jerusalem")

# Hebrew kupot list — single source of truth for the menu and matching.
KUPOT_CHOLIM = ["כללית", "מכבי", "מאוחדת", "לאומית", "פרטי"]


def slot_in_window(slot_start: datetime, window: TimeWindow) -> bool:
    """Return True if the slot's local hour is in the chosen window.

    Morning window is 00:00–13:59; afternoon is 14:00 onward.
    """
    local = slot_start.astimezone(_TZ) if slot_start.tzinfo else slot_start
    hour = local.hour
    if window == TimeWindow.MORNING:
        return hour < 14
    return hour >= 14


def format_when(slot_start: datetime) -> str:
    """Human-readable Hebrew date+time for a slot.

    Builds the string in Python rather than via strftime — Windows' strftime
    can't encode non-ASCII format characters under some locales.
    """
    local = slot_start.astimezone(_TZ) if slot_start.tzinfo else slot_start
    return f"{local.strftime('%d/%m/%Y')} בשעה {local.strftime('%H:%M')}"
