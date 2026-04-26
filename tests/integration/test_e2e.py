from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from call_agent.api.routes.webhook import router
from call_agent.domain.models import (
    Appointment,
    AppointmentType,
    BookRequest,
    Clinic,
    Doctor,
    Patient,
    Route,
    TimeSlot,
)
from call_agent.repositories.conversation import RedisConversationRepository
from call_agent.services.agent import AgentService
from call_agent.services.routing import RoutingService

CLINIC_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCTOR_ID = UUID("22222222-2222-2222-2222-222222222222")
ROUTE_PHONE = "whatsapp:+14155238886"
PATIENT_PHONE = "whatsapp:+972501234567"


class FakeSchedulingAPI:
    async def get_clinic(self, clinic_id: UUID) -> Clinic:
        return Clinic(
            id=clinic_id, name="מרפאת בדיקה", address="רחוב 123",
            phone="050-1234567",
        )

    async def list_doctors(
        self, clinic_id: UUID, active_only: bool = True
    ) -> list[Doctor]:
        return []

    async def get_doctor(self, doctor_id: UUID) -> Doctor:
        return Doctor(
            id=doctor_id, clinic_id=CLINIC_ID, first_name="דן",
            last_name="כהן", specialty="רפואת שיניים", email="dan@test.com",
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


def _make_openai_response(content: str) -> Any:
    message = MagicMock()
    message.content = content
    message.tool_calls = None

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)

    route = Route(
        phone_number=ROUTE_PHONE, clinic_id=CLINIC_ID, doctor_id=DOCTOR_ID
    )
    routing_service = RoutingService({ROUTE_PHONE: route})

    fake_redis = fakeredis.aioredis.FakeRedis()
    conversation_repo = RedisConversationRepository(redis=fake_redis)

    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("שלום! אני המזכירה הדיגיטלית. איך אוכל לעזור?")
    )

    agent_service = AgentService(
        openai_client=mock_openai,
        scheduling_api=FakeSchedulingAPI(),
        conversation_repo=conversation_repo,
    )

    test_app.state.message_handler = agent_service
    test_app.state.routing_service = routing_service
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_e2e_first_message(client: TestClient) -> None:
    response = client.post(
        "/webhook/twilio",
        data={
            "Body": "שלום",
            "From": PATIENT_PHONE,
            "To": ROUTE_PHONE,
            "MessageSid": "SM789",
        },
    )
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text
    assert "<Message>" in response.text
    assert "שלום" in response.text


def test_e2e_multi_turn(client: TestClient) -> None:
    # First message
    client.post(
        "/webhook/twilio",
        data={
            "Body": "שלום",
            "From": PATIENT_PHONE,
            "To": ROUTE_PHONE,
            "MessageSid": "SM001",
        },
    )

    # Second message — conversation should continue
    response = client.post(
        "/webhook/twilio",
        data={
            "Body": "אני רוצה לקבוע תור",
            "From": PATIENT_PHONE,
            "To": ROUTE_PHONE,
            "MessageSid": "SM002",
        },
    )
    assert response.status_code == 200
    assert "<Message>" in response.text
