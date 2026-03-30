from __future__ import annotations

import json

import redis.asyncio as aioredis

from call_agent.domain.models import Message

_TTL_SECONDS = 86400  # 24 hours


class RedisConversationRepository:
    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    @staticmethod
    def _key(patient_phone: str, route_phone: str) -> str:
        return f"conv:{patient_phone}:{route_phone}"

    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]:
        raw = await self._redis.get(self._key(patient_phone, route_phone))
        if raw is None:
            return []
        items = json.loads(raw)
        return [Message.model_validate(m) for m in items]

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None:
        key = self._key(patient_phone, route_phone)
        data = json.dumps(
            [m.model_dump(mode="json", exclude_none=True) for m in messages]
        )
        await self._redis.set(key, data, ex=_TTL_SECONDS)

    async def clear(self, patient_phone: str, route_phone: str) -> None:
        await self._redis.delete(self._key(patient_phone, route_phone))
