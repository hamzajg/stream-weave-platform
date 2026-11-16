# Validation — workflow-definitions

## Traceability

| AC | Criterion | Scenarios | Wave(s) | Test evidence |
|----|-----------|-----------|---------|---------------|
| 1 | An `editor` creates a workflow and receives a draft v1 with… | A viewer is read-only and an admin can delete, An editor creates a workflow, Another organization's workflow is invisible | 1 | test_workflows.py |
| 2 | A member lists only their own organization's workflows, and… | A viewer is read-only and an admin can delete, An editor creates a workflow, Another organization's workflow is invisible | 1 | test_workflows.py |
| 3 | A `viewer` can read but cannot create, update or delete… | A viewer is read-only and an admin can delete, An editor creates a workflow, Another organization's workflow is invisible | 1 | test_workflows.py |
| 4 | Replacing the draft graph with a valid definition persists… | A malformed graph is rejected, A valid draft graph is persisted, An edge to an undeclared node is rejected | 2 | test_workflows.py |
| 5 | A draft whose edges reference an undeclared node is… | A malformed graph is rejected, A valid draft graph is persisted, An edge to an undeclared node is rejected | 2 | test_workflows.py |
| 6 | A draft with duplicate node ids, no `trigger` node, two… | A malformed graph is rejected, A valid draft graph is persisted, An edge to an undeclared node is rejected | 2 | test_workflows.py |
| 7 | Publishing freezes the current draft as a numbered… | A published snapshot never changes, An invalid draft cannot be published, Deleting a workflow removes its history, Publishing freezes a version and opens the next draft | 3 | test_workflows.py |
| 8 | A published version is immutable: replacing the draft after… | A published snapshot never changes, An invalid draft cannot be published, Deleting a workflow removes its history, Publishing freezes a version and opens the next draft | 3 | test_workflows.py |
| 9 | Deleting a workflow removes it from the list and from… | A published snapshot never changes, An invalid draft cannot be published, Deleting a workflow removes its history, Publishing freezes a version and opens the next draft | 3 | test_workflows.py |
| 10 | Publishing an invalid or empty draft is rejected with… | A published snapshot never changes, An invalid draft cannot be published, Deleting a workflow removes its history, Publishing freezes a version and opens the next draft | 3 | test_workflows.py |

## Scenario coverage

- Scenarios: 10 total, 10 with detected test evidence, 0 without
- ✓ `An editor creates a workflow` (@w1)
- ✓ `Another organization's workflow is invisible` (@w1)
- ✓ `A viewer is read-only and an admin can delete` (@w1)
- ✓ `A valid draft graph is persisted` (@w2)
- ✓ `An edge to an undeclared node is rejected` (@w2)
- ✓ `A malformed graph is rejected` (@w2)
- ✓ `Publishing freezes a version and opens the next draft` (@w3)
- ✓ `A published snapshot never changes` (@w3)
- ✓ `An invalid draft cannot be published` (@w3)
- ✓ `Deleting a workflow removes its history` (@w3)

## Demo script (walked 2026-11-16)

Environment: `DATABASE_URL=sqlite:////tmp/demo-sw.db .venv/bin/python -m uvicorn
app.main:app --port 8123`, driver `scripts/demo_workflows_api.py` (real HTTP, no
test client). Observed, not asserted:

| Step | Request | Observed |
|---|---|---|
| register + login an owner | `POST /api/auth/register`, `/login` | `201`, `200` (token) |
| create organization | `POST /api/orgs` | `201`, slug `acme-corp` |
| **An editor creates a workflow** | `POST /api/workflows` | `201`, `slug=invoice-triage`, `draft_version=1`, `published_version=null` |
| **A valid draft graph is persisted** | `PUT /api/workflows/{id}/draft` (trigger→agent→action) | `200`, version 1 draft, 3 nodes / 2 edges echoed back |
| **An edge to an undeclared node is rejected** | same path, edge target `ghost` | `422` `"edge 0 target 'ghost' does not match any declared node"` |
| **Publishing freezes a version** | `POST /api/workflows/{id}/publish` | `200`, version 1 `published`; `GET /{id}` now reports `draft_version=2` |
| **A published snapshot never changes** | `PUT /api/workflows/{id}/draft` with one edge removed | `200` on v2; history shows v1 = 3 nodes / **2** edges, v2 = 3 nodes / **1** edge |
| **A viewer is read-only** | viewer invited via `POST /api/orgs/{id}/invite` + `POST /api/orgs/invitations/accept` | `GET /{id}` → `200`; `POST /publish` → `403` |
| **Another organization's workflow is invisible** | outsider in `Globex` | `GET /{id}` → `404`; `GET /api/workflows` → `200 []` |
| **Deleting a workflow removes its history** | `DELETE /api/workflows/{id}` as admin | `204`; `GET /{id}` and `GET /{id}/versions` → `404` |

Server log confirmed each call; the demo process was stopped and port 8123
refused connections afterwards (`curl` exit 7).

## Gaps

- none — spec is fully traced; all 10 scenarios have named test evidence
- Deliberately out of scope (SPEC.md → Scope out): executing a workflow, and
  wiring the ReactFlow builder to these endpoints. Both are follow-up features,
  not gaps in this one.

Note: 'no evidence' means neither the scenario name nor a
token match was found in test files — verify by hand before
treating it as a real gap. '~' marks weak token-match evidence.