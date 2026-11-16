# Waves — workflow-definitions

Each wave IS an iteration: a time-boxed, independently shippable
increment — one branch, one PR, green tests, demoable outcome.
Do not start wave N+1 until wave N merges.

## Wave 1 — iteration 1

Scenarios proven by this wave:
- An editor creates a workflow
- Another organization's workflow is invisible
- A viewer is read-only and an admin can delete

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US1 | As an editor, I want to create a named workflow in my organization, so that my team has one shared place to start building | M | — | `workflows` + `workflow_versions` models, draft v1 on create, slug per org (D1, D5). |
| US2 | As a member, I want to list and open my organization's workflows without seeing anyone else's, so that tenant data stays private | S | — | tenant-scoped queries; foreign id is 404 (D4). |
| US3 | As an owner, I want roles enforced on workflow writes, so that viewers cannot change what the team runs | S | — | reuse OrganizationRole; editor+ writes, admin+ deletes. |

## Wave 2 — iteration 2

Scenarios proven by this wave:
- A valid draft graph is persisted
- An edge to an undeclared node is rejected
- A malformed graph is rejected

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US4 | As an editor, I want to save the graph I drew, so that my work survives closing the browser | M | — | PUT /draft replaces the single draft version row (D2, D3). |
| US5 | As an editor, I want the server to reject an incoherent graph with a reason, so that I cannot publish something that cannot run | M | — | pure validator in `app/utils/workflow_graph.py`, 422 naming the defect. |

## Wave 3 — iteration 3

Scenarios proven by this wave:
- Publishing freezes a version and opens the next draft
- A published snapshot never changes
- Deleting a workflow removes its history

| Item | Title | Size | Deps | Notes |
|------|-------|------|------|-------|
| US6 | As an editor, I want to publish a version, so that teammates and runs use a stable definition | M | — | publish flips status and opens the next draft (D2). |
| US7 | As a viewer, I want to see version history, so that I can tell which definition is live and what changed | S | — | GET /versions ordered desc; published rows immutable. |
| US8 | As an admin, I want to delete a workflow, so that abandoned experiments do not clutter the org | S | US2 | cascade versions; 404 afterwards. |
