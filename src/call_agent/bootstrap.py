from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
import openai
import redis.asyncio as aioredis

from call_agent.config import Settings
from call_agent.domain.models import Route
from call_agent.repositories.conversation import RedisConversationRepository
from call_agent.repositories.scheduling_api import SchedulingAPIClient
from call_agent.services.agent import AgentService
from call_agent.services.routing import RoutingService


@dataclass
class Container:
    agent_service: AgentService
    routing_service: RoutingService
    httpx_client: httpx.AsyncClient
    redis_client: aioredis.Redis  # type: ignore[type-arg]


async def bootstrap(settings: Settings | None = None) -> Container:
    if settings is None:
        settings = Settings()

    httpx_client = httpx.AsyncClient(timeout=30.0)
    redis_client: aioredis.Redis[bytes] = aioredis.from_url(
        settings.redis_url
    )
    openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    scheduling_api = SchedulingAPIClient(
        base_url=settings.scheduling_api_url, client=httpx_client
    )
    conversation_repo = RedisConversationRepository(redis=redis_client)
    agent_service = AgentService(
        openai_client=openai_client,
        scheduling_api=scheduling_api,
        conversation_repo=conversation_repo,
    )

    # Build routing table
    routes: dict[str, Route] = {}
    if settings.route_phone and settings.route_clinic_id:
        routes[settings.route_phone] = Route(
            phone_number=settings.route_phone,
            clinic_id=UUID(settings.route_clinic_id),
            doctor_id=UUID(settings.route_doctor_id) if settings.route_doctor_id else None,
        )
    routing_service = RoutingService(routes)

    return Container(
        agent_service=agent_service,
        routing_service=routing_service,
        httpx_client=httpx_client,
        redis_client=redis_client,
    )


async def shutdown(container: Container) -> None:
    await container.httpx_client.aclose()
    await container.redis_client.close()
