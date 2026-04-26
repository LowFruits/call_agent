from __future__ import annotations

from fastapi import Request

from call_agent.repositories import ConversationRepositoryProtocol
from call_agent.repositories.scheduling_api import SchedulingAPIClient
from call_agent.services import MessageHandlerProtocol
from call_agent.services.routing import RoutingService


def get_message_handler(request: Request) -> MessageHandlerProtocol:
    return request.app.state.message_handler  # type: ignore[no-any-return]


def get_routing_service(request: Request) -> RoutingService:
    return request.app.state.routing_service  # type: ignore[no-any-return]


def get_scheduling_api(request: Request) -> SchedulingAPIClient:
    return request.app.state.scheduling_api  # type: ignore[no-any-return]


def get_conversation_repo(request: Request) -> ConversationRepositoryProtocol:
    return request.app.state.conversation_repo  # type: ignore[no-any-return]
