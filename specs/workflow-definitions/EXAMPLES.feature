# workflow-definitions — specifications by example
# Scenario tags @w<N> map items to delivery waves (see WAVES.md / BACKLOG.md).

Feature: Workflow definitions

  Background:
    Given an organization "Acme Corp" where a user is a member

  @w1 @happy-path
  Scenario: An editor creates a workflow
    Given I am an editor of "Acme Corp"
    When I POST /api/workflows with name "Invoice Triage" and a description
    Then the response is 201 with version 1 and status "draft"
    And the workflow slug is "invoice-triage"
    And GET /api/workflows lists it for every member of "Acme Corp"

  @w1 @multi-tenant
  Scenario: Another organization's workflow is invisible
    Given a workflow "Invoice Triage" in organization "Acme Corp"
    And I am a member of organization "Globex"
    When I GET /api/workflows/{id} for that workflow
    Then the response is 404
    And GET /api/workflows for me does not contain it

  @w1 @authorization
  Scenario: A viewer is read-only and an admin can delete
    Given I am a viewer of "Acme Corp"
    When I POST, PATCH or DELETE a workflow
    Then every response is 403
    And GET /api/workflows still returns 200
    Given I am an admin of "Acme Corp"
    When I DELETE the workflow
    Then the response is 204

  @w2 @graph
  Scenario: A valid draft graph is persisted
    Given a workflow in "Acme Corp" whose draft is empty
    When I PUT /api/workflows/{id}/draft with a trigger, an agent and an action node connected in a chain
    Then the response is 200
    And GET /api/workflows/{id} returns exactly those 3 nodes and 2 edges

  @w2 @validation
  Scenario: An edge to an undeclared node is rejected
    Given a workflow in "Acme Corp"
    When I PUT /api/workflows/{id}/draft where an edge targets "ghost"
    Then the response is 422 and the message names "ghost"
    And GET /api/workflows/{id} still returns the previous draft

  @w2 @validation
  Scenario Outline: A malformed graph is rejected
    Given a workflow in "Acme Corp"
    When I PUT /api/workflows/{id}/draft with <defect>
    Then the response is 422 and the message mentions "<reason>"

    Examples:
      | defect                              | reason           |
      | two nodes with the same id          | duplicate node   |
      | no trigger node                     | trigger          |
      | two trigger nodes                   | trigger          |
      | a node of type "teleport"           | unknown type     |

  @w3 @publish
  Scenario: Publishing freezes a version and opens the next draft
    Given a workflow in "Acme Corp" with a valid draft at version 1
    When I POST /api/workflows/{id}/publish
    Then the response is 200 with version 1 status "published"
    And GET /api/workflows/{id} reports a new editable draft at version 2
    And GET /api/workflows/{id}/versions lists version 1 as "published"

  @w3 @immutability
  Scenario: A published snapshot never changes
    Given a workflow whose version 1 is published
    When I PUT /api/workflows/{id}/draft with a different graph
    Then version 1 as returned by GET /api/workflows/{id}/versions keeps its original nodes
    And the draft at version 2 contains the new graph

  @w3 @delete
  Scenario: Deleting a workflow removes its history
    Given a workflow in "Acme Corp" with a published version
    When an admin DELETE the workflow
    Then GET /api/workflows/{id} is 404
    And GET /api/workflows/{id}/versions is 404
