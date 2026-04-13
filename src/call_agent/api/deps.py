from __future__ import annotations

from fastapi import Request

from call_agent.repositories.scheduling_api import SchedulingAPIClient
from call_agent.services.agent import AgentService
from call_agent.services.routing import RoutingService


def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service  # type: ignore[no-any-return]


def get_routing_service(request: Request) -> RoutingService:
    return request.app.state.routing_service  # type: ignore[no-any-return]


def get_scheduling_api(request: Request) -> SchedulingAPIClient:
    return request.app.state.scheduling_api  # type: ignore[no-any-return]
