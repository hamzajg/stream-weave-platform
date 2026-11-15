# ADR 0002 — Agent runtime: in-house loop first, AutoGen later

Date: 2026-11-15
Status: accepted

## Context

StreamWeave's product goal is no-code AI agentic workflows. The README
names Microsoft AutoGen Studio as the intended engine, but no agent
runtime exists yet — only auth, orgs, onboarding, dashboard. The first
agent increment needed *something* real to build on: conversations,
tools, and a loop — without prematurely coupling to AutoGen's model.

## Decisions

1. **In-house agent loop in `app/agents/`.** A bounded loop
   (`loop.run_turn`): LLM → tool calls → tool results → repeat until a
   final answer or `agent_max_iterations` (6). Rationale: the loop is
   ~100 lines, fully testable with a fake LLM, and gives the product a
   working agent surface now; AutoGen can replace the *engine* later
   without changing the API or tool contract.
2. **OpenAI-compatible LLM client, no vendor SDK.** `llm.py` POSTs to
   `{base}/chat/completions` via httpx — Ollama's `/v1` layer is the
   default (`agent_llm_base_url` derived from `ollama_url`). Env:
   `AGENT_LLM_BASE_URL`, `AGENT_LLM_API_KEY`, `AGENT_LLM_MODEL`. Rationale:
   provider-agnostic — Ollama locally, any compatible endpoint in prod;
   httpx is already a dependency.
3. **Read-only tool registry, org-scoped.** `tools.py` registers
   functions that re-check org membership/role per call — the agent
   cannot exceed the caller's permissions. v1 tools are reads only
   (`list_org_members`, `get_organization_info`,
   `list_pending_invitations`, `list_my_organizations`). Rationale:
   writes need a confirmation design; reads prove the loop safely.
4. **Persisted conversations.** `AgentConversation` (org + owner) and
   `AgentMessage` (role, content, `tool_calls` JSON, tool linkage).
   History replays faithfully — tool calls are stored raw so the model
   sees the same shape it produced. Rationale: agent memory is the
   product; stateless single-turn would not be agentic.
5. **Conversations are private + org-bound.** Owner-only reads;
   membership re-checked per request. Rationale: multi-tenant safety —
   an agent acting for a user must never cross org boundaries.
6. **Failure semantics.** LLM errors → `502 Agent backend error`;
   tool errors → returned to the model as results (it can recover or
   explain). Rationale: a flaky tool shouldn't kill the conversation.

## Consequences / open questions

- **AutoGen Studio remains the long-term engine candidate** — this
  runtime is deliberately small; if AutoGen wins, `loop.py`/`llm.py`
  are the seam to replace, not the API or tools.
- **No write tools yet** — org/invitation mutations need a human
  confirmation step (design pending).
- **No streaming** — `send_message` returns when the turn completes;
  SSE streaming is a later increment (SSE infra doesn't exist yet).
- **No frontend** — the API is backend-first; a chat UI lands with the
  workflow builder work.
- **No workflow/agent definitions yet** — conversations are ad-hoc
  chat, not reusable agentic workflows. That's the next architectural
  decision (workflow model, triggers, runs).
- `agent_max_history` (20) bounds context — long conversations will
  need summarization.
