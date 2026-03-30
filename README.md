# Call Agent

WhatsApp AI chatbot that replaces human secretaries at doctors' offices. Patients message via WhatsApp to schedule appointments, get doctor info, and ask clinic questions.

## Architecture

```
Patient (WhatsApp) → Twilio → FastAPI webhook → OpenAI (tools) → Scheduling API
                                    ↕
                              Redis (conversation state)
```

- **LLM**: OpenAI with function calling — scheduling API endpoints exposed as tools
- **WhatsApp**: Twilio (webhook-based)
- **Routing**: Each Twilio number maps to a clinic/doctor
- **State**: Redis with 24h TTL for conversation history

## Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in:
```
OPENAI_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
REDIS_URL=
SCHEDULING_API_URL=https://scheduling-simulation-api.onrender.com
```

## Run

```bash
uvicorn src.call_agent.api.app:app --reload
```

## Status

**Phase 1 — Foundation** (in progress)
