# Call Agent — Design Document

## Mission
Replace human secretaries at doctors' offices with a WhatsApp AI chatbot. Patients message to schedule appointments, ask about doctors, and get clinic information — in natural Hebrew conversation.

## Constraints
- WhatsApp as the primary channel (voice may be added later as a separate channel)
- Must use the scheduling API (Database_Simulation) as its data source — no direct DB access
- Israeli market — conversations primarily in Hebrew
- Channel-agnostic core — separate conversation logic from transport
- Each Twilio number maps to a specific clinic/doctor (phone-number routing)

## Domain Entities
- **Route**: Maps a Twilio phone number to a clinic_id + optional doctor_id
- **Conversation**: Message history for a patient on a specific route (stored in Redis, 24h TTL)
- **Tool**: An action the LLM can take — wraps a scheduling API endpoint

## Infrastructure
- **LLM**: OpenAI API (GPT-4o) with function calling
- **WhatsApp**: Twilio (webhook → FastAPI)
- **Conversation state**: Redis Cloud (free tier, 30MB)
- **Scheduling backend**: Database_Simulation API (https://scheduling-simulation-api.onrender.com)
- **Deployment**: Render (free tier)

## Key Decisions
See meta repo ADRs:
- ADR-004: OpenAI as LLM
- ADR-005: Twilio for WhatsApp
- ADR-006: Phone-number routing
- ADR-007: Redis for conversation state

## Phases

### Phase 1 — Foundation
- Project scaffolding and CI
- Scheduling API client (generated from OpenAPI spec)
- Basic agent with tool definitions
- Twilio webhook integration
- Redis conversation store
- End-to-end: patient sends message → agent responds

### Phase 2 — Conversational Quality
- Hebrew system prompts and conversation tuning
- Multi-turn appointment booking flow
- Error handling and edge cases
- Doctor operational info (pricing, policies) in responses

### Phase 3 — Production Readiness
- Logging and observability
- Rate limiting
- Deployment to Render
- Real clinic onboarding
