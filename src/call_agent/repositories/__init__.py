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
from call_agent.domain.protocol import ProtocolContext, ProtocolState


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
        self, doctor_id: UUID, active_only: bool = True
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

    async def create_message(
        self,
        doctor_id: UUID,
        patient_phone: str,
        body: str,
        patient_name: str | None = None,
    ) -> dict[str, Any]: ...


class ConversationRepositoryProtocol(Protocol):
    async def get_messages(
        self, patient_phone: str, route_phone: str
    ) -> list[Message]: ...

    async def save_messages(
        self, patient_phone: str, route_phone: str, messages: list[Message]
    ) -> None: ...

    async def get_protocol_state(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolState: ...

    async def set_protocol_state(
        self, patient_phone: str, route_phone: str, state: ProtocolState
    ) -> None: ...

    async def get_protocol_context(
        self, patient_phone: str, route_phone: str
    ) -> ProtocolContext: ...

    async def set_protocol_context(
        self, patient_phone: str, route_phone: str, context: ProtocolContext
    ) -> None: ...

    async def clear(self, patient_phone: str, route_phone: str) -> None: ...
