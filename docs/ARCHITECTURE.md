# Architecture — StreamWeave Platform

Current-state map. Descriptive, not aspirational; see `docs/adr/` for why.

## Shape

```
stream-weave-platform/
├── app/                     FastAPI backend (Python)
│   ├── main.py              app factory; mounts routers; serves app/static
│   ├── config.py            env-driven settings
│   ├── database.py          engine/session; SQLite streamweave.db default
│   ├── api/                 routers: health, auth, organizations,
│   │                        onboarding, dashboard
│   ├── models/              user, organization, invitation
│   ├── schemas/             pydantic DTOs
│   ├── utils/               helpers
│   └── static/              built webapp (served at GET /)
├── webapp/                  React 18 + Vite + TS + Tailwind frontend
│   └── src/{pages,components,contexts,styles}
├── tests/                   pytest suite
├── docs/                    platform docs + ux-analysis-report
├── Dockerfile               backend image (serves API + static)
├── docker-compose.yml       local full-stack
└── requirements{,-dev}.txt  backend deps / test deps
```

## Request flow

1. Browser loads `GET /` → FastAPI serves `app/static/index.html` (built
   webapp).
2. Webapp calls same-origin `/api/*`.
3. Routers in `app/api/` validate via `app/schemas/`, persist via
   `app/models/` + `app/database.py`, return pydantic responses.
4. Auth: JWT — `POST /api/auth/login` issues token; `refresh` rotates;
   `me`/`logout` manage session.

## Data

SQLite `streamweave.db` (dev default). Models: `User`, `Organization`,
`Invitation` — multi-tenant orgs with invitations. Migrations: none
visible — schema is created from models; treat DB changes carefully.

## Frontend/backend contract

Same origin — no CORS needed in prod. Contract lives in
`app/api/*.py` route decorators + `app/schemas/`. Webapp proxies nothing;
it calls `/api/*` directly.

## Roadmap context (not yet built)

- Microsoft AutoGen Studio integration for agent execution.
- Visual workflow builder (no-code agentic workflows) — the product goal.
- Email delivery for password reset.
