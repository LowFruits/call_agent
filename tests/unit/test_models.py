from datetime import datetime
from uuid import uuid4

from call_agent.domain.enums import AppointmentStatus, BookedBy, MessageRole
from call_agent.domain.models import (
    Appointment,
    AppointmentType,
    BookRequest,
    CancelRequest,
    Clinic,
    Doctor,
    Message,
    Patient,
    Route,
    TimeSlot,
)
from call_agent.domain.schemas import TwilioWebhookPayload


class TestEnums:
    def test_appointment_status_values(self) -> None:
        assert AppointmentStatus.SCHEDULED == "scheduled"
        assert AppointmentStatus.CANCELLED == "cancelled"
        assert AppointmentStatus.COMPLETED == "completed"
        assert AppointmentStatus.NO_SHOW == "no_show"

    def test_booked_by_values(self) -> None:
        assert BookedBy.AGENT == "agent"
        assert BookedBy.STAFF == "staff"
        assert BookedBy.PATIENT == "patient"

    def test_message_role_values(self) -> None:
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"


class TestSchedulingModels:
    def test_clinic_round_trip(self) -> None:
        clinic = Clinic(
            id=uuid4(), name="Test Clinic", address="123 St", phone="050-1234567"
        )
        data = clinic.model_dump(mode="json")
        assert Clinic.model_validate(data) == clinic
        assert clinic.timezone == "Asia/Jerusalem"

    def test_doctor_round_trip(self) -> None:
        doctor = Doctor(
            id=uuid4(),
            clinic_id=uuid4(),
            first_name="Dan",
            last_name="Cohen",
            specialty="Dentist",
            email="dan@test.com",
        )
        data = doctor.model_dump(mode="json")
        assert Doctor.model_validate(data) == doctor
        assert doctor.is_active is True

    def test_patient_round_trip(self) -> None:
        patient = Patient(
            id=uuid4(), first_name="Yael", last_name="Levi", phone="052-9876543"
        )
        data = patient.model_dump(mode="json")
        assert Patient.model_validate(data) == patient

    def test_appointment_defaults(self) -> None:
        appt = Appointment(
            id=uuid4(),
            doctor_id=uuid4(),
            patient_id=uuid4(),
            appointment_type_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
            end_time=datetime(2026, 4, 1, 10, 30),
        )
        assert appt.status == AppointmentStatus.SCHEDULED
        assert appt.booked_by == BookedBy.AGENT

    def test_time_slot(self) -> None:
        slot = TimeSlot(
            start_time=datetime(2026, 4, 1, 9, 0),
            end_time=datetime(2026, 4, 1, 9, 30),
        )
        assert slot.end_time > slot.start_time

    def test_book_request(self) -> None:
        req = BookRequest(
            doctor_id=uuid4(),
            patient_id=uuid4(),
            appointment_type_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
        )
        assert req.booked_by == BookedBy.AGENT
        assert req.notes is None

    def test_cancel_request(self) -> None:
        assert CancelRequest().reason is None
        assert CancelRequest(reason="changed mind").reason == "changed mind"

    def test_appointment_type(self) -> None:
        at = AppointmentType(
            id=uuid4(), clinic_id=uuid4(), name="Checkup", duration_minutes=30
        )
        assert at.is_active is True


class TestInternalModels:
    def test_route_minimal(self) -> None:
        route = Route(phone_number="whatsapp:+14155238886", clinic_id=uuid4())
        assert route.doctor_id is None
        assert route.system_prompt_override is None

    def test_route_full(self) -> None:
        route = Route(
            phone_number="whatsapp:+14155238886",
            clinic_id=uuid4(),
            doctor_id=uuid4(),
            system_prompt_override="Custom prompt",
        )
        assert route.doctor_id is not None

    def test_message_user(self) -> None:
        msg = Message(role=MessageRole.USER, content="Hello")
        data = msg.model_dump(mode="json")
        assert Message.model_validate(data) == msg

    def test_message_tool(self) -> None:
        msg = Message(
            role=MessageRole.TOOL,
            content='{"result": "ok"}',
            tool_call_id="call_123",
            name="get_clinic_info",
        )
        assert msg.tool_call_id == "call_123"

    def test_message_assistant_with_tool_calls(self) -> None:
        msg = Message(
            role=MessageRole.ASSISTANT,
            tool_calls=[{"id": "call_1", "function": {"name": "test", "arguments": "{}"}}],
        )
        assert msg.content is None
        assert len(msg.tool_calls) == 1


class TestTwilioSchema:
    def test_payload_creation(self) -> None:
        payload = TwilioWebhookPayload(
            body="Hello",
            from_number="whatsapp:+972501234567",
            to_number="whatsapp:+14155238886",
            message_sid="SM123",
        )
        assert payload.body == "Hello"
        assert payload.from_number.startswith("whatsapp:")
