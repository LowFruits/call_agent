from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from call_agent.domain.enums import AppointmentStatus, BookedBy, MessageRole

# ---------------------------------------------------------------------------
# Scheduling API models
# ---------------------------------------------------------------------------

class Clinic(BaseModel):
    id: UUID
    name: str
    address: str
    phone: str
    timezone: str = "Asia/Jerusalem"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Doctor(BaseModel):
    id: UUID
    clinic_id: UUID
    first_name: str
    last_name: str
    specialty: str
    email: str
    phone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Patient(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone: str
    email: str | None = None
    date_of_birth: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AppointmentType(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    duration_minutes: int
    is_active: bool = True
    created_at: datetime | None = None


class Appointment(BaseModel):
    id: UUID
    doctor_id: UUID
    patient_id: UUID
    appointment_type_id: UUID
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    booked_by: BookedBy = BookedBy.AGENT
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    cancelled_at: datetime | None = None


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime


class BookRequest(BaseModel):
    doctor_id: UUID
    patient_id: UUID
    appointment_type_id: UUID
    start_time: datetime
    booked_by: BookedBy = BookedBy.AGENT
    notes: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


# ---------------------------------------------------------------------------
# Internal models
# ---------------------------------------------------------------------------

class Route(BaseModel):
    phone_number: str
    clinic_id: UUID
    doctor_id: UUID | None = None
    system_prompt_override: str | None = None


class Message(BaseModel):
    role: MessageRole
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = Field(default=None, description="Tool name for tool messages")
