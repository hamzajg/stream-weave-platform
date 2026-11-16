# Backlog: workflow-definitions

Items are USER STORIES in the parseable format below — keep the heading
shape `## US<n> — <story>` and the field lines intact so `wave_plan` can
parse them. Write the story as: "As a <role>, I want <goal>, so that
<value>" — the title after the dash IS the story.

```
## US<n> — As a <role>, I want <goal>, so that <value>
- Scenarios: @w1, @w2
- Depends: US1, US3        (optional; omit for wave-1 items)
- Size: S|M|L
- Notes: <one line>
```

Order stories by user value; dependencies express technical order only.

## US1 — As an editor, I want to create a named workflow in my organization, so that my team has one shared place to start building
- Scenarios: @w1
- Size: M
- Notes: `workflows` + `workflow_versions` models, draft v1 on create, slug per org (D1, D5).

## US2 — As a member, I want to list and open my organization's workflows without seeing anyone else's, so that tenant data stays private
- Scenarios: @w1
- Size: S
- Notes: tenant-scoped queries; foreign id is 404 (D4).

## US3 — As an owner, I want roles enforced on workflow writes, so that viewers cannot change what the team runs
- Scenarios: @w1
- Size: S
- Notes: reuse OrganizationRole; editor+ writes, admin+ deletes.

## US4 — As an editor, I want to save the graph I drew, so that my work survives closing the browser
- Scenarios: @w2
- Size: M
- Notes: PUT /draft replaces the single draft version row (D2, D3).

## US5 — As an editor, I want the server to reject an incoherent graph with a reason, so that I cannot publish something that cannot run
- Scenarios: @w2
- Size: M
- Notes: pure validator in `app/utils/workflow_graph.py`, 422 naming the defect.

## US6 — As an editor, I want to publish a version, so that teammates and runs use a stable definition
- Scenarios: @w3
- Size: M
- Notes: publish flips status and opens the next draft (D2).

## US7 — As a viewer, I want to see version history, so that I can tell which definition is live and what changed
- Scenarios: @w3
- Size: S
- Notes: GET /versions ordered desc; published rows immutable.

## US8 — As an admin, I want to delete a workflow, so that abandoned experiments do not clutter the org
- Scenarios: @w3
- Depends: US2
- Size: S
- Notes: cascade versions; 404 afterwards.
