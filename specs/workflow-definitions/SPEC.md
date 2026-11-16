# Spec: workflow-definitions

> Spec-driven development artifact. This file is the contract: implementation
> is done when every acceptance criterion maps to a scenario in
> `EXAMPLES.feature` and every scenario has a passing check.

## Problem

StreamWeave's pitch is that a business specialist builds an agentic workflow
visually and a team runs it. Today the platform has auth, organizations,
onboarding, dashboards and the agent chat runtime — but no workflow at all:
`GET /api/workflows/*` does not exist, the ReactFlow builder has nowhere to
save to, and a team cannot hand a workflow to a colleague because the definition
only lives in one browser tab. Every downstream capability (execution, run
history, per-workflow agents) is blocked on a persisted, validated, versioned
workflow definition.

## Users

- **Editor** — a business specialist in an organization who builds and publishes
  a workflow graph.
- **Viewer** — a colleague or auditor who needs to read the current definition
  and its version history without changing it.
- **Owner/Admin** — must be able to delete a workflow; is the escalation path
  when an editor leaves.

## Scope (in)

- `Workflow` (tenant-scoped container: name, slug, description, owner) and
  `WorkflowVersion` (an immutable, numbered graph snapshot with `draft` /
  `published` state) persisted with the existing SQLAlchemy models.
- REST API under `/api/workflows`: create (draft v1), list, fetch, rename,
  replace the draft graph, publish, list versions, delete.
- Server-side graph validation: unique node ids, edges resolve to declared
  nodes, exactly one `trigger` node, known node types. Validation failures are
  `422` with the offending node/edge named.
- Membership-scoped authorization reusing the existing org roles: readers need
  any membership, authors need `editor`/`admin`/`owner`, delete needs
  `admin`/`owner`. A workflow belonging to another org is a `404`, never a
  `403` (no tenant enumeration).
- Publishing is one-way for a version: a published snapshot can never be
  mutated, and publishing again produces a new draft.

## Scope (out)

- Executing a workflow (the `runs` / actor-system feature).
- The ReactFlow builder UI wiring (follow-up; this spec stops at the API).
- Per-node credentials, scheduling and triggers beyond the declaration.
- Workflow sharing/transfer between organizations.

## Acceptance criteria

| # | Criterion | Scenario(s) |
|---|-----------|-------------|
| 1 | An `editor` creates a workflow and receives a draft v1 with a slug derived from the name, scoped to their organization | @w1 |
| 2 | A member lists only their own organization's workflows, and fetching another organization's workflow by id returns `404` | @w1 |
| 3 | A `viewer` can read but cannot create, update or delete (`403`), while `admin`/`owner` can delete | @w1 |
| 4 | Replacing the draft graph with a valid definition persists exactly the submitted nodes and edges | @w2 |
| 5 | A draft whose edges reference an undeclared node is rejected with `422` naming the bad edge, and the stored draft is unchanged | @w2 |
| 6 | A draft with duplicate node ids, no `trigger` node, two `trigger` nodes, or an unknown node type is rejected with `422` | @w2 |
| 7 | Publishing freezes the current draft as a numbered published version and starts a new editable draft | @w3 |
| 8 | A published version is immutable: replacing the draft after publish does not alter the published snapshot, and version history lists both | @w3 |
| 9 | Deleting a workflow removes it from the list and from version history lookups (`404` afterwards) | @w3 |
| 10 | Publishing an invalid or empty draft is rejected with `422`, leaving the workflow unpublished and still editable | @w3 |

## Decisions

- **D1 — Two tables, not one JSON blob on `workflows`.** `workflows` holds
  identity (name/slug/owner), `workflow_versions` holds numbered immutable
  graphs. Publishing is therefore a status flip on a row, not a destructive
  update, and history is a query. Chosen over a single `definition` column
  because AC-8 (immutability + history) is impossible to satisfy honestly
  without row-per-version.
- **D2 — Version rows are insert-only.** `PUT /draft` mutates the row whose
  `status == draft`; `publish` flips that row to `published` and eagerly
  creates the next `draft` row at `version + 1`. No UPDATE ever touches a
  published row, so immutability is enforced by the write path, not by trust.
- **D3 — Definition shape is `{nodes: [...], edges: [...]}`, validated in
  `app/utils/workflow_graph.py`.** Node: `id`, `type` in
  `trigger|agent|condition|action`, `label`, optional `config` object. Edge:
  `source`, `target`. Validation is a pure function returning a list of
  problems, so it is unit-testable without HTTP and reusable by the builder's
  preview endpoint later.
- **D4 — Tenant check first, role check second.** Every route resolves the
  workflow *within the caller's organizations* and returns `404` when it is
  not there; only then does the role check produce `403`. This prevents an
  outsider from learning that an id exists.
- **D5 — `slug` is unique per organization**, derived from the name and
  suffixed (`-2`, `-3`, …) on collision; it is stable after creation so links
  and future run URLs do not break on rename.
- **D6 — Scope deliberately stops at the API.** No execution, no UI wiring;
  AC-1..10 are all reachable with `pytest` against the in-memory SQLite
  fixture, which is what makes every gate in `GATES.md` agent-resolvable.
- **D7 — Publish validates, then clones.** Publishing runs the same validator
  over the stored draft (an empty draft has no trigger and is refused with
  `422`), flips that row to `published`, and inserts the next draft as a copy
  of the graph just published. Editors therefore start from what is live rather
  than from nothing, and the live definition is never one that cannot run.
