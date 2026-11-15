# ADR 0003 — Human-confirmed write tools for the agent

## Status

Accepted — implemented on `feat/agent-write-confirmation`.

## Context

ADR 0002 shipped the agent runtime with read-only tools; write
capabilities were explicitly deferred until a confirmation design
existed. The question: how does an LLM-driven agent perform state
changes without acting autonomously?

## Decision

Two-phase propose → approve, enforced structurally:

- `Tool.requires_confirmation` flag. Confirmed tools are **never
  executed inside the LLM loop** — `tools.execute_tool` persists an
  `AgentPendingAction` (`pending`, 24h TTL) and returns a
  `pending_confirmation` payload telling the model to ask the user.
- `POST /api/agents/actions/{id}/approve` runs the tool's real function
  under the **approver's** identity (`run_approved_action`); the tool's
  own membership/role checks still apply, so approval grants nothing
  the approver lacks. Result or error is stored on the action.
- `POST .../reject` marks `rejected`; expired pending actions →
  `410 Gone` and flip to `expired`. Actions are owner-private like
  conversations; non-pending approval → `409`.
- First write tool: `invite_org_member` (admin/owner only, grants only
  `editor`/`viewer` — agents can't escalate privileges). The invitation
  token is never returned to the model.
- System prompt updated: the model must say an action is *pending*,
  never claim completion.

## Consequences

- The LLM can propose but never execute writes — the safety boundary is
  code, not prompt text.
- Approval is synchronous REST — no email/push notification yet; a UI
  surface for pending actions is the natural next slice.
- `AgentPendingAction` is audit-grade: who proposed, what args, who
  resolved, result/error — replayable.
- Deferred: multi-step saga writes, delegation (approver ≠ proposer is
  currently impossible since actions are owner-private), expiry sweep
  job (expiry is lazy — checked on approve/list).
