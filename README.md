# Call Agent

WhatsApp AI chatbot that replaces human secretaries at doctors' offices. Patients message via WhatsApp to schedule appointments, get doctor info, and ask clinic questions.

## Architecture

```
┌─────────────┐         ┌─────────────────┐         ┌──────────────────────────────┐
│   Patient    │         │     Twilio       │         │     Call Agent (FastAPI)      │
│  (WhatsApp)  │────────▶│  WhatsApp API    │────────▶│  POST /webhook/whatsapp      │
│              │◀────────│                  │◀────────│                              │
└─────────────┘  reply   └─────────────────┘  TwiML  │   ┌──────────────────────┐   │
                                                      │   │   Agent Service       │   │
                                                      │   │   (conversation mgr)  │   │
                                                      │   └───────┬────────┬─────┘   │
                                                      └───────────┼────────┼─────────┘
                                                                  │        │
                                              ┌───────────────────┘        └──────────────────┐
                                              ▼                                               ▼
                                ┌──────────────────────┐                        ┌─────────────────────┐
                                │    OpenAI API         │                        │   Redis              │
                                │    (gpt-4o-mini)      │                        │   (conversation      │
                                │                       │                        │    state, 24h TTL)   │
                                │  11 function-calling   │                        └─────────────────────┘
                                │  tools exposed:       │
                                │  - search doctors     │
                                │  - check availability │
                                │  - book/cancel appts  │
                                │  - clinic info        │
                                └───────────┬───────────┘
                                            │ tool calls
                                            ▼
                                ┌───────────────────────┐
                                │  Scheduling API        │
                                │  (Database_Simulation) │
                                │  on Render             │
                                │                        │
                                │  doctors, clinics,     │
                                │  availability, slots,  │
                                │  appointments          │
                                └────────────────────────┘
```

- **LLM**: OpenAI with function calling — scheduling API endpoints exposed as 11 tools
- **WhatsApp**: Twilio webhook-based, responds with TwiML
- **Routing**: Each Twilio number maps to a clinic/doctor
- **State**: Redis with 24h TTL for conversation history
- **Language**: All patient-facing responses in Hebrew

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
