from uuid import uuid4

from call_agent.domain.models import Route
from call_agent.services.routing import RoutingService


def test_resolve_known_route() -> None:
    route = Route(phone_number="whatsapp:+14155238886", clinic_id=uuid4())
    service = RoutingService({"whatsapp:+14155238886": route})
    assert service.resolve("whatsapp:+14155238886") == route


def test_resolve_unknown_route() -> None:
    service = RoutingService({})
    assert service.resolve("whatsapp:+19999999999") is None
