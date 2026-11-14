# ADR 0001 — Initial architecture

Date: 2026-11-13 (baseline recorded retroactively)
Status: accepted (describes what is built)

## Context

StreamWeave aims to be an enterprise no-code platform for AI agentic
workflows. The first iterations delivered the foundation: landing page,
auth, multi-tenant orgs, onboarding, dashboard — with the agent runtime
still ahead.

## Decisions

1. **FastAPI + React/Vite/TS/Tailwind.** Python API backend, React SPA
   frontend, same-origin deployment (FastAPI serves `app/static/`).
   Rationale: fast iteration, single deployable, typed contract via
   pydantic.
2. **Router-per-domain in `app/api/`.** health, auth, organizations,
   onboarding, dashboard — one APIRouter each, mounted in `main.py`.
   Rationale: bounded contexts stay small and independently testable.
3. **JWT auth with refresh rotation.** `/api/auth` issues access + refresh
   tokens; `me`/`logout`/password-reset endpoints cover the session
   lifecycle. Rationale: standard stateless API auth; refresh supports
   longer sessions without long-lived tokens.
4. **SQLite for dev, Docker for prod shape.** `streamweave.db` is the dev
   default; Dockerfile + compose package backend + built frontend.
   Rationale: zero-infra local dev; production DB choice still open.
5. **Schemas separate from models.** pydantic `schemas/` mirror `models/`
   but don't leak ORM objects. Rationale: stable API contract independent
   of persistence changes.

## Consequences / open questions

- No DB migrations tool — schema managed by model metadata; adding
  columns needs care on existing `streamweave.db` files.
- Password-reset has no mail transport — delivery is unsolved.
- AutoGen Studio / workflow-builder runtime is the next architectural
  decision (where agent execution lives, how workflows are stored).
- No CI-visible frontend tests; coverage is backend pytest + frontend
  build/lint only.
