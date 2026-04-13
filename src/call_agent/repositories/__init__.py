from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID

from call_agent.domain.models import (
    Appointment,
    AppointmentType,
    BookRequest,
    Clinic,
    Doctor,
    Message,
    Patient,
    TimeSlot,
)


class SchedulingAPIProtocol(Protocol):
    async def get_clinic(self, clinic_id: UUID) -> Clinic: ...

    async def list_doctors(
        self, clinic_id: UUID | None = None, active_only: bool = True
    ) -> list[Doctor]: ...

    async def get_doctor(self, doctor_id: UUID) -> Doctor: ...

    async def get_doctor_operational_info(
        self, doctor_id: UUID
    ) -> dict[str, Any]: ...

    async def find_patient_by_phone(self, phone: str) -> Patient | None: ...

    async def create_patient(
        self, first_name: str, last_name: str, phone: str
    ) -> Patient: ...

    async def list_appointment_types(
        self, clinic_id: UUID | None = None, active_only: bool = True
    ) -> list[AppointmentType]: ...

    async def get_available_slots(
        self, doctor_id: UUID, slot_date: date, appointment_type_id: UUID
    ) -> list[TimeSlot]: ...

    async def book_appointment(self, request: BookRequest) -> Appointment: ...

    async def cancel_appointment(
        self, appointment_id: UUID, reason: str | None = None
    ) -> Appointment: ...

    async def get_patient_appointments(
        self, patient_id: UUID
    ) -> list[Appointment]: ...


class ConversationRepositoryProtocol(Protocol):
    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]: ...

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None: ...

    async def clear(self, patient_phone: str, route_phone: str) -> None: ...
