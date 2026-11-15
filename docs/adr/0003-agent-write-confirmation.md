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
  `410 Gone` and flip to `expired`. Non-pending approval → `409`.
- **Delegated confirmation:** actions are visible to their proposer and
  to OWNER/ADMIN members of the action's org — an admin can approve or
  reject a proposal made by another member (execution still runs under
  the approver's identity, so the tool's role checks gate it). Others
  get `404`, same as a missing action. `resolved_by` records who
  resolved it.
- **Proposal-time authorization:** confirmed tools may declare an
  `authorize` pre-flight check run before the pending row is created
  (`invite_org_member` requires admin/owner + valid args). Rejected
  proposals return an error to the model — no action is persisted.
  State checks that can change by approval time (duplicate member,
  pending invitation) stay in the tool function and re-run on approve.
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
  resolved (`resolved_by`), result/error — replayable.
- Deferred: multi-step saga writes, expiry sweep job (expiry is lazy —
  checked on approve), notification when a delegated action awaits an
  admin, and finer-grained delegation (e.g. per-tool approver roles).
