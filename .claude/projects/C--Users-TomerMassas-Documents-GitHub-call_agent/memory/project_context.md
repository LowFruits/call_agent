---
name: Project Context
description: Overall description of this repo — architecture, purpose, key decisions
type: project
---
## Overview
WhatsApp AI chatbot replacing human secretaries at doctors' offices. Patients message via WhatsApp to schedule appointments, get doctor info, and ask clinic questions. Part of the LowFruits system.

## Architecture
Patient (WhatsApp) → Twilio webhook → FastAPI → OpenAI (function calling) → Scheduling API
Conversation state stored in Redis with 24h TTL.
Phone-number routing: each Twilio number maps to a clinic/doctor.

## Infrastructure
- LLM: OpenAI API (GPT-4o) with function calling
- WhatsApp: Twilio (webhook-based)
- Conversation state: Redis Cloud (free tier)
- Scheduling backend: Database_Simulation (https://scheduling-simulation-api.onrender.com)
- Deployment: Render (free tier, service name: call-agent)

## Key Entities
- Route: Twilio phone number → clinic_id + optional doctor_id
- Conversation: Message history per patient+route (Redis, 24h TTL)
- Tool: LLM action wrapping a scheduling API endpoint
