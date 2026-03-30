from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from call_agent.domain.models import BookRequest
from call_agent.repositories.scheduling_api import SchedulingAPIClient

BASE_URL = "https://api.test"

CLINIC_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCTOR_ID = UUID("22222222-2222-2222-2222-222222222222")
PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
APPT_TYPE_ID = UUID("44444444-4444-4444-4444-444444444444")
APPT_ID = UUID("55555555-5555-5555-5555-555555555555")

CLINIC_JSON = {
    "id": str(CLINIC_ID),
    "name": "Test Clinic",
    "address": "123 St",
    "phone": "050-1234567",
    "timezone": "Asia/Jerusalem",
}

DOCTOR_JSON = {
    "id": str(DOCTOR_ID),
    "clinic_id": str(CLINIC_ID),
    "first_name": "Dan",
    "last_name": "Cohen",
    "specialty": "Dentist",
    "email": "dan@test.com",
    "is_active": True,
}

PATIENT_JSON = {
    "id": str(PATIENT_ID),
    "first_name": "Yael",
    "last_name": "Levi",
    "phone": "052-9876543",
}

APPT_TYPE_JSON = {
    "id": str(APPT_TYPE_ID),
    "clinic_id": str(CLINIC_ID),
    "name": "Checkup",
    "duration_minutes": 30,
    "is_active": True,
}

APPOINTMENT_JSON = {
    "id": str(APPT_ID),
    "doctor_id": str(DOCTOR_ID),
    "patient_id": str(PATIENT_ID),
    "appointment_type_id": str(APPT_TYPE_ID),
    "start_time": "2026-04-01T10:00:00",
    "end_time": "2026-04-01T10:30:00",
    "status": "scheduled",
    "booked_by": "agent",
}

SLOT_JSON = {
    "start_time": "2026-04-01T09:00:00",
    "end_time": "2026-04-01T09:30:00",
}


def _mock_transport(handler):  # type: ignore[no-untyped-def]
    return httpx.MockTransport(handler)


def _make_client(handler):  # type: ignore[no-untyped-def]
    transport = _mock_transport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return SchedulingAPIClient(base_url=BASE_URL, client=http_client)


@pytest.mark.asyncio
async def test_get_clinic() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{BASE_URL}/clinics/{CLINIC_ID}"
        return httpx.Response(200, json=CLINIC_JSON)

    client = _make_client(handler)
    clinic = await client.get_clinic(CLINIC_ID)
    assert clinic.id == CLINIC_ID
    assert clinic.name == "Test Clinic"


@pytest.mark.asyncio
async def test_list_doctors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "clinic_id" in str(request.url)
        return httpx.Response(200, json=[DOCTOR_JSON])

    client = _make_client(handler)
    doctors = await client.list_doctors(CLINIC_ID)
    assert len(doctors) == 1
    assert doctors[0].first_name == "Dan"


@pytest.mark.asyncio
async def test_get_doctor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=DOCTOR_JSON)

    client = _make_client(handler)
    doctor = await client.get_doctor(DOCTOR_ID)
    assert doctor.specialty == "Dentist"


@pytest.mark.asyncio
async def test_get_doctor_operational_info() -> None:
    info = {"price": "200 NIS", "cancellation_policy": "24h notice"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "operational-info" in str(request.url)
        return httpx.Response(200, json=info)

    client = _make_client(handler)
    result = await client.get_doctor_operational_info(DOCTOR_ID)
    assert result["price"] == "200 NIS"


@pytest.mark.asyncio
async def test_find_patient_by_phone_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "phone=" in str(request.url)
        return httpx.Response(200, json=PATIENT_JSON)

    client = _make_client(handler)
    patient = await client.find_patient_by_phone("052-9876543")
    assert patient is not None
    assert patient.last_name == "Levi"


@pytest.mark.asyncio
async def test_find_patient_by_phone_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Not found"})

    client = _make_client(handler)
    patient = await client.find_patient_by_phone("000-0000000")
    assert patient is None


@pytest.mark.asyncio
async def test_create_patient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["first_name"] == "Yael"
        return httpx.Response(201, json=PATIENT_JSON)

    client = _make_client(handler)
    patient = await client.create_patient("Yael", "Levi", "052-9876543")
    assert patient.id == PATIENT_ID


@pytest.mark.asyncio
async def test_list_appointment_types() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[APPT_TYPE_JSON])

    client = _make_client(handler)
    types = await client.list_appointment_types(CLINIC_ID)
    assert len(types) == 1
    assert types[0].duration_minutes == 30


@pytest.mark.asyncio
async def test_get_available_slots() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[SLOT_JSON])

    client = _make_client(handler)
    slots = await client.get_available_slots(
        DOCTOR_ID, date(2026, 4, 1), APPT_TYPE_ID
    )
    assert len(slots) == 1
    assert slots[0].start_time == datetime(2026, 4, 1, 9, 0)


@pytest.mark.asyncio
async def test_book_appointment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["doctor_id"] == str(DOCTOR_ID)
        return httpx.Response(201, json=APPOINTMENT_JSON)

    client = _make_client(handler)
    req = BookRequest(
        doctor_id=DOCTOR_ID,
        patient_id=PATIENT_ID,
        appointment_type_id=APPT_TYPE_ID,
        start_time=datetime(2026, 4, 1, 10, 0),
    )
    appt = await client.book_appointment(req)
    assert appt.id == APPT_ID


@pytest.mark.asyncio
async def test_cancel_appointment() -> None:
    cancelled = {**APPOINTMENT_JSON, "status": "cancelled"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "cancel" in str(request.url)
        return httpx.Response(200, json=cancelled)

    client = _make_client(handler)
    appt = await client.cancel_appointment(APPT_ID, reason="changed mind")
    assert appt.status == "cancelled"


@pytest.mark.asyncio
async def test_get_patient_appointments() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "patient_id" in str(request.url)
        return httpx.Response(200, json=[APPOINTMENT_JSON])

    client = _make_client(handler)
    appts = await client.get_patient_appointments(PATIENT_ID)
    assert len(appts) == 1


@pytest.mark.asyncio
async def test_http_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Internal error"})

    client = _make_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_clinic(uuid4())
