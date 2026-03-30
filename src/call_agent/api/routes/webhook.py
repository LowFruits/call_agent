from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from call_agent.api.deps import get_agent_service, get_routing_service
from call_agent.domain.schemas import TwilioWebhookPayload
from call_agent.services.agent import AgentService
from call_agent.services.routing import RoutingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _twiml_message(text: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{text}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/twilio")
async def twilio_webhook(
    payload: TwilioWebhookPayload = Depends(TwilioWebhookPayload.from_form),
    agent: AgentService = Depends(get_agent_service),
    routing: RoutingService = Depends(get_routing_service),
) -> Response:
    route = routing.resolve(payload.to_number)
    if route is None:
        logger.warning("No route for %s", payload.to_number)
        return _twiml_message("מצטערים, מספר זה אינו מוגדר במערכת.")

    reply = await agent.handle_message(
        patient_phone=payload.from_number,
        route=route,
        text=payload.body,
    )
    return _twiml_message(reply)
