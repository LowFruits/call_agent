from __future__ import annotations

from pathlib import Path

import pytest

from call_agent.domain.enums import MessageRole
from call_agent.domain.models import Message
from call_agent.domain.protocol import Branch, ProtocolContext, ProtocolState
from call_agent.repositories.file_conversation import FileConversationRepository

PATIENT = "+972501234567"
ROUTE = "local"


@pytest.fixture
def repo(tmp_path: Path) -> FileConversationRepository:
    return FileConversationRepository(path=tmp_path / "conv.json")


@pytest.mark.asyncio
async def test_messages_round_trip(repo: FileConversationRepository) -> None:
    msgs = [Message(role=MessageRole.USER, content="hi")]
    await repo.save_messages(PATIENT, ROUTE, msgs)
    loaded = await repo.get_messages(PATIENT, ROUTE)
    assert loaded[0].content == "hi"


@pytest.mark.asyncio
async def test_default_protocol_state(repo: FileConversationRepository) -> None:
    state = await repo.get_protocol_state(PATIENT, ROUTE)
    assert state == ProtocolState.ASK_INTENT


@pytest.mark.asyncio
async def test_protocol_state_persistence(
    repo: FileConversationRepository, tmp_path: Path
) -> None:
    await repo.set_protocol_state(PATIENT, ROUTE, ProtocolState.ASK_BIRTH_DATE)
    # Reload from disk
    repo2 = FileConversationRepository(path=tmp_path / "conv.json")
    state = await repo2.get_protocol_state(PATIENT, ROUTE)
    assert state == ProtocolState.ASK_BIRTH_DATE


@pytest.mark.asyncio
async def test_protocol_context_round_trip(
    repo: FileConversationRepository,
) -> None:
    ctx = ProtocolContext(branch=Branch.MESSAGE, message_body="Need help")
    await repo.set_protocol_context(PATIENT, ROUTE, ctx)
    loaded = await repo.get_protocol_context(PATIENT, ROUTE)
    assert loaded.branch == Branch.MESSAGE
    assert loaded.message_body == "Need help"


@pytest.mark.asyncio
async def test_messages_and_protocol_coexist(
    repo: FileConversationRepository,
) -> None:
    await repo.save_messages(
        PATIENT, ROUTE, [Message(role=MessageRole.USER, content="a")]
    )
    await repo.set_protocol_state(PATIENT, ROUTE, ProtocolState.ASK_INTENT)
    await repo.set_protocol_context(PATIENT, ROUTE, ProtocolContext(branch=Branch.NEW))

    msgs = await repo.get_messages(PATIENT, ROUTE)
    state = await repo.get_protocol_state(PATIENT, ROUTE)
    ctx = await repo.get_protocol_context(PATIENT, ROUTE)
    assert msgs[0].content == "a"
    assert state == ProtocolState.ASK_INTENT
    assert ctx.branch == Branch.NEW


@pytest.mark.asyncio
async def test_clear_wipes_everything(repo: FileConversationRepository) -> None:
    await repo.save_messages(
        PATIENT, ROUTE, [Message(role=MessageRole.USER, content="a")]
    )
    await repo.set_protocol_state(PATIENT, ROUTE, ProtocolState.ASK_BIRTH_DATE)
    await repo.set_protocol_context(PATIENT, ROUTE, ProtocolContext(branch=Branch.NEW))

    await repo.clear(PATIENT, ROUTE)

    assert await repo.get_messages(PATIENT, ROUTE) == []
    assert await repo.get_protocol_state(PATIENT, ROUTE) == ProtocolState.ASK_INTENT
    assert await repo.get_protocol_context(PATIENT, ROUTE) == ProtocolContext()
