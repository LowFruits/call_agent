# Call Agent — Claude Instructions

## What This Repo Is
WhatsApp AI chatbot that replaces human secretaries at doctors' offices. Part of the LowFruits system.

For cross-repo context, ADRs, and API contracts, see the [meta repo](https://github.com/LowFruits/meta) (locally: `../meta/`).

## Stack
- Python 3.11+ / FastAPI / Pydantic v2
- OpenAI API (function calling)
- Twilio (WhatsApp webhooks)
- Redis (conversation state)
- Scheduling API: https://scheduling-simulation-api.onrender.com

## Package Layout
```
src/call_agent/
    api/         — FastAPI app, routes, dependencies
    domain/      — Models, enums, schemas
    services/    — Business logic (agent, conversation, scheduling client)
    repositories/ — Data access (Redis, API client)
```

## Commands
```bash
ruff check src/ tests/          # Lint
mypy src/                       # Type check
pytest                          # Test
uvicorn src.call_agent.api.app:app --reload  # Run
```

## Working With Me (Tomer)
- Never make code changes without explicit permission
- Explain what you plan to change and why before doing it
- Be concise, no fluff
- Update memory after sub-tasks
