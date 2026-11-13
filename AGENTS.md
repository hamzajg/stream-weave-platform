# AGENTS.md — StreamWeave Platform

Guidance for AI agents (and humans) working in this repository.

## Project

StreamWeave is an enterprise AI-agentic workflow platform: business users
build/deploy/manage agentic workflows without code. Python **FastAPI**
backend + React/TypeScript/Tailwind **webapp**, multi-tenant orgs, designed
to integrate with Microsoft AutoGen Studio. Docker + docker-compose for
deployment.
Stack: Python 3 (FastAPI, SQLAlchemy-style models, JWT auth), React 18 +
Vite + TypeScript + Tailwind.

## Commands

Verified 2026-11-13 against CI (`.github/workflows/ci.yml`) and README.

| Task | Command |
|---|---|
| Backend tests | `pip install -r requirements-dev.txt && pytest` (from repo root; `pytest.ini` present) |
| Backend dev server | `uvicorn app.main:app --reload --port 8000` |
| Frontend install | `cd webapp && npm ci` |
| Frontend build | `cd webapp && npm run build` (`tsc -b && vite build`) |
| Frontend lint | `cd webapp && npm run lint` |
| Frontend dev | `cd webapp && npm run dev` |
| Full stack | `docker compose up` (Dockerfile + docker-compose.yml at root) |

Backend serves the built frontend from `app/static/` at `GET /`.

## Architecture

```
app/                        FastAPI backend
  main.py                   app factory: mounts routers, GET / + /health
  config.py                 settings (env-driven)
  database.py               DB engine/session (SQLite streamweave.db default)
  api/
    health.py               /api health
    auth.py                 /api/auth: register, login, refresh, me,
                            logout, password-reset request/confirm
    organizations.py        /api/orgs: multi-tenant org management
    onboarding.py           /api/onboarding: org/user onboarding flow
    dashboard.py            /api/dashboard: dashboard data
  models/                   user.py, organization.py, invitation.py
  schemas/                  pydantic request/response models
  static/                   built frontend (served at /)
  utils/                    helpers
webapp/                     React + Vite + TS + Tailwind frontend
  src/{pages,components,contexts,styles}
tests/                      pytest suite
streamweave.db              SQLite dev database (gitignored? verify)
docker-compose.yml          backend + webapp containers
```

### API surface (backend, prefix `/api`)

| Router | Mount | Notes |
|---|---|---|
| health | `/api` | health checks |
| auth | `/api/auth` | register/login/refresh/me/logout/password-reset |
| organizations | `/api/orgs` | tenant CRUD |
| onboarding | `/api/onboarding` | onboarding flow |
| dashboard | `/api/dashboard` | dashboard aggregates |

Frontend talks to `/api/*` on the same origin (FastAPI serves static + API).

## Conventions

- Backend: FastAPI routers per domain in `app/api/`, pydantic schemas in
  `app/schemas/`, ORM models in `app/models/`. Keep routers thin — logic in
  services/utils, not handlers.
- Frontend: React function components, `react-router-dom`, contexts for
  shared state; Tailwind utility classes (no CSS modules).
- Auth is JWT (`/api/auth/login` → token; `refresh` for rotation).
- KISS/SOLID: one router per bounded context; schemas mirror models but
  stay separate (don't leak ORM objects).

## Landmines

- **Default branch is `main`, not `master`.**
- `streamweave.db` SQLite file — dev default; don't commit DB state.
- Password-reset has **no mail transport configured** — tokens expire per
  `PASSWORD_RESET_EXPIRE_MINUTES`; delivery is a TODO (README notes this).
- Frontend build output goes to `app/static/` — backend must be restarted
  or static dir refreshed to serve new UI.
- `.venv/` exists in working tree locally — use `requirements*.txt`, don't
  rely on it.
- AutoGen Studio integration is planned/partial — check `docs/` before
  assuming agent runtime exists.
- `pytest` needs `requirements-dev.txt` installed; plain `requirements.txt`
  lacks test deps.

## Agent rules

- Branch from `main`; name branches `feat/*`, `fix/*`, `chore/*`, `docs/*`.
- Docs-only changes still go through a PR; never commit to `main` directly.
- Verify before claiming: run `pytest` (backend) and `npm run build` +
  `npm run lint` (webapp) and report the real result.
- Keep API contract in sync: any `app/api/*` route change must update
  `docs/ARCHITECTURE.md` and the frontend caller in the same PR.
- Keep changes minimal and consistent with surrounding code. No drive-by
  refactors.
- Update AGENTS.md / docs/ARCHITECTURE.md when routes, models, env vars,
  or the frontend/backend boundary changes.
