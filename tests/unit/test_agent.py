from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from call_agent.domain.models import (
    Appointment,
    AppointmentType,
    BookRequest,
    Clinic,
    Doctor,
    Message,
    Patient,
    Route,
    TimeSlot,
)
from call_agent.services.agent import AgentService

CLINIC_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCTOR_ID = UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class FakeConversationRepo:
    def __init__(self) -> None:
        self._store: dict[str, list[Message]] = {}

    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]:
        return list(self._store.get(f"{patient_phone}:{route_phone}", []))

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None:
        self._store[f"{patient_phone}:{route_phone}"] = list(messages)

    async def clear(self, patient_phone: str, route_phone: str) -> None:
        self._store.pop(f"{patient_phone}:{route_phone}", None)


class FakeSchedulingAPI:
    async def get_clinic(self, clinic_id: UUID) -> Clinic:
        return Clinic(
            id=clinic_id, name="Test Clinic", address="123 St", phone="050-1234567"
        )

    async def list_doctors(
        self, clinic_id: UUID, active_only: bool = True
    ) -> list[Doctor]:
        return []

    async def get_doctor(self, doctor_id: UUID) -> Doctor:
        return Doctor(
            id=doctor_id, clinic_id=CLINIC_ID, first_name="Dan",
            last_name="Cohen", specialty="Dentist", email="dan@test.com",
        )

    async def get_doctor_operational_info(
        self, doctor_id: UUID
    ) -> dict[str, Any]:
        return {}

    async def find_patient_by_phone(self, phone: str) -> Patient | None:
        return None

    async def create_patient(
        self, first_name: str, last_name: str, phone: str
    ) -> Patient:
        return Patient(
            id=uuid4(), first_name=first_name, last_name=last_name, phone=phone
        )

    async def list_appointment_types(
        self, doctor_id: UUID, active_only: bool = True
    ) -> list[AppointmentType]:
        return []

    async def get_available_slots(
        self, doctor_id: UUID, slot_date: date, appointment_type_id: UUID
    ) -> list[TimeSlot]:
        return []

    async def book_appointment(self, request: BookRequest) -> Appointment:
        raise NotImplementedError

    async def cancel_appointment(
        self, appointment_id: UUID, reason: str | None = None
    ) -> Appointment:
        raise NotImplementedError

    async def get_patient_appointments(
        self, patient_id: UUID
    ) -> list[Appointment]:
        return []


def _make_openai_response(content: str | None = None, tool_calls: Any = None) -> Any:
    """Create a mock OpenAI chat completion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(call_id: str, name: str, arguments: str) -> Any:
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = arguments
    tc.model_dump.return_value = {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }
    return tc


@pytest.fixture
def route() -> Route:
    return Route(
        phone_number="whatsapp:+14155238886",
        clinic_id=CLINIC_ID,
        doctor_id=DOCTOR_ID,
    )


@pytest.fixture
def agent() -> AgentService:
    openai_client = AsyncMock()
    return AgentService(
        openai_client=openai_client,
        scheduling_api=FakeSchedulingAPI(),
        conversation_repo=FakeConversationRepo(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simple_text_response(agent: AgentService, route: Route) -> None:
    agent._openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(content="שלום! איך אוכל לעזור?")
    )
    reply = await agent.handle_message("whatsapp:+972501234567", route, "שלום")
    assert reply == "שלום! איך אוכל לעזור?"


@pytest.mark.asyncio
async def test_system_prompt_on_first_message(
    agent: AgentService, route: Route
) -> None:
    agent._openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(content="Hello")
    )
    await agent.handle_message("whatsapp:+972501234567", route, "Hi")

    # Verify the OpenAI call included a system message
    call_args = agent._openai.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "Test Clinic" in messages[0]["content"]
    assert "Dan" in messages[0]["content"]


@pytest.mark.asyncio
async def test_tool_call_loop(agent: AgentService, route: Route) -> None:
    tool_call = _make_tool_call(
        "call_1", "get_clinic_info", f'{{"clinic_id": "{CLINIC_ID}"}}'
    )

    # First call: model requests a tool
    # Second call: model gives text response
    agent._openai.chat.completions.create = AsyncMock(
        side_effect=[
            _make_openai_response(tool_calls=[tool_call]),
            _make_openai_response(content="The clinic is Test Clinic at 123 St."),
        ]
    )

    reply = await agent.handle_message("whatsapp:+972501234567", route, "Where is the clinic?")
    assert "Test Clinic" in reply
    assert agent._openai.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_conversation_persists(agent: AgentService, route: Route) -> None:
    agent._openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(content="First reply")
    )
    await agent.handle_message("whatsapp:+972501234567", route, "First message")

    agent._openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(content="Second reply")
    )
    reply = await agent.handle_message("whatsapp:+972501234567", route, "Second message")
    assert reply == "Second reply"

    # Second call should include history from first call
    call_args = agent._openai.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    # system + user1 + assistant1 + user2
    assert len(messages) == 4


@pytest.mark.asyncio
async def test_fallback_reply_when_no_content(
    agent: AgentService, route: Route
) -> None:
    # Simulate max iterations exhausted (all tool calls, never text)
    tool_call = _make_tool_call(
        "call_1", "get_clinic_info", f'{{"clinic_id": "{CLINIC_ID}"}}'
    )
    agent._openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(tool_calls=[tool_call])
    )

    reply = await agent.handle_message("whatsapp:+972501234567", route, "Hi")
    assert "מצטער" in reply
