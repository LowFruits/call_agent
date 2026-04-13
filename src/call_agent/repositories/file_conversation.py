from __future__ import annotations

import json
from pathlib import Path

from call_agent.domain.models import Message

_DEFAULT_PATH = Path("data/conversations.json")


class FileConversationRepository:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._store: dict[str, list[dict]] = {}  # type: ignore[type-arg]
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            self._store = json.loads(self._path.read_text(encoding="utf-8"))

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _key(patient_phone: str, route_phone: str) -> str:
        return f"conv:{patient_phone}:{route_phone}"

    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]:
        items = self._store.get(self._key(patient_phone, route_phone), [])
        return [Message.model_validate(m) for m in items]

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None:
        key = self._key(patient_phone, route_phone)
        self._store[key] = [
            m.model_dump(mode="json", exclude_none=True) for m in messages
        ]
        self._persist()

    async def clear(self, patient_phone: str, route_phone: str) -> None:
        key = self._key(patient_phone, route_phone)
        self._store.pop(key, None)
        self._persist()
