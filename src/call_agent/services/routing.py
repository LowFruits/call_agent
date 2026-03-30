from __future__ import annotations

from call_agent.domain.models import Route


class RoutingService:
    def __init__(self, routes: dict[str, Route]) -> None:
        self._routes = routes

    def resolve(self, phone_number: str) -> Route | None:
        return self._routes.get(phone_number)
