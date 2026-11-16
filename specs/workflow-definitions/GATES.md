# Gates: workflow-definitions

> Preconditions for phase transitions. Each `## G<n> — <title>` block is a
> gate. `ship_loop` refuses to advance past a phase while a blocking gate is
> pending. Definitions live here; status and evidence live in `LOOP.md`.
>
> Gate phases: `spec` (before writing the spec), `plan` (before planning
> waves), `wave:<n>` (before starting wave n), `validate` (before validation),
> `finish` (before closing the feature).
>
> Gate types: decision | artifact | external | technical | quality | data.
> Resolver: `human` (needs a person to decide/provide something) or `agent`
> (the agent can satisfy it). Check: `manual`, `file:<repo-relative-path>`, or
> `command:<exact command>` (the agent runs it and records the output as
> evidence — the oracle never executes it).

## G1 — Workflow definition contract frozen
- Before: plan
- Type: decision
- Owner: tech-lead
- Resolver: agent
- Blocking: yes
- Check: manual
- Why: every wave writes against the same graph shape and status codes;
  D1–D6 in SPEC.md fix `{nodes, edges}`, draft/published semantics, 404-vs-403
  ordering and slug rules before wave 1 starts.

## G2 — Existing backend suite still green
- Before: wave:2
- Type: technical
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: command:python -m pytest -q
- Why: wave 1 adds models to the shared `Base` metadata; auth, orgs and agent
  tests must still pass before the graph layer builds on top.

## G3 — Publishing and tenant isolation are covered by tests
- Before: validate
- Type: quality
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: command:python -m pytest -q tests/test_workflows.py
- Why: AC-7, AC-8 and the 404-not-403 rule are the security- and
  correctness-critical paths; they must be asserted by committed tests, not
  observed by hand.

## G4 — Frontend and deployment untouched
- Before: finish
- Type: artifact
- Owner: agent
- Resolver: agent
- Blocking: yes
- Check: command:git diff --name-only origin/main...HEAD
- Why: this feature is backend-only (Scope out). A diff that reaches into
  `webapp/`, `Dockerfile` or compose means scope crept; the verifier must
  confirm the changed paths stay under `app/`, `tests/` and `specs/`.
