from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from call_agent.domain.enums import AppointmentStatus, BookedBy
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
from call_agent.services.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Validate tool definitions structure
# ---------------------------------------------------------------------------

CLINIC_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCTOR_ID = UUID("22222222-2222-2222-2222-222222222222")
PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
APPT_TYPE_ID = UUID("44444444-4444-4444-4444-444444444444")
APPT_ID = UUID("55555555-5555-5555-5555-555555555555")


class TestToolDefinitions:
    def test_all_tools_have_required_fields(self) -> None:
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_tool_count(self) -> None:
        assert len(TOOL_DEFINITIONS) == 11

    def test_registry_matches_definitions(self) -> None:
        defined_names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        registry_names = set(TOOL_REGISTRY.keys())
        assert defined_names == registry_names


# ---------------------------------------------------------------------------
# Fake scheduling API for testing executors
# ---------------------------------------------------------------------------

class FakeSchedulingAPI:
    async def get_clinic(self, clinic_id: UUID) -> Clinic:
        return Clinic(
            id=clinic_id, name="Test Clinic", address="123 St", phone="050-1234567"
        )

    async def list_doctors(
        self, clinic_id: UUID, active_only: bool = True
    ) -> list[Doctor]:
        return [
            Doctor(
                id=DOCTOR_ID, clinic_id=clinic_id, first_name="Dan",
                last_name="Cohen", specialty="Dentist", email="dan@test.com",
            )
        ]

    async def get_doctor(self, doctor_id: UUID) -> Doctor:
        return Doctor(
            id=doctor_id, clinic_id=CLINIC_ID, first_name="Dan",
            last_name="Cohen", specialty="Dentist", email="dan@test.com",
        )

    async def get_doctor_operational_info(
        self, doctor_id: UUID
    ) -> dict[str, Any]:
        return {"price": "200 NIS", "cancellation_policy": "24h notice"}

    async def find_patient_by_phone(self, phone: str) -> Patient | None:
        if phone == "052-9876543":
            return Patient(
                id=PATIENT_ID, first_name="Yael", last_name="Levi", phone=phone
            )
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
        return [
            AppointmentType(
                id=APPT_TYPE_ID, doctor_id=doctor_id, name="Checkup",
                duration_minutes=30,
            )
        ]

    async def get_available_slots(
        self, doctor_id: UUID, slot_date: date, appointment_type_id: UUID
    ) -> list[TimeSlot]:
        return [
            TimeSlot(
                start_time=datetime(2026, 4, 1, 9, 0),
                end_time=datetime(2026, 4, 1, 9, 30),
            )
        ]

    async def book_appointment(self, request: BookRequest) -> Appointment:
        return Appointment(
            id=APPT_ID, doctor_id=request.doctor_id, patient_id=request.patient_id,
            appointment_type_id=request.appointment_type_id,
            start_time=request.start_time,
            end_time=request.start_time,
            status=AppointmentStatus.SCHEDULED, booked_by=BookedBy.AGENT,
        )

    async def cancel_appointment(
        self, appointment_id: UUID, reason: str | None = None
    ) -> Appointment:
        return Appointment(
            id=appointment_id, doctor_id=DOCTOR_ID, patient_id=PATIENT_ID,
            appointment_type_id=APPT_TYPE_ID,
            start_time=datetime(2026, 4, 1, 10, 0),
            end_time=datetime(2026, 4, 1, 10, 30),
            status=AppointmentStatus.CANCELLED,
        )

    async def get_patient_appointments(
        self, patient_id: UUID
    ) -> list[Appointment]:
        return [
            Appointment(
                id=APPT_ID, doctor_id=DOCTOR_ID, patient_id=patient_id,
                appointment_type_id=APPT_TYPE_ID,
                start_time=datetime(2026, 4, 1, 10, 0),
                end_time=datetime(2026, 4, 1, 10, 30),
            )
        ]


# ---------------------------------------------------------------------------
# Test tool executors
# ---------------------------------------------------------------------------

@pytest.fixture
def api() -> FakeSchedulingAPI:
    return FakeSchedulingAPI()


@pytest.fixture
def route() -> Route:
    return Route(
        phone_number="whatsapp:+14155238886",
        clinic_id=CLINIC_ID,
        doctor_id=None,
    )


@pytest.mark.asyncio
async def test_get_clinic_info(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["get_clinic_info"](api, {}, route)
    )
    assert result["name"] == "Test Clinic"


@pytest.mark.asyncio
async def test_list_doctors(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["list_doctors"](api, {}, route)
    )
    assert len(result) == 1
    assert result[0]["first_name"] == "Dan"


@pytest.mark.asyncio
async def test_find_patient_found(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["find_patient"](api, {"phone": "052-9876543"}, route)
    )
    assert result["first_name"] == "Yael"


@pytest.mark.asyncio
async def test_find_patient_not_found(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["find_patient"](api, {"phone": "000-0000000"}, route)
    )
    assert result["found"] is False


@pytest.mark.asyncio
async def test_get_available_slots(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["get_available_slots"](api, {
            "doctor_id": str(DOCTOR_ID),
            "date": "2026-04-01",
            "appointment_type_id": str(APPT_TYPE_ID),
        }, route)
    )
    assert len(result) == 1


@pytest.mark.asyncio
async def test_book_appointment(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["book_appointment"](api, {
            "doctor_id": str(DOCTOR_ID),
            "patient_id": str(PATIENT_ID),
            "appointment_type_id": str(APPT_TYPE_ID),
            "start_time": "2026-04-01T10:00:00",
        }, route)
    )
    assert result["status"] == "scheduled"


@pytest.mark.asyncio
async def test_cancel_appointment(api: FakeSchedulingAPI, route: Route) -> None:
    result = json.loads(
        await TOOL_REGISTRY["cancel_appointment"](api, {
            "appointment_id": str(APPT_ID),
            "reason": "changed mind",
        }, route)
    )
    assert result["status"] == "cancelled"
