from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from call_agent.domain.models import Message
from call_agent.domain.protocol import ProtocolContext, ProtocolState

_DEFAULT_PATH = Path("data/conversations.json")


class FileConversationRepository:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        # Per scope_key entry: {"messages": [...], "state": "...", "context": {...}}
        self._store: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            # Migrate legacy format (key -> list of message dicts)
            self._store = {
                k: (v if isinstance(v, dict) else {"messages": v})
                for k, v in raw.items()
            }

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _key(patient_phone: str, route_phone: str) -> str:
        return f"conv:{patient_phone}:{route_phone}"

    def _entry(self, key: str) -> dict[str, Any]:
        return self._store.setdefault(key, {})

    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]:
        entry = self._store.get(self._key(patient_phone, route_phone), {})
        items = entry.get("messages", [])
        return [Message.model_validate(m) for m in items]

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None:
        entry = self._entry(self._key(patient_phone, route_phone))
        entry["messages"] = [
            m.model_dump(mode="json", exclude_none=True) for m in messages
        ]
        self._persist()

    async def get_protocol_state(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolState:
        entry = self._store.get(self._key(patient_phone, route_phone), {})
        value = entry.get("state")
        if value is None:
            return ProtocolState.ASK_INTENT
        return ProtocolState(value)

    async def set_protocol_state(
        self, patient_phone: str, route_phone: str, state: ProtocolState
    ) -> None:
        entry = self._entry(self._key(patient_phone, route_phone))
        entry["state"] = state.value
        self._persist()

    async def get_protocol_context(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolContext:
        entry = self._store.get(self._key(patient_phone, route_phone), {})
        data = entry.get("context")
        if data is None:
            return ProtocolContext()
        return ProtocolContext.model_validate(data)

    async def set_protocol_context(
        self, patient_phone: str, route_phone: str, context: ProtocolContext
    ) -> None:
        entry = self._entry(self._key(patient_phone, route_phone))
        entry["context"] = context.model_dump(mode="json", exclude_none=True)
        self._persist()

    async def clear(self, patient_phone: str, route_phone: str) -> None:
        key = self._key(patient_phone, route_phone)
        self._store.pop(key, None)
        self._persist()
