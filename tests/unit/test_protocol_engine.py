from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import fakeredis.aioredis
import httpx
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
from call_agent.domain.protocol import ProtocolState
from call_agent.repositories.conversation import RedisConversationRepository
from call_agent.services.protocol.engine import ProtocolEngine

CLINIC_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCTOR_ID = UUID("22222222-2222-2222-2222-222222222222")
PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
APPT_TYPE_FIRST = UUID("44444444-4444-4444-4444-444444444444")
APPT_TYPE_FOLLOWUP = UUID("55555555-5555-5555-5555-555555555555")
EXISTING_APPT_ID = UUID("66666666-6666-6666-6666-666666666666")

PATIENT_PHONE = "+972501234567"
ROUTE_PHONE = "whatsapp:+14155238886"


class FakeAPI:
    def __init__(self) -> None:
        self.booked: list[BookRequest] = []
        self.cancelled: list[UUID] = []
        self.messages_created: list[dict[str, Any]] = []
        self.patient_exists = True
        self.has_existing_appt = False
        self.raise_on_slots = False

    async def get_clinic(self, clinic_id: UUID) -> Clinic:
        return Clinic(id=clinic_id, name="Test", address="x", phone="0")

    async def list_doctors(
        self, clinic_id: UUID | None = None, active_only: bool = True
    ) -> list[Doctor]:
        return []

    async def get_doctor(self, doctor_id: UUID) -> Doctor:
        return Doctor(
            id=doctor_id, clinic_id=CLINIC_ID, first_name="A", last_name="B",
            specialty="x", email="a@b.c",
        )

    async def get_doctor_operational_info(
        self, doctor_id: UUID
    ) -> dict[str, Any]:
        return {}

    async def find_patient_by_phone(self, phone: str) -> Patient | None:
        if not self.patient_exists:
            return None
        return Patient(
            id=PATIENT_ID, first_name="Yossi", last_name="Cohen", phone=phone
        )

    async def create_patient(
        self, first_name: str, last_name: str, phone: str
    ) -> Patient:
        return Patient(
            id=PATIENT_ID, first_name=first_name, last_name=last_name, phone=phone
        )

    async def list_appointment_types(
        self, doctor_id: UUID, active_only: bool = True
    ) -> list[AppointmentType]:
        return [
            AppointmentType(
                id=APPT_TYPE_FIRST, doctor_id=doctor_id,
                name="ביקור ראשון", duration_minutes=30,
            ),
            AppointmentType(
                id=APPT_TYPE_FOLLOWUP, doctor_id=doctor_id,
                name="ביקור חוזר", duration_minutes=15,
            ),
        ]

    async def get_available_slots(
        self, doctor_id: UUID, slot_date: date, appointment_type_id: UUID
    ) -> list[TimeSlot]:
        if self.raise_on_slots:
            request = httpx.Request("GET", "https://example/test")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError(
                "doctor/type mismatch", request=request, response=response
            )
        # Always return one morning slot
        start = datetime.combine(slot_date, datetime.min.time()).replace(
            hour=10, tzinfo=UTC
        )
        return [TimeSlot(start_time=start, end_time=start + timedelta(minutes=30))]

    async def book_appointment(self, request: BookRequest) -> Appointment:
        self.booked.append(request)
        return Appointment(
            id=uuid4(),
            doctor_id=request.doctor_id,
            patient_id=request.patient_id,
            appointment_type_id=request.appointment_type_id,
            start_time=request.start_time,
            end_time=request.start_time + timedelta(minutes=30),
            status=AppointmentStatus.SCHEDULED,
            booked_by=BookedBy.AGENT,
        )

    async def cancel_appointment(
        self, appointment_id: UUID, reason: str | None = None
    ) -> Appointment:
        self.cancelled.append(appointment_id)
        return Appointment(
            id=appointment_id, doctor_id=DOCTOR_ID, patient_id=PATIENT_ID,
            appointment_type_id=APPT_TYPE_FIRST,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            status=AppointmentStatus.CANCELLED, booked_by=BookedBy.AGENT,
        )

    async def get_patient_appointments(
        self, patient_id: UUID
    ) -> list[Appointment]:
        if not self.has_existing_appt:
            return []
        future = datetime.now(UTC) + timedelta(days=2)
        return [
            Appointment(
                id=EXISTING_APPT_ID, doctor_id=DOCTOR_ID, patient_id=patient_id,
                appointment_type_id=APPT_TYPE_FIRST,
                start_time=future,
                end_time=future + timedelta(minutes=30),
                status=AppointmentStatus.SCHEDULED, booked_by=BookedBy.AGENT,
            )
        ]

    async def create_message(
        self,
        doctor_id: UUID,
        patient_phone: str,
        body: str,
        patient_name: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "doctor_id": doctor_id,
            "patient_phone": patient_phone,
            "body": body,
            "patient_name": patient_name,
        }
        self.messages_created.append(record)
        return record


@pytest.fixture
def route() -> Route:
    return Route(phone_number=ROUTE_PHONE, clinic_id=CLINIC_ID, doctor_id=DOCTOR_ID)


@pytest.fixture
def fake_api() -> FakeAPI:
    return FakeAPI()


@pytest.fixture
def repo() -> RedisConversationRepository:
    return RedisConversationRepository(redis=fakeredis.aioredis.FakeRedis())


@pytest.fixture
def engine(
    fake_api: FakeAPI, repo: RedisConversationRepository
) -> ProtocolEngine:
    return ProtocolEngine(scheduling_api=fake_api, conversation_repo=repo)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Opening
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_message_shows_intent_menu(
    engine: ProtocolEngine, route: Route
) -> None:
    reply = await engine.handle_message(PATIENT_PHONE, route, "שלום")
    assert "1" in reply and "2" in reply and "3" in reply


@pytest.mark.asyncio
async def test_unrecognised_intent_reprompts(
    engine: ProtocolEngine, route: Route
) -> None:
    await engine.handle_message(PATIENT_PHONE, route, "hello")
    reply = await engine.handle_message(PATIENT_PHONE, route, "blah blah")
    assert "1" in reply and "2" in reply


# ---------------------------------------------------------------------------
# New booking happy path (for self)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_booking_for_self_happy_path(
    engine: ProtocolEngine,
    route: Route,
    fake_api: FakeAPI,
    repo: RedisConversationRepository,
) -> None:
    # 1. Intent: new appointment
    await engine.handle_message(PATIENT_PHONE, route, "2")
    # 2. First visit: yes
    await engine.handle_message(PATIENT_PHONE, route, "כן")
    # 3. Kupat cholim: Clalit
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # 4. Birth date
    await engine.handle_message(PATIENT_PHONE, route, "01/01/1990")
    # 5. Visit type: phone
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # 6. Time window: morning
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # 7. When: soonest (offers a slot)
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # 8. Confirm slot: yes
    await engine.handle_message(PATIENT_PHONE, route, "כן")
    # 9. For self: yes
    await engine.handle_message(PATIENT_PHONE, route, "כן")
    # 10. Patient ID (valid)
    await engine.handle_message(PATIENT_PHONE, route, "123456782")
    # 11. SMS consent: no
    await engine.handle_message(PATIENT_PHONE, route, "לא")
    # 12. Confirm summary: yes
    final = await engine.handle_message(PATIENT_PHONE, route, "כן")

    assert "התור נקבע" in final
    assert len(fake_api.booked) == 1
    booked = fake_api.booked[0]
    assert booked.appointment_type_id == APPT_TYPE_FIRST  # first visit
    state = await repo.get_protocol_state(PATIENT_PHONE, ROUTE_PHONE)
    assert state == ProtocolState.DONE


# ---------------------------------------------------------------------------
# Private path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_private_kupah_triggers_confirm(
    engine: ProtocolEngine, route: Route
) -> None:
    await engine.handle_message(PATIENT_PHONE, route, "2")  # new
    await engine.handle_message(PATIENT_PHONE, route, "כן")  # first visit
    reply = await engine.handle_message(PATIENT_PHONE, route, "5")  # private
    assert "פרטי" in reply or "עלות" in reply


# ---------------------------------------------------------------------------
# Invalid ID re-prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_id_reprompts(
    engine: ProtocolEngine, route: Route
) -> None:
    # Walk to ASK_PATIENT_ID
    msgs = ["2", "כן", "1", "01/01/1990", "1", "1", "1", "כן", "כן"]
    for m in msgs:
        await engine.handle_message(PATIENT_PHONE, route, m)
    # Now at ASK_PATIENT_ID — send bad ID
    reply = await engine.handle_message(PATIENT_PHONE, route, "111111111")
    assert "תקינה" in reply or "תקין" in reply


# ---------------------------------------------------------------------------
# Leave-message branch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leave_message_persists(
    engine: ProtocolEngine,
    route: Route,
    fake_api: FakeAPI,
) -> None:
    await engine.handle_message(PATIENT_PHONE, route, "3")  # leave message
    final = await engine.handle_message(PATIENT_PHONE, route, "צריך לדבר עם הרופא")

    assert len(fake_api.messages_created) == 1
    msg = fake_api.messages_created[0]
    assert msg["body"] == "צריך לדבר עם הרופא"
    assert msg["doctor_id"] == DOCTOR_ID
    assert "נשמרה" in final or "תודה" in final


# ---------------------------------------------------------------------------
# Existing appointment — cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_existing(
    engine: ProtocolEngine,
    route: Route,
    fake_api: FakeAPI,
) -> None:
    fake_api.has_existing_appt = True
    # Intent: existing
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # Action: cancel (3)
    await engine.handle_message(PATIENT_PHONE, route, "3")
    # Confirm: yes
    final = await engine.handle_message(PATIENT_PHONE, route, "כן")

    assert EXISTING_APPT_ID in fake_api.cancelled
    assert "בוטל" in final


@pytest.mark.asyncio
async def test_existing_no_appt_falls_back_to_new(
    engine: ProtocolEngine, route: Route, fake_api: FakeAPI
) -> None:
    fake_api.has_existing_appt = False
    reply = await engine.handle_message(PATIENT_PHONE, route, "1")
    # Should mention no existing + transition to first-visit question
    assert "ראשון" in reply  # first-visit prompt is now asked


# ---------------------------------------------------------------------------
# Reschedule with "change something else"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reschedule_change_visit_type_loops(
    engine: ProtocolEngine, route: Route, fake_api: FakeAPI
) -> None:
    fake_api.has_existing_appt = True
    # Intent: existing
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # Action: reschedule (2)
    await engine.handle_message(PATIENT_PHONE, route, "2")
    # Time-selection: window=morning, when=soonest
    await engine.handle_message(PATIENT_PHONE, route, "1")
    await engine.handle_message(PATIENT_PHONE, route, "1")
    # Now at TS_OFFER_SLOT — confirm
    await engine.handle_message(PATIENT_PHONE, route, "כן")
    # Now at RESCHEDULE_OFFER_SLOT 3-way — pick "change something else" (3)
    reply = await engine.handle_message(PATIENT_PHONE, route, "3")
    # Should be at change menu
    assert "שנה" in reply or "סוג ביקור" in reply

    # Pick visit type (1) → re-asks visit type → re-enters TS
    reply = await engine.handle_message(PATIENT_PHONE, route, "1")
    assert "טלפ" in reply or "פרונטלי" in reply


# ---------------------------------------------------------------------------
# Restart after DONE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_after_done_restarts(
    engine: ProtocolEngine,
    route: Route,
    fake_api: FakeAPI,
) -> None:
    # Cancel flow ends in DONE
    fake_api.has_existing_appt = True
    await engine.handle_message(PATIENT_PHONE, route, "1")
    await engine.handle_message(PATIENT_PHONE, route, "3")
    await engine.handle_message(PATIENT_PHONE, route, "כן")
    # Now state should be DONE — next message restarts
    reply = await engine.handle_message(PATIENT_PHONE, route, "שלום")
    assert "1" in reply and "2" in reply and "3" in reply


# ---------------------------------------------------------------------------
# Mismatch handling — slot fetch fails (e.g. doctor/type mismatch 4xx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slot_mismatch_handled_gracefully(
    engine: ProtocolEngine,
    route: Route,
    fake_api: FakeAPI,
) -> None:
    fake_api.raise_on_slots = True

    # Walk to the time-selection sub-FSM
    await engine.handle_message(PATIENT_PHONE, route, "2")  # new
    await engine.handle_message(PATIENT_PHONE, route, "כן")  # first visit
    await engine.handle_message(PATIENT_PHONE, route, "1")  # kupah
    await engine.handle_message(PATIENT_PHONE, route, "01/01/1990")  # birth
    await engine.handle_message(PATIENT_PHONE, route, "1")  # visit type
    await engine.handle_message(PATIENT_PHONE, route, "1")  # window=morning
    # When=soonest triggers slot fetch → raises → graceful fallback
    reply = await engine.handle_message(PATIENT_PHONE, route, "1")

    assert "אינו זמין" in reply or "ננסה" in reply  # slot-gone message
    assert "בוקר" in reply  # window prompt re-shown
