# Delivery Loop — workflow-definitions

Status: running
Iterations: 2
Updated: 2026-11-16T08:22:14Z

| Wave | Status | Branch | PR | Evidence | Updated |
|------|--------|--------|----|----------|---------|
| 1 | done | feat/workflow-definitions-w1 | #15 | pytest -q 41 passed (7 new workflow tests: create/draft v1, slug uniqueness, tenant 404, viewer 403, admin delete); CI 4 | 2026-11-16T08:12:17Z |
| 2 | done | feat/workflow-definitions-w2 | #16 | pytest -q 49 passed (8 new draft+validator tests incl. 422 naming ghost edge, duplicate ids, trigger count, unknown type | 2026-11-16T08:20:11Z |
| 3 | in-progress | feat/workflow-definitions-w3 | — | — | 2026-11-16T08:22:14Z |

## Gates

| Gate | Status | Evidence | Updated |
|------|--------|----------|---------|
| G1 | met | specs/workflow-definitions/SPEC.md Decisions D1-D6 (tables, insert-only versions, {nodes,edges} shape, 404-before-403, s | 2026-11-16T07:59:27Z |
| G2 | met | python -m pytest -q on merged main 3ed99af -> 41 passed, 0 failed | 2026-11-16T08:12:18Z |
| G3 | pending | — | — |
| G4 | pending | — | — |

## Events

- 2026-11-16T07:59:27Z gate G1 met: specs/workflow-definitions/SPEC.md Decisions D1-D6 (tables, insert-only versions, {nodes,edges} shape, 404-before-403, s
- 2026-11-16T08:01:01Z start wave 1 on feat/workflow-definitions-w1
- 2026-11-16T08:12:17Z complete wave 1 (#15): pytest -q 41 passed (7 new workflow tests: create/draft v1, slug uniqueness, tenant 404, viewer 403, admin delete); CI 4
- 2026-11-16T08:12:18Z gate G2 met: python -m pytest -q on merged main 3ed99af -> 41 passed, 0 failed
- 2026-11-16T08:13:03Z start wave 2 on feat/workflow-definitions-w2
- 2026-11-16T08:20:11Z complete wave 2 (#16): pytest -q 49 passed (8 new draft+validator tests incl. 422 naming ghost edge, duplicate ids, trigger count, unknown type
- 2026-11-16T08:22:14Z start wave 3 on feat/workflow-definitions-w3
