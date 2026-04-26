from __future__ import annotations

import fakeredis.aioredis
import pytest

from call_agent.domain.enums import MessageRole
from call_agent.domain.models import Message
from call_agent.domain.protocol import Branch, ProtocolContext, ProtocolState, VisitType
from call_agent.repositories.conversation import RedisConversationRepository


@pytest.fixture
def repo() -> RedisConversationRepository:
    redis = fakeredis.aioredis.FakeRedis()
    return RedisConversationRepository(redis=redis)


PATIENT = "whatsapp:+972501234567"
ROUTE = "whatsapp:+14155238886"


@pytest.mark.asyncio
async def test_empty_conversation(repo: RedisConversationRepository) -> None:
    messages = await repo.get_messages(PATIENT, ROUTE)
    assert messages == []


@pytest.mark.asyncio
async def test_save_and_load(repo: RedisConversationRepository) -> None:
    msgs = [
        Message(role=MessageRole.SYSTEM, content="You are a secretary."),
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi! How can I help?"),
    ]
    await repo.save_messages(PATIENT, ROUTE, msgs)
    loaded = await repo.get_messages(PATIENT, ROUTE)
    assert len(loaded) == 3
    assert loaded[0].role == MessageRole.SYSTEM
    assert loaded[1].content == "Hello"
    assert loaded[2].content == "Hi! How can I help?"


@pytest.mark.asyncio
async def test_overwrite_conversation(repo: RedisConversationRepository) -> None:
    msgs1 = [Message(role=MessageRole.USER, content="First")]
    await repo.save_messages(PATIENT, ROUTE, msgs1)

    msgs2 = [
        Message(role=MessageRole.USER, content="First"),
        Message(role=MessageRole.ASSISTANT, content="Reply"),
    ]
    await repo.save_messages(PATIENT, ROUTE, msgs2)

    loaded = await repo.get_messages(PATIENT, ROUTE)
    assert len(loaded) == 2


@pytest.mark.asyncio
async def test_clear(repo: RedisConversationRepository) -> None:
    msgs = [Message(role=MessageRole.USER, content="Hi")]
    await repo.save_messages(PATIENT, ROUTE, msgs)
    await repo.clear(PATIENT, ROUTE)
    assert await repo.get_messages(PATIENT, ROUTE) == []


@pytest.mark.asyncio
async def test_tool_message_round_trip(repo: RedisConversationRepository) -> None:
    msgs = [
        Message(
            role=MessageRole.ASSISTANT,
            tool_calls=[{"id": "call_1", "function": {"name": "test", "arguments": "{}"}}],
        ),
        Message(
            role=MessageRole.TOOL,
            content='{"result": "ok"}',
            tool_call_id="call_1",
            name="test",
        ),
    ]
    await repo.save_messages(PATIENT, ROUTE, msgs)
    loaded = await repo.get_messages(PATIENT, ROUTE)
    assert loaded[0].tool_calls is not None
    assert loaded[1].tool_call_id == "call_1"
    assert loaded[1].name == "test"


@pytest.mark.asyncio
async def test_separate_conversations(repo: RedisConversationRepository) -> None:
    other_route = "whatsapp:+15559999999"
    await repo.save_messages(PATIENT, ROUTE, [Message(role=MessageRole.USER, content="A")])
    await repo.save_messages(PATIENT, other_route, [Message(role=MessageRole.USER, content="B")])

    a = await repo.get_messages(PATIENT, ROUTE)
    b = await repo.get_messages(PATIENT, other_route)
    assert a[0].content == "A"
    assert b[0].content == "B"


# ---------------------------------------------------------------------------
# Protocol state + context persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_protocol_state(repo: RedisConversationRepository) -> None:
    state = await repo.get_protocol_state(PATIENT, ROUTE)
    assert state == ProtocolState.ASK_INTENT


@pytest.mark.asyncio
async def test_default_protocol_context(repo: RedisConversationRepository) -> None:
    ctx = await repo.get_protocol_context(PATIENT, ROUTE)
    assert ctx == ProtocolContext()


@pytest.mark.asyncio
async def test_set_and_get_protocol_state(repo: RedisConversationRepository) -> None:
    await repo.set_protocol_state(PATIENT, ROUTE, ProtocolState.ASK_KUPAT_CHOLIM)
    state = await repo.get_protocol_state(PATIENT, ROUTE)
    assert state == ProtocolState.ASK_KUPAT_CHOLIM


@pytest.mark.asyncio
async def test_set_and_get_protocol_context(repo: RedisConversationRepository) -> None:
    ctx = ProtocolContext(
        branch=Branch.NEW,
        first_visit=True,
        kupat_cholim="Clalit",
        visit_type=VisitType.IN_PERSON,
    )
    await repo.set_protocol_context(PATIENT, ROUTE, ctx)
    loaded = await repo.get_protocol_context(PATIENT, ROUTE)
    assert loaded.branch == Branch.NEW
    assert loaded.first_visit is True
    assert loaded.kupat_cholim == "Clalit"
    assert loaded.visit_type == VisitType.IN_PERSON


@pytest.mark.asyncio
async def test_clear_removes_protocol_data(
    repo: RedisConversationRepository,
) -> None:
    await repo.set_protocol_state(PATIENT, ROUTE, ProtocolState.ASK_BIRTH_DATE)
    await repo.set_protocol_context(PATIENT, ROUTE, ProtocolContext(branch=Branch.NEW))
    await repo.save_messages(PATIENT, ROUTE, [Message(role=MessageRole.USER, content="x")])

    await repo.clear(PATIENT, ROUTE)

    assert await repo.get_protocol_state(PATIENT, ROUTE) == ProtocolState.ASK_INTENT
    assert await repo.get_protocol_context(PATIENT, ROUTE) == ProtocolContext()
    assert await repo.get_messages(PATIENT, ROUTE) == []
