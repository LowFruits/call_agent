from __future__ import annotations

import json

import redis.asyncio as aioredis

from call_agent.domain.models import Message
from call_agent.domain.protocol import ProtocolContext, ProtocolState

_TTL_SECONDS = 86400  # 24 hours


class RedisConversationRepository:
    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    @staticmethod
    def _msg_key(patient_phone: str, route_phone: str) -> str:
        return f"conv:{patient_phone}:{route_phone}"

    @staticmethod
    def _state_key(patient_phone: str, route_phone: str) -> str:
        return f"state:{patient_phone}:{route_phone}"

    @staticmethod
    def _ctx_key(patient_phone: str, route_phone: str) -> str:
        return f"ctx:{patient_phone}:{route_phone}"

    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]:
        raw = await self._redis.get(self._msg_key(patient_phone, route_phone))
        if raw is None:
            return []
        items = json.loads(raw)
        return [Message.model_validate(m) for m in items]

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None:
        key = self._msg_key(patient_phone, route_phone)
        data = json.dumps(
            [m.model_dump(mode="json", exclude_none=True) for m in messages]
        )
        await self._redis.set(key, data, ex=_TTL_SECONDS)

    async def get_protocol_state(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolState:
        raw = await self._redis.get(self._state_key(patient_phone, route_phone))
        if raw is None:
            return ProtocolState.ASK_INTENT
        value = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return ProtocolState(value)

    async def set_protocol_state(
        self, patient_phone: str, route_phone: str, state: ProtocolState
    ) -> None:
        await self._redis.set(
            self._state_key(patient_phone, route_phone),
            state.value,
            ex=_TTL_SECONDS,
        )

    async def get_protocol_context(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolContext:
        raw = await self._redis.get(self._ctx_key(patient_phone, route_phone))
        if raw is None:
            return ProtocolContext()
        return ProtocolContext.model_validate_json(raw)

    async def set_protocol_context(
        self, patient_phone: str, route_phone: str, context: ProtocolContext
    ) -> None:
        await self._redis.set(
            self._ctx_key(patient_phone, route_phone),
            context.model_dump_json(exclude_none=True),
            ex=_TTL_SECONDS,
        )

    async def clear(self, patient_phone: str, route_phone: str) -> None:
        await self._redis.delete(
            self._msg_key(patient_phone, route_phone),
            self._state_key(patient_phone, route_phone),
            self._ctx_key(patient_phone, route_phone),
        )
