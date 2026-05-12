---
name: Project progress
description: Session-by-session log of work done on call_agent
type: project
originSessionId: fbd8085f-3cf1-4e7f-a651-c9fea5ecfb49
---
## 2026-03-30 — Session 1: Phase 1 Foundation

- Explored meta repo: learned all ADRs, API contracts, coding standards, infrastructure setup
- Planned and implemented all 7 Phase 1 steps (domain → repos → services → API → bootstrap)
- 58 tests passing, ruff clean, mypy strict clean
- Committed: `bca1ddf Implement Phase 1 foundation: full E2E WhatsApp agent pipeline`
- Set up external services: Redis Cloud (free tier), Twilio sandbox, OpenAI (new account)
- Seeded test data: 4 appointment types + availability rules for all 7 doctors (Sun-Thu 09:00-17:00)
- Created `.env` with all credentials
- Switched default model from gpt-4o to gpt-4o-mini (cost savings)
- Local test confirmed: agent responds in Hebrew via Twilio webhook
- Created `scripts/seed_data.py` for repeatable data seeding

## 2026-04-05 — Session 2: Deploy to Render & First Bug Fix

- Deployed call-agent to Render: https://call-agent-oj4k.onrender.com (free tier)
- Connected Twilio sandbox webhook to `/webhook/twilio` (initially tried wrong path `/webhook/whatsapp`)
- Added env vars on Render: OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, REDIS_URL, SCHEDULING_API_URL, ROUTE_PHONE, ROUTE_CLINIC_ID
- Fixed routing issue: ROUTE_PHONE/ROUTE_CLINIC_ID env vars were missing on Render
- Fixed UUID bug: LLM was guessing clinic_id for tools (badly formed UUID). Refactored tool executors to auto-fill clinic_id from route context instead of LLM args
- Committed: `1afc9cd Auto-fill clinic_id from route context in tool executors`
- Updated README with detailed architecture block diagram
- Discovered cold-start timeout issue: both Render free tier services sleep after 15 min, stacking cold starts exceeds Twilio's timeout
- **Not resolved yet**: cold-start / timeout problem needs addressing next session

## 2026-04-13 — Session 3: Local Dev Environment & Architecture Pivot

- Decided to move away from hosted free-tier services to a local dev environment (avoid cold-start issues, $0 cost)
- Implemented `FileConversationRepository` — file-backed JSON conversation store replacing Redis for local dev
- Bootstrap auto-detects: if `REDIS_URL` not set, uses file store; if set, uses Redis (backward compatible)
- Made `clinic_id` optional across the system (call_agent client + protocol, Database_Simulation API) — since 1 doctor = 1 clinic
- Built local chat UI: `GET /chat` serves WhatsApp-style HTML page, `GET /chat/doctors` lists doctors, `POST /chat/send` handles messages
- Chat UI has doctor picker on load → selects doctor → scopes agent to that doctor
- Exposed `scheduling_api` on Container/app.state for chat route to use
- Verified chat UI loads and doctor list populates from Render-hosted Scheduling API
- Extended Database_Simulation schema: doctor_health_funds table, appointment type pricing, patient id_number, patient_relations, patient search endpoint, first-visit check endpoint
- Planned and sent prompt for new `admin-dashboard` repo (pure HTML/JS admin tool for managing doctors/patients/calendars)
- Planned deterministic chat protocol to replace OpenAI agent (based on Tomer's PDF questionnaire)

**Next steps:**
1. Commit all uncommitted local dev changes in call_agent
2. Admin dashboard repo: scaffold and implement doctors list + detail pages
3. DB schema: seed doctor health funds, pricing, and patient data via admin dashboard
4. Implement deterministic chat protocol in call_agent (state machine, no AI for now)
5. Fix CI: add `python-multipart` to test dependencies

## 2026-04-26 → 2026-04-27 — Session 4: Phase 2 Protocol + ADR-009 Sync

### Phase 2 deterministic chat protocol — fully implemented (commit c2a8b0c)
- Built `src/call_agent/services/protocol/` module: engine, validators, prompts_he, 5 handler files (intent, new_booking, time_selection, existing, message), common helpers
- 28-state FSM covering the full call_recipe.pdf flow: intent menu → new-booking (first-visit, kupah, birth date, visit type, time-selection sub-FSM, for-self, IDs, SMS consent, summary, book) → existing-appointment (more-info, reschedule with change-else loop, cancel) → leave-message → DONE
- Reschedule uses Option C (sub-FSM): time-selection is reusable, plus a "change something else" loop for visit-type/kupah edits
- New domain types: `domain/protocol.py` with `ProtocolState` enum, `Branch`, `ProtocolContext`, helper enums
- Conversation repo extended (Redis + file): `get/set_protocol_state`, `get/set_protocol_context`, separate keys, same TTL
- `services/__init__.py` defines `MessageHandlerProtocol` — both `AgentService` and `ProtocolEngine` satisfy it
- New env flag `USE_PROTOCOL=true` (default); `false` falls back to the LLM agent
- Routes (`webhook.py`, `chat.py`) wired through the new protocol via DI
- Hebrew-only prompts; future LLM-fallback hook designed in via `STUCK` state (not triggered in v1)
- Caught and fixed a Windows `strftime` bug — can't encode non-ASCII format chars; switched to numeric formatting + literal Hebrew

### Cross-repo: Database_Simulation `messages` table (commit c2a8b0c)
- DB sim shipped a new `messages` entity + 4 endpoints (POST/GET/PATCH) per the prompt I wrote
- Added `create_message()` to scheduling client; FSM's leave-message branch + more-info placeholder both use it
- Note: DB sim dropped `clinic_id` from messages (derivable from doctor_id) — already reflected
- Note: validation errors return 422 (FastAPI default), not 400

### Cross-repo: ADR-009 — per-doctor appointment types (commit c2a8b0c)
- DB sim shipped breaking change: `AppointmentType` is now doctor-scoped (`clinic_id` removed, `doctor_id` added)
- Listing endpoint: `GET /doctors/{doctor_id}/appointment-types?active_only=…` (old `/appointment-types/?clinic_id=…` is gone)
- Slot/booking endpoints now strictly validate `(doctor_id, type_id)` pairs
- All call_agent call sites updated, AppointmentType model now has `doctor_id` + optional `price_private`/`price_health_fund`
- LLM tool schema for `list_appointment_types` now requires `doctor_id` param
- Added mismatch error handling: `httpx.HTTPStatusError` in `_find_and_offer_slot` re-prompts with new `BOOKING_SLOT_GONE` Hebrew string; tightened `Exception` catch in summarize-and-confirm to log + show `BOOKING_FAILED`

### Cross-repo: timezone Option A shipped on DB sim (NO call_agent code change needed)
- DB sim shipped tz-aware everywhere: `/scheduling/slots` returns `+03:00`, bookings require tz-aware `start_time` (naive → 422), appointment reads return UTC with `Z` suffix
- Verified call_agent's data flow is naturally tz-preserving end-to-end (Pydantic v2 + pass-through pattern). No code change required.
- Optional follow-ups discussed but NOT done: (a) update test fixtures to mirror tz-aware live contract, (b) fix `_candidate_dates` to use Jerusalem-local "today" (avoids 21:00–23:59 UTC edge case)

### Phase 2 testing
- 124 tests passing total (added: 44 validator tests, 6 file-conversation-repo tests, 10 protocol engine integration tests, +1 mismatch test)
- ruff + mypy strict clean
- Live verified: end-to-end new-booking through chat UI succeeds against the real Render-hosted backend; appointment lands in DB

### Local chat UI — per-doctor scoping + dev reset (UNCOMMITTED, last 5 files)
- Conversation key was previously `conv:+972501234567:local` regardless of doctor — switching doctors leaked state
- Now `local:{doctor_id}` — each doctor has its own conversation
- Added `POST /chat/reset` endpoint; chat.html calls it on every doctor selection (dev/QA convenience — Twilio webhook untouched)
- Bootstrap exposes `conversation_repo` on Container/app.state; new `get_conversation_repo` dep
- Files: bootstrap.py, app.py, deps.py, chat.py, chat.html (+ my_prompt scratch file)

### Process feedback
- Mid-session, I started editing for the per-doctor change without a written plan — Tomer interrupted and rejected. Reverted, wrote the plan, got approval, then executed.
- Updated `feedback_no_rush.md` to make explicit: bar for skipping a plan is essentially zero. Even mid-session tweaks need a written plan first.

**Next steps:**
1. Commit the 5 uncommitted local-dev files (per-doctor scoping + reset endpoint) — SHOULD do today
2. Optional: update test fixtures for tz-aware contract + Jerusalem-local "today" fix in `_candidate_dates`
3. Verify in dashboard repo that the timezone fix actually surfaces appointments on the slot grid (was the original bug that started the timezone thread)
4. Phase 3: admin dashboard work continues in separate repo
5. Future: layer LLM on top of the deterministic protocol (the `STUCK` state hook is in place)

## 2026-05-12 — Session 5: Protocol UX overhaul (6 user-driven changes)

Six changes to the deterministic FSM driven by chat-UX feedback. Planned end-to-end (see plan summary inline) and executed as four logical commits' worth of code, currently a single uncommitted working tree.

### Numbered yes/no prompts (Item 1)
- Rewrote 8 strings in `prompts_he.py` from `(כן/לא)` to numbered `1. כן / 2. לא` form: `ASK_FIRST_VISIT`, `CONFIRM_PRIVATE`, `ASK_FOR_SELF`, `ASK_SMS_CONSENT`, `CONFIRM_CANCEL`, `SUMMARY_CONFIRM_NEW_TEMPLATE`, `SUMMARY_CONFIRM_RESCHEDULE_TEMPLATE`, `OFFER_SLOT_TEMPLATE` (now retired).
- `parse_yes_no` already accepted `1`/`2`, so no parser change required.

### ID validation explanation (Item 2)
- No code change — clarified to Tomer that `is_valid_israeli_id` runs the teudat-zehut checksum (Luhn-like). `123456789` fails because the 9th digit isn't constructed to make the sum divisible by 10.

### Time-selection redesign (Items 4 + 5 + 6)
- **States**: removed `TS_ASK_WINDOW`, `TS_ASK_WHEN`, `TS_OFFER_SLOT`. Added `TS_ASK_MODE`, `TS_OFFER_CLOSEST`, `TS_OFFER_DATE_SLOTS`, `NO_SLOTS_OFFER_MESSAGE`.
- **Flow**: visit-type → `איך תרצה לבחור מועד?` (1=closest / 2=specific date).
  - Closest mode walks the doctor's working days (from new `GET /doctors/{id}/availability` client call) and fills up to 3 slots per window (morning 09–12, noon 12–15, evening 15–end Asia/Jerusalem). Renders 1–9 menu grouped by window. Hard cap 180 days; on 0 slots → `NO_SLOTS_OFFER_MESSAGE` → yes routes to leave-message branch, no → DONE.
  - Specific-date mode shows working days line, validates the user's date against rules + exceptions, fetches that day's slots, returns up to 3 indexed picks spread across the day (first / middle / last).
- **Decline UX**: typing "לא" at an offer cycles the *next* batch (closest) or refetches with declined filtered (specific). Numeric picks resolved before the "no" check so `2` doesn't mis-trigger decline.
- **Declined memory** (Item 6): new `ProtocolContext.declined_slot_starts: list[datetime]`. Never re-offers a previously-rejected start time across the session.
- **Domain model additions**: `AvailabilityRule`, `CalendarException`, `DoctorAvailability` in `domain/models.py`. `TimeWindow` enum extended to 3 values. New `WhenMode` enum replaces `WhenPreference`. New `offered_slots` / `offered_slots_end` dict maps on `ProtocolContext`.
- **Helpers**: `slot_window`, `working_weekdays`, `is_date_blocked`, `format_working_days`, `format_slot_line` in `handlers/common.py`. Hebrew weekday names included.
- **Format change**: `format_when` now prefixes the weekday, e.g. `יום ראשון 14/05/2026 בשעה 09:00`.
- **Schema break safety**: both `RedisConversationRepository` and `FileConversationRepository` now catch `ValueError`/`ValidationError` on `get_protocol_state`/`get_protocol_context` and return fresh defaults. Active conversations from before this deploy auto-restart at the greeting on next message.

### Global back/restart navigation (Item 3)
- Reserved tokens: `99` (and `חזור`/`אחורה`/`back`) = back one step; `0` (and `התחל מחדש`/`התחלה`/`restart`) = full reset to greeting.
- Engine intercepts tokens before dispatching to handlers — no per-handler boilerplate.
- New `HistoryEntry` pydantic model + `ProtocolContext.state_history` stack + `ProtocolContext.last_prompt` for replayable rollback. History pushed only on state changes (re-prompts don't accumulate).
- Per-prompt hint `(99 = חזור, 0 = התחל מחדש)` appended by the engine. Suppressed at `ASK_INTENT`, `DONE`, `STUCK`.
- `_commit_pick` no longer clears `offered_slots` so "back" from `ASK_FOR_SELF` → `TS_OFFER_CLOSEST` re-renders the menu without re-querying the API.
- Edge cases: empty stack + `99` re-shows current prompt; `2` as a slot pick precedes the decline parse so it doesn't mis-trigger; `99` literal as a name/message body is interpreted as nav (accepted trade-off).

### Tests
- 132 tests passing (was 124). Added: declined-slot memory, non-working-day rejection, 180-day → leave-message fallback, back returns to previous state, restart returns to greeting, nav hint appended/skipped correctly, back works inside time-selection.
- Updated walks for the new state sequence: closest-mode happy path is 11 messages (was 12 with the old window→when split).
- ruff + mypy strict clean.

### Process notes
- Single planning pass up-front, four logical commits' worth of code grouped as one working tree per Tomer's preference at session-end (`/session-end` ritual ships one commit).
- Tomer's manual verification: "seems to work very good".

### Next steps
1. Single commit + push (handled by `/session-end`).
2. Live verification in `/chat` UI against the Render-hosted backend — quick smoke through closest mode (should show 9 numbered slots grouped by window) and specific date (3 spread slots). Tests cover the logic; UI hasn't been touched.
3. Optional polish: `parse_int_choice` only matches digits 1–9 today, which is fine for the current 9-max menu but caps the design. If we ever need 10+ options, widen the regex.
4. Outstanding from prior sessions (not progressed this session): CI `python-multipart` fix; tz-aware test fixtures; Jerusalem-local `_candidate_dates`; admin-dashboard repo work.
5. Future: hybrid LLM fallback via the `STUCK` hook — now meaningful since users have escape hatches (`0`/`99`) and a leave-message fallback.
