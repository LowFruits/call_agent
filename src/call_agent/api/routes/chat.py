from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from call_agent.api.deps import (
    get_conversation_repo,
    get_message_handler,
    get_scheduling_api,
)
from call_agent.domain.models import Route
from call_agent.repositories import ConversationRepositoryProtocol
from call_agent.repositories.scheduling_api import SchedulingAPIClient
from call_agent.services import MessageHandlerProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_PATIENT_PHONE = "+972501234567"

_HTML_PATH = Path(__file__).resolve().parent.parent / "static" / "chat.html"


def _route_phone_for(doctor_id: str) -> str:
    """Per-doctor scope so each doctor has its own conversation key."""
    return f"local:{doctor_id}"


class ChatRequest(BaseModel):
    doctor_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


class ResetRequest(BaseModel):
    doctor_id: str


class DoctorItem(BaseModel):
    id: str
    name: str
    specialty: str


@router.get("", response_class=HTMLResponse)
async def chat_page() -> HTMLResponse:
    html = _HTML_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@router.get("/doctors", response_model=list[DoctorItem])
async def list_doctors(
    api: SchedulingAPIClient = Depends(get_scheduling_api),
) -> list[DoctorItem]:
    doctors = await api.list_doctors()
    return [
        DoctorItem(
            id=str(d.id),
            name=f"{d.first_name} {d.last_name}",
            specialty=d.specialty,
        )
        for d in doctors
    ]


@router.post("/reset")
async def reset_conversation(
    req: ResetRequest,
    repo: ConversationRepositoryProtocol = Depends(get_conversation_repo),
) -> dict[str, str]:
    await repo.clear(_PATIENT_PHONE, _route_phone_for(req.doctor_id))
    return {"status": "ok"}


@router.post("/send", response_model=ChatResponse)
async def send_message(
    req: ChatRequest,
    handler: MessageHandlerProtocol = Depends(get_message_handler),
    api: SchedulingAPIClient = Depends(get_scheduling_api),
) -> ChatResponse:
    doctor = await api.get_doctor(UUID(req.doctor_id))
    route = Route(
        phone_number=_route_phone_for(req.doctor_id),
        clinic_id=doctor.clinic_id,
        doctor_id=doctor.id,
    )
    reply = await handler.handle_message(
        patient_phone=_PATIENT_PHONE,
        route=route,
        text=req.message,
    )
    return ChatResponse(reply=reply)
