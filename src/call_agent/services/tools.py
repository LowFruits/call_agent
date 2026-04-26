from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from call_agent.domain.models import Route
from call_agent.repositories import SchedulingAPIProtocol

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_clinic_info",
            "description": "Get information about the clinic (name, address, phone, timezone).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_doctors",
            "description": "List all active doctors at the clinic.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_info",
            "description": "Get detailed information about a specific doctor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The doctor UUID"},
                },
                "required": ["doctor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_operational_info",
            "description": (
                "Get operational information for a doctor: pricing, cancellation policy, "
                "accepted insurance, and other policies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The doctor UUID"},
                },
                "required": ["doctor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_patient",
            "description": "Find a patient by their phone number. Returns null if not found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "Patient phone number",
                    },
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_patient",
            "description": (
                "Create a new patient record. "
                "Use after confirming the patient is not already registered."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Patient first name"},
                    "last_name": {"type": "string", "description": "Patient last name"},
                    "phone": {"type": "string", "description": "Patient phone number"},
                },
                "required": ["first_name", "last_name", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_appointment_types",
            "description": (
                "List available appointment types for a specific doctor "
                "(e.g. checkup, consultation). Each doctor has their own catalog."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The doctor UUID"},
                },
                "required": ["doctor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": (
                "Get available time slots for a doctor on a specific date "
                "for a given appointment type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The doctor UUID"},
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                    "appointment_type_id": {
                        "type": "string",
                        "description": "The appointment type UUID",
                    },
                },
                "required": ["doctor_id", "date", "appointment_type_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book an appointment. Requires doctor, patient, appointment type, and start time. "
                "Always confirm the details with the patient before booking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The doctor UUID"},
                    "patient_id": {"type": "string", "description": "The patient UUID"},
                    "appointment_type_id": {
                        "type": "string",
                        "description": "The appointment type UUID",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Appointment start time in ISO 8601 format",
                    },
                },
                "required": ["doctor_id", "patient_id", "appointment_type_id", "start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment. Optionally provide a reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment UUID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional cancellation reason",
                    },
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_appointments",
            "description": "List all appointments for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient UUID",
                    },
                },
                "required": ["patient_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executors
# ---------------------------------------------------------------------------

async def _execute_get_clinic_info(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    clinic = await api.get_clinic(route.clinic_id)
    return clinic.model_dump_json()


async def _execute_list_doctors(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    doctors = await api.list_doctors(route.clinic_id)
    return json.dumps([d.model_dump(mode="json") for d in doctors])


async def _execute_get_doctor_info(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    doctor = await api.get_doctor(UUID(args["doctor_id"]))
    return doctor.model_dump_json()


async def _execute_get_doctor_operational_info(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    info = await api.get_doctor_operational_info(UUID(args["doctor_id"]))
    return json.dumps(info)


async def _execute_find_patient(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    patient = await api.find_patient_by_phone(args["phone"])
    if patient is None:
        return json.dumps({"found": False})
    return patient.model_dump_json()


async def _execute_create_patient(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    patient = await api.create_patient(
        first_name=args["first_name"],
        last_name=args["last_name"],
        phone=args["phone"],
    )
    return patient.model_dump_json()


async def _execute_list_appointment_types(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    types = await api.list_appointment_types(UUID(args["doctor_id"]))
    return json.dumps([t.model_dump(mode="json") for t in types])


async def _execute_get_available_slots(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    slots = await api.get_available_slots(
        doctor_id=UUID(args["doctor_id"]),
        slot_date=date.fromisoformat(args["date"]),
        appointment_type_id=UUID(args["appointment_type_id"]),
    )
    return json.dumps([s.model_dump(mode="json") for s in slots])


async def _execute_book_appointment(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    from call_agent.domain.models import BookRequest

    req = BookRequest(
        doctor_id=UUID(args["doctor_id"]),
        patient_id=UUID(args["patient_id"]),
        appointment_type_id=UUID(args["appointment_type_id"]),
        start_time=args["start_time"],
    )
    appt = await api.book_appointment(req)
    return appt.model_dump_json()


async def _execute_cancel_appointment(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    appt = await api.cancel_appointment(
        appointment_id=UUID(args["appointment_id"]),
        reason=args.get("reason"),
    )
    return appt.model_dump_json()


async def _execute_get_patient_appointments(
    api: SchedulingAPIProtocol, args: dict[str, Any], route: Route
) -> str:
    appts = await api.get_patient_appointments(UUID(args["patient_id"]))
    return json.dumps([a.model_dump(mode="json") for a in appts])


ToolExecutor = Any  # Callable[[SchedulingAPIProtocol, dict[str, Any]], Awaitable[str]]

TOOL_REGISTRY: dict[str, ToolExecutor] = {
    "get_clinic_info": _execute_get_clinic_info,
    "list_doctors": _execute_list_doctors,
    "get_doctor_info": _execute_get_doctor_info,
    "get_doctor_operational_info": _execute_get_doctor_operational_info,
    "find_patient": _execute_find_patient,
    "create_patient": _execute_create_patient,
    "list_appointment_types": _execute_list_appointment_types,
    "get_available_slots": _execute_get_available_slots,
    "book_appointment": _execute_book_appointment,
    "cancel_appointment": _execute_cancel_appointment,
    "get_patient_appointments": _execute_get_patient_appointments,
}
