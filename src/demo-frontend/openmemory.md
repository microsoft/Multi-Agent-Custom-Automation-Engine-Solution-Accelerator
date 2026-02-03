## Overview
- Multi-service AI voice receptionist + lead gen project.
- Demo frontend in `src/demo-frontend` (Next.js app router) for chat, calls, and scheduling UI.
- Backend services include `src/leadgen` (Python lead-gen pipeline) and `src/voice-server` (FastAPI WebSocket proxy).

## Architecture
- `src/demo-frontend/app` uses Next.js app router with page-level composition.
- `src/demo-frontend/components` holds UI widgets for the demo (chat, calls, calendar, stats).
- `src/leadgen` contains agents, integrations, models, and orchestration for lead generation.
- `src/voice-server` is a FastAPI WebSocket service bridging Twilio streams to OpenAI Realtime.

## User Defined Namespaces
- [Leave blank - user populates]

## Components
- `CallButton`: Manages Twilio call initiation via WebSocket and call state transitions.
- `ChatInterface`: Chat UI with scrolling and message actions for demo conversations.
- `AppointmentCalendar`: Week/month calendar views and appointment filtering by range.

## Patterns
- Date-only appointment strings use `YYYY-MM-DD` and are treated as local dates in UI.
- Calendar day keys derive from local date strings for consistent mapping and filtering.
