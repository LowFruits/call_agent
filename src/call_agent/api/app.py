from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from call_agent.api.routes import chat_router, webhook_router
from call_agent.bootstrap import bootstrap, shutdown


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = await bootstrap()
    app.state.agent_service = container.agent_service
    app.state.routing_service = container.routing_service
    app.state.scheduling_api = container.scheduling_api
    yield
    await shutdown(container)


app = FastAPI(title="Call Agent", version="0.1.0", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
