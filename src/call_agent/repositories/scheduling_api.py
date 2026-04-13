from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import httpx

from call_agent.domain.models import (
    Appointment,
    AppointmentType,
    BookRequest,
    Clinic,
    Doctor,
    Patient,
    TimeSlot,
)


class SchedulingAPIClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def get_clinic(self, clinic_id: UUID) -> Clinic:
        resp = await self._client.get(self._url(f"/clinics/{clinic_id}"))
        resp.raise_for_status()
        return Clinic.model_validate(resp.json())

    async def list_doctors(
        self, clinic_id: UUID | None = None, active_only: bool = True
    ) -> list[Doctor]:
        params: dict[str, str | bool] = {"active_only": active_only}
        if clinic_id is not None:
            params["clinic_id"] = str(clinic_id)
        resp = await self._client.get(
            self._url("/doctors/"),
            params=params,
        )
        resp.raise_for_status()
        return [Doctor.model_validate(d) for d in resp.json()]

    async def get_doctor(self, doctor_id: UUID) -> Doctor:
        resp = await self._client.get(self._url(f"/doctors/{doctor_id}"))
        resp.raise_for_status()
        return Doctor.model_validate(resp.json())

    async def get_doctor_operational_info(
        self, doctor_id: UUID
    ) -> dict[str, Any]:
        resp = await self._client.get(
            self._url(f"/doctors/{doctor_id}/operational-info")
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def find_patient_by_phone(self, phone: str) -> Patient | None:
        resp = await self._client.get(
            self._url("/patients/by-phone"), params={"phone": phone}
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return Patient.model_validate(resp.json())

    async def create_patient(
        self, first_name: str, last_name: str, phone: str
    ) -> Patient:
        resp = await self._client.post(
            self._url("/patients/"),
            json={"first_name": first_name, "last_name": last_name, "phone": phone},
        )
        resp.raise_for_status()
        return Patient.model_validate(resp.json())

    async def list_appointment_types(
        self, clinic_id: UUID | None = None, active_only: bool = True
    ) -> list[AppointmentType]:
        params: dict[str, str | bool] = {"active_only": active_only}
        if clinic_id is not None:
            params["clinic_id"] = str(clinic_id)
        resp = await self._client.get(
            self._url("/appointment-types/"),
            params=params,
        )
        resp.raise_for_status()
        return [AppointmentType.model_validate(at) for at in resp.json()]

    async def get_available_slots(
        self, doctor_id: UUID, slot_date: date, appointment_type_id: UUID
    ) -> list[TimeSlot]:
        resp = await self._client.get(
            self._url("/scheduling/slots"),
            params={
                "doctor_id": str(doctor_id),
                "date": slot_date.isoformat(),
                "appointment_type_id": str(appointment_type_id),
            },
        )
        resp.raise_for_status()
        return [TimeSlot.model_validate(s) for s in resp.json()]

    async def book_appointment(self, request: BookRequest) -> Appointment:
        resp = await self._client.post(
            self._url("/scheduling/appointments/book"),
            json=request.model_dump(mode="json"),
        )
        resp.raise_for_status()
        return Appointment.model_validate(resp.json())

    async def cancel_appointment(
        self, appointment_id: UUID, reason: str | None = None
    ) -> Appointment:
        body = {"reason": reason} if reason else None
        resp = await self._client.post(
            self._url(f"/scheduling/appointments/{appointment_id}/cancel"),
            json=body,
        )
        resp.raise_for_status()
        return Appointment.model_validate(resp.json())

    async def get_patient_appointments(
        self, patient_id: UUID
    ) -> list[Appointment]:
        resp = await self._client.get(
            self._url("/appointments/by-patient"),
            params={"patient_id": str(patient_id)},
        )
        resp.raise_for_status()
        return [Appointment.model_validate(a) for a in resp.json()]
