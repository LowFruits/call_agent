---
name: Project roadmap
description: Phase-by-phase roadmap with completion status
type: project
originSessionId: fbd8085f-3cf1-4e7f-a651-c9fea5ecfb49
---
## Phase 1 — Foundation
- [x] Project scaffolding and CI
- [x] Domain models and schemas (Pydantic v2)
- [x] Scheduling API client (11 endpoints, httpx)
- [x] Redis conversation store (24h TTL)
- [x] Agent service with OpenAI function calling (11 tools)
- [x] Hebrew system prompt builder
- [x] Twilio webhook integration (TwiML responses)
- [x] Bootstrap wiring (constructor injection)
- [x] External services setup (Redis Cloud, Twilio sandbox, OpenAI)
- [x] Test data seeded (doctors, appointment types, availability)
- [x] Local E2E test passing
- [x] Deploy to Render (https://call-agent-oj4k.onrender.com)
- [x] Connect Twilio sandbox webhook to Render URL
- [x] File-based conversation store (local dev, no Redis needed)
- [x] Local chat UI with doctor picker (/chat)
- [x] clinic_id made optional across system
- [ ] Fix CI: add python-multipart to test dependencies

## Phase 2 — Deterministic Chat Protocol
- [x] Implement state machine for booking flow (based on PDF questionnaire) — 28 states
- [x] Opening question: existing appointment / new / leave message
- [x] New appointment flow: kupat cholim, visit type, date preference, patient ID, SMS consent, summary, book
- [x] Existing appointment flow: view details, reschedule (with change-else loop), cancel, more-info placeholder
- [x] Leave-message branch (writes to DB sim `/messages/` endpoint)
- [x] Time-selection sub-FSM (reusable by new + reschedule)
- [x] USE_PROTOCOL env flag (default true) — LLM agent stays as fallback
- [x] Per-doctor conversation scoping in chat UI
- [x] Hebrew-only prompts centralised in `prompts_he.py`
- [x] STUCK hook designed in for future hybrid LLM fallback
- [ ] Per-doctor protocol extensions (extra questions per doctor — future enhancement)
- [ ] Later: layer OpenAI on top via STUCK hook for off-script user input

## Phase 3 — Admin Dashboard (separate repo)
- [ ] Scaffold admin-dashboard repo
- [ ] Doctors list page
- [ ] Doctor detail page (info, kupot cholim, pricing, availability, calendar)
- [ ] Add doctor guided form
- [ ] Patient search
- [ ] Query bar for debugging

## Phase 4 — Production Readiness
- [ ] Logging and observability
- [ ] Rate limiting
- [ ] Real clinic onboarding
