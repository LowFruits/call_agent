---
name: Project status
description: Current phase and progress of call_agent development
type: project
originSessionId: fbd8085f-3cf1-4e7f-a651-c9fea5ecfb49
---
As of 2026-04-27: Phase 2 deterministic chat protocol live and verified end-to-end.

**Done:**
- Phase 1: Full E2E pipeline (FastAPI + OpenAI + Twilio + Redis), deployed to Render, Twilio webhook connected
- Local dev environment: file-based store, chat UI at /chat, redirect from /
- DB schema extended: health funds, pricing, patient ID, family relations, search, `/messages/` endpoint
- Phase 2: deterministic chat protocol implemented — 28-state FSM covering full call_recipe.pdf flow (new booking, reschedule with change-else loop, cancel, leave message, more-info placeholder)
- ADR-009 sync: AppointmentType doctor-scoped; mismatch errors handled gracefully
- Per-doctor conversation scoping in chat UI; reset on doctor selection
- 124 tests passing, ruff + mypy strict clean
- End-to-end new-booking verified live against Render backend

**In progress:**
- Admin dashboard repo (separate repo, scaffolding/in-development)
- Dashboard timezone-aware display verification (DB sim shipped Option A; need to confirm dashboard surfaces appointments correctly)

**Next:**
1. Commit uncommitted local-dev changes (per-doctor scoping + /chat/reset endpoint)
2. Optional polish: tz-aware test fixtures, Jerusalem-local `_candidate_dates`
3. Admin dashboard: doctors list + detail pages
4. Seed doctor config data (kupot cholim, pricing) via admin dashboard
5. Future: hybrid mode — layer LLM on top of FSM via the `STUCK` hook for off-script questions
