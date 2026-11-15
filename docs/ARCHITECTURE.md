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
│   │                        onboarding, dashboard, agents
│   ├── agents/              agent runtime: tools.py (read-only tool
│   │                        registry), llm.py (OpenAI-compatible
│   │                        client), loop.py (LLM ↔ tools)
│   ├── models/              user, organization, invitation, agent
│   │                        (AgentConversation, AgentMessage)
│   ├── schemas/             pydantic DTOs (auth, organization, agents)
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

## Agent runtime (`app/agents/` + `/api/agents`)

Org-scoped chat agent — first slice (read-only tools, no workflow
builder yet):

- `POST /api/agents/conversations/{id}/messages` persists the user
  message, then `loop.run_turn` alternates LLM ↔ tool calls until the
  model answers without tool calls or `agent_max_iterations` (6) is hit.
- Other routes: `GET /api/agents/tools`, `POST/GET
  /api/agents/conversations`, `GET /api/agents/conversations/{id}`.
- Tools (`tools.py`) are read-only and re-check membership/role per
  call: `list_org_members`, `get_organization_info`,
  `list_pending_invitations` (admin+), `list_my_organizations`.
- LLM (`llm.py`) is any OpenAI-compatible `chat/completions` endpoint —
  default derived from `ollama_url` + `/v1`. Env: `AGENT_LLM_BASE_URL`,
  `AGENT_LLM_API_KEY`, `AGENT_LLM_MODEL` (default `llama3.1`),
  `AGENT_MAX_ITERATIONS`, `AGENT_MAX_HISTORY`.
- `AgentMessage.tool_calls` stores the raw JSON so history replays
  faithfully; tool results are `role="tool"` messages.
- LLM failures → `502` (`Agent backend error`); tool failures return an
  error result to the model — they never crash the loop.
- Conversations are private to their owner and bound to one org;
  membership is re-checked on every request.

## Frontend/backend contract

Same origin — no CORS needed in prod. Contract lives in
`app/api/*.py` route decorators + `app/schemas/`. Webapp proxies nothing;
it calls `/api/*` directly. The webapp does not call `/api/agents` yet —
the agent API is backend-first; a chat UI is future work.

## Roadmap context (not yet built)

- Microsoft AutoGen Studio integration for agent execution — the agent
  runtime in `app/agents/` is the in-house first slice; AutoGen remains
  the longer-term engine decision (ADR 0002).
- Visual workflow builder (no-code agentic workflows) — the product goal.
- Write tools for the agent (org/invitation mutations need a
  confirmation design first).
- Email delivery for password reset.
