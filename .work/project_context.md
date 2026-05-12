---
name: Project context
description: Key architectural decisions and infrastructure details for call_agent
type: project
originSessionId: fbd8085f-3cf1-4e7f-a651-c9fea5ecfb49
---
## Architecture
- FastAPI + Repository pattern with Protocol interfaces + constructor injection (bootstrap.py)
- Channel-agnostic message-handling core (services/) separated from transport (api/)
- Two interchangeable handlers behind `MessageHandlerProtocol`:
  - `services/protocol/engine.py` — deterministic FSM (Phase 2, default — `USE_PROTOCOL=true`)
  - `services/agent.py` — OpenAI-driven LLM agent (kept as fallback — `USE_PROTOCOL=false`)
- Conversation state in Redis (24h TTL) or file-based (local dev). Stores messages + protocol_state + protocol_context per (patient_phone, route_phone) scope.
- Local dev mode: file-based store, local chat UI at /chat, no Redis/Twilio needed

## Phase 2 Protocol (deterministic FSM)
- Module: `src/call_agent/services/protocol/`
  - `engine.py` — dispatches state → handler; also intercepts global navigation tokens before dispatch
  - `validators.py` — Israeli ID checksum, date parsing, intent/yes-no/visit-type/when-mode/etc parsers
  - `prompts_he.py` — single source of truth for Hebrew strings
  - `handlers/intent.py, new_booking.py, time_selection.py, existing.py, message.py, common.py`
- States cover the full call_recipe.pdf flow + sub-FSM time-selection (post-2026-05-12 redesign)
- `domain/protocol.py` — `ProtocolState`, `Branch`, `ProtocolContext` (Pydantic), `HistoryEntry`, helper enums
- Reschedule path uses sub-FSM (Option C) + "change something else" loop for visit_type/kupah edits
- `STUCK` state hook designed in for future hybrid LLM-fallback (not triggered in v1)

### Time-selection sub-FSM (post-2026-05-12 redesign)
- States: `TS_ASK_MODE` → either `TS_OFFER_CLOSEST` or `TS_ASK_SPECIFIC_DATE` → `TS_OFFER_DATE_SLOTS`; fallback `NO_SLOTS_OFFER_MESSAGE` when nothing in the next 180 days.
- `WhenMode` enum: `CLOSEST` (1) / `SPECIFIC_DATE` (2). Replaces the old 3-way `WhenPreference`.
- `TimeWindow` enum: 3 buckets — `MORNING` (09–12), `NOON` (12–15), `EVENING` (15–end), Asia/Jerusalem hours.
- Closest mode walks the doctor's working days (from `/doctors/{id}/availability`), filling up to 3 slots per window → renders a numbered 1–9 menu grouped by window header. Hard cap 180 days; 0 slots → routes to leave-message branch.
- Specific-date mode validates against availability rules + exceptions, fetches one day, picks 3 spread slots (first / middle / last).
- `ProtocolContext.declined_slot_starts: list[datetime]` — never re-offers a rejected slot in the same session.
- `ProtocolContext.offered_slots` / `offered_slots_end` — `dict[int, datetime]` mapping menu number → slot bounds. Kept across `_commit_pick` so back-nav can re-render the menu without an API round-trip.

### Global navigation (post-2026-05-12)
- Reserved tokens, intercepted in `engine.handle_message` before any handler runs:
  - `99` / `חזור` / `אחורה` / `back` — pop one step from `state_history`
  - `0` / `התחל מחדש` / `התחלה` / `restart` — clear context + state, return greeting
- `ProtocolContext.state_history: list[HistoryEntry]` + `last_prompt: str | None` track the back stack and the replayable current prompt.
- History pushed only on state-changing transitions (re-prompts don't accumulate).
- Engine appends `(99 = חזור, 0 = התחל מחדש)` to every non-terminal prompt (`ASK_INTENT`, `DONE`, `STUCK` exempted).
- Numeric picks parsed before decline-word check so `2` resolves as slot #2, not "no".

### Conversation-store resilience (post-2026-05-12)
- Both `RedisConversationRepository` and `FileConversationRepository` now catch `ValueError`/`ValidationError` on `get_protocol_state` / `get_protocol_context` and return fresh defaults. Active conversations from before a schema-changing deploy auto-restart at the greeting on the user's next message — no manual migration step needed.

## LLM Model (legacy/fallback path)
- Using **gpt-4o-mini** (not gpt-4o) — cost decision by Tomer
- Active when `USE_PROTOCOL=false`

## Local Dev Setup
- Comment out `REDIS_URL` in `.env` → uses `FileConversationRepository` (JSON at data/conversations.json)
- Chat UI at `http://localhost:8000/chat` (or `--port 8001` if 8000 busy) — doctor picker → scoped chat
- `GET /` redirects to `/chat`
- Patient phone hardcoded as `+972501234567`; route phone is per-doctor: `local:{doctor_id}` (so each doctor has its own conversation)
- Doctor selection in the UI calls `POST /chat/reset` — dev/QA convenience to start fresh every time
- Still uses Render-hosted Scheduling API (may cold-start on first request)

## External Services
- **Redis Cloud**: free tier, 30MB, us-east-1 (optional for local dev)
- **Twilio**: sandbox mode, number +14155238886, join code "vegetable-free" (not needed for local dev)
- **Scheduling API**: https://scheduling-simulation-api.onrender.com (Render free tier)
- **OpenAI**: separate account from Tomer's main, key named "call-agent"

## Data Model Changes
### 2026-04-13
- `clinic_id` now optional on list endpoints (doctors, appointment types) — 1 doctor = 1 clinic
- New table: `doctor_health_funds` (which kupot cholim each doctor accepts)
- New fields on `appointment_types`: `price_private`, `price_health_fund`
- New field on `patients`: `id_number` (teudat zehut, 9 digits)
- New table: `patient_relations` (family tree linking)
- New endpoints: `/patients/search`, `/patients/{id}/has-visited/{doctor_id}`

### 2026-04-26: ADR-009 — `AppointmentType` is doctor-scoped
- `clinic_id` field DROPPED from AppointmentType; replaced by required `doctor_id`
- Listing endpoint moved: `GET /doctors/{doctor_id}/appointment-types?active_only=…` (old `/appointment-types/?clinic_id=…` is gone)
- Slot + booking endpoints now strictly validate `(doctor_id, appointment_type_id)` pairs (404/4xx on mismatch)
- Existing appointment-type UUIDs were invalidated by the migration (rows fanned out per-doctor)
- AppointmentType model now also returns `price_private`, `price_health_fund` (string | null)

### 2026-04-26: Database_Simulation `/messages/` endpoint shipped
- New entity for the leave-message branch: `id, doctor_id, patient_phone, patient_name?, body, status (pending/read/replied/archived), created_at, read_at?, replied_at?`
- Endpoints: `POST /messages/`, `GET /messages/`, `GET /messages/{id}`, `PATCH /messages/{id}`
- `clinic_id` intentionally omitted (derivable from doctor_id)
- Validation errors return 422 (FastAPI default), not 400

### 2026-04-26: Timezone — DB sim adopted Option A (everything tz-aware)
- `/scheduling/slots` returns ISO with Asia/Jerusalem offset (`+03:00`/`+02:00` DST-aware)
- POST `/scheduling/appointments/book` requires tz-aware `start_time`; naive → 422
- All appointment reads return UTC with `Z` suffix; same instant as the offered slot
- All other timestamps (created_at, updated_at, cancelled_at, read_at, replied_at) are tz-aware UTC
- call_agent's data flow is naturally tz-preserving (Pydantic v2 pass-through) — no code change needed

## Test Data
- Clinic: "Tomer" (3fa85f64-5717-4562-b3fc-2c963f66afa6) in Bat Galim
- 7 doctors (ENT, Pediatrics, Dermatology, Gynecology, Gastroenterology, Vascular Surgery)
- 4 appointment types (ביקור ראשון 30m, ביקור חוזר 15m, ייעוץ 20m, בדיקה 45m)
- Availability: Sun-Thu 09:00-17:00 for all doctors
- Note: 1 duplicate "ביקור ראשון" appointment type exists (from early failed attempt)
- Health funds, pricing, patient IDs: not yet seeded — will be done via admin dashboard

## Deployment
- **Call Agent**: https://call-agent-oj4k.onrender.com (Render free tier)
- **Twilio webhook**: POST https://call-agent-oj4k.onrender.com/webhook/twilio
- Tool executors receive `route` context — clinic-scoped tools auto-fill clinic_id from route

## Key Files
- `scripts/seed_data.py` — seeds appointment types + availability rules
- `.env` — local credentials (gitignored)
- `render.yaml` — deployment config
- `src/call_agent/api/routes/chat.py` — local chat UI endpoints (incl. `POST /chat/reset`)
- `src/call_agent/api/static/chat.html` — chat UI HTML
- `src/call_agent/repositories/file_conversation.py` — file-based conversation store
- `src/call_agent/services/protocol/` — Phase 2 deterministic FSM module
- `src/call_agent/domain/protocol.py` — protocol state + context types
- `call_recipe.pdf` — source-of-truth questionnaire that defined the FSM flow

## New Repos (planned/in progress)
- **admin-dashboard** — pure HTML/JS admin tool for managing doctors, patients, calendars. Talks directly to Scheduling API.
