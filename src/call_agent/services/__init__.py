from __future__ import annotations

from typing import Protocol

from call_agent.domain.models import Route


class MessageHandlerProtocol(Protocol):
    async def handle_message(
        self, patient_phone: str, route: Route, text: str
    ) -> str: ...


__all__ = ["MessageHandlerProtocol"]
