from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from call_agent.api.routes.webhook import router
from call_agent.domain.models import Route
from call_agent.services.routing import RoutingService

CLINIC_ID = uuid4()
ROUTE_PHONE = "whatsapp:+14155238886"
PATIENT_PHONE = "whatsapp:+972501234567"


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)

    route = Route(phone_number=ROUTE_PHONE, clinic_id=CLINIC_ID)
    routing_service = RoutingService({ROUTE_PHONE: route})

    agent_service = AsyncMock()
    agent_service.handle_message = AsyncMock(return_value="שלום! איך אוכל לעזור?")

    test_app.state.agent_service = agent_service
    test_app.state.routing_service = routing_service
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_twilio_webhook_success(client: TestClient, app: FastAPI) -> None:
    response = client.post(
        "/webhook/twilio",
        data={
            "Body": "שלום",
            "From": PATIENT_PHONE,
            "To": ROUTE_PHONE,
            "MessageSid": "SM123",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert "<Message>שלום! איך אוכל לעזור?</Message>" in response.text
    assert "<Response>" in response.text


def test_twilio_webhook_unknown_route(client: TestClient) -> None:
    response = client.post(
        "/webhook/twilio",
        data={
            "Body": "Hello",
            "From": PATIENT_PHONE,
            "To": "whatsapp:+19999999999",
            "MessageSid": "SM456",
        },
    )
    assert response.status_code == 200
    assert "אינו מוגדר" in response.text
