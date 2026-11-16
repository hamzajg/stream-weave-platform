"""Confirmation-gated workflow writes: propose in the loop, approve out of it.

`create_workflow` and `replace_workflow_draft` follow the `invite_org_member`
pattern — `requires_confirmation=True`, an `authorize` pre-flight that runs when
the model proposes, and execution only from the approve endpoint under the
approver's identity.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import llm, tools
from app.database import Base, get_db
from app.main import app
from app.models import OrganizationMember, OrganizationRole, User

PASSWORD = "correct-horse-123"

GRAPH = {
    "nodes": [
        {"id": "t1", "type": "trigger", "label": "New invoice"},
        {"id": "a1", "type": "agent", "label": "Classify"},
    ],
    "edges": [{"source": "t1", "target": "a1"}],
}

# An edge pointing at a node that does not exist: invalid by validate_definition.
BROKEN_GRAPH = {
    "nodes": [{"id": "t1", "type": "trigger", "label": "New invoice"}],
    "edges": [{"source": "t1", "target": "ghost"}],
}


@pytest.fixture()
def api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, Session
    app.dependency_overrides.clear()


def _register(client, email=None):
    email = email or f"user-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return email


def _login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_org(client, token, name="Acme Corp"):
    response = client.post(
        "/api/orgs",
        json={"name": name, "industry": "manufacturing", "size": "11-50"},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_workflow(client, token, org, name="Invoice Triage", graph=GRAPH):
    response = client.post(
        "/api/workflows",
        json={"organization_id": org["id"], "name": name},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    workflow = response.json()
    draft = client.put(
        f"/api/workflows/{workflow['id']}/draft", json=graph, headers=_auth(token)
    )
    assert draft.status_code == 200, draft.text
    return client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token)).json()


def _owner(client, workflow_names=("Invoice Triage",)):
    email = _register(client)
    token = _login(client, email)
    org = _create_org(client, token)
    workflows = [
        _create_workflow(client, token, org, name) for name in workflow_names
    ]
    return email, token, org, workflows


def _add_member(client, owner_token, org_id, role="viewer", email=None):
    """Register + invite + accept a member with `role`; returns (email, token)."""
    email = email or f"member-{uuid.uuid4().hex}@example.com"
    _register(client, email)
    invite = client.post(
        f"/api/orgs/{org_id}/invite",
        json={"email": email, "role": role},
        headers=_auth(owner_token),
    )
    assert invite.status_code == 200, invite.text
    token = _login(client, email)
    accept = client.post(
        "/api/orgs/invitations/accept",
        json={"token": invite.json()["token"]},
        headers=_auth(token),
    )
    assert accept.status_code == 200, accept.text
    return email, token


def _set_role(Session, org_id, email, role):
    db = Session()
    try:
        user = db.query(User).filter(User.email == email).one()
        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == uuid.UUID(org_id),
                OrganizationMember.user_id == user.id,
            )
            .one()
        )
        member.role = OrganizationRole(role)
        db.commit()
    finally:
        db.close()


class FakeLLM:
    """Replays queued assistant messages in place of a real model."""

    def __init__(self, responses):
        self.responses = list(responses)

    async def __call__(self, messages, tools=None):
        return self.responses.pop(0)


def _tool_call(call_id, name, arguments):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        }],
    }


def _propose(client, monkeypatch, token, org_id, name, arguments):
    """Drive one agent turn that calls `name`; returns (action id or None, tool result).

    The turn always ends with a plain assistant message so the loop is finite.
    """
    conversation = client.post(
        "/api/agents/conversations",
        json={"organization_id": org_id},
        headers=_auth(token),
    ).json()
    fake = FakeLLM([
        _tool_call("call_1", name, arguments),
        {"role": "assistant", "content": "Awaiting your approval."},
    ])
    monkeypatch.setattr(llm, "chat_completion", fake)

    response = client.post(
        f"/api/agents/conversations/{conversation['id']}/messages",
        json={"content": "please"},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    tool_message = [m for m in response.json()["messages"] if m["role"] == "tool"][0]

    actions = client.get("/api/agents/actions", headers=_auth(token)).json()
    pending = [a for a in actions if a["status"] == "pending"]
    return (pending[0]["id"] if pending else None), tool_message["content"]


def _workflow_names(client, token, org_id):
    listed = client.get(
        f"/api/workflows?organization_id={org_id}", headers=_auth(token)
    )
    assert listed.status_code == 200, listed.text
    return [w["name"] for w in listed.json()]


def _approve(client, token, action_id):
    return client.post(f"/api/agents/actions/{action_id}/approve", headers=_auth(token))


# ------------------------------------------------------------------- registry

def test_write_tools_require_confirmation():
    for name in ("create_workflow", "replace_workflow_draft"):
        tool = tools.get_tool(name)
        assert tool is not None, name
        assert tool.requires_confirmation is True
        assert tool.authorize is not None
        assert "CONFIRMATION" in tool.description


def test_tools_endpoint_lists_write_tools(api):
    client, _ = api
    _, token, _, _ = _owner(client)

    response = client.get("/api/agents/tools", headers=_auth(token))

    names = {t["name"] for t in response.json()}
    assert {"create_workflow", "replace_workflow_draft"} <= names


# ----------------------------------------------------------- create: propose

def test_create_is_only_a_proposal_until_approved(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "create_workflow",
        json.dumps({
            "name": "Invoice Triage",
            "description": "Route invoices",
            "definition": GRAPH,
        }),
    )

    assert action_id is not None
    assert "pending_confirmation" in tool_result
    assert _workflow_names(client, token, org["id"]) == []

    approved = _approve(client, token, action_id)

    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "executed"
    assert body["result"]["name"] == "Invoice Triage"
    assert body["result"]["slug"] == "invoice-triage"
    assert body["result"]["draft_version"] == 1
    assert body["result"]["definition"] == GRAPH
    assert _workflow_names(client, token, org["id"]) == ["Invoice Triage"]


def test_create_without_a_graph_starts_empty(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "create_workflow", '{"name": "Empty"}'
    )
    approved = _approve(client, token, action_id)

    assert approved.json()["status"] == "executed"
    workflow = client.get(
        f"/api/workflows?organization_id={org['id']}", headers=_auth(token)
    ).json()[0]
    assert workflow["definition"] == {"nodes": [], "edges": []}


def test_rejecting_a_create_writes_nothing(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "create_workflow", '{"name": "Never"}'
    )
    rejected = client.post(
        f"/api/agents/actions/{action_id}/reject", headers=_auth(token)
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert _workflow_names(client, token, org["id"]) == []


def test_create_rejects_a_missing_name_at_proposal_time(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "create_workflow", '{"name": "   "}'
    )

    assert action_id is None
    assert "A workflow name is required" in tool_result


def test_create_rejects_an_incoherent_graph_at_proposal_time(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "create_workflow",
        '{"name": "Broken", "definition": ' + json.dumps(BROKEN_GRAPH) + "}",
    )

    assert action_id is None
    assert "Invalid workflow graph" in tool_result
    assert "does not match any declared node" in tool_result
    assert _workflow_names(client, token, org["id"]) == []


def test_agent_create_gets_a_unique_slug(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=("Invoice Triage",))

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "create_workflow",
        '{"name": "Invoice Triage"}',
    )
    approved = _approve(client, token, action_id)

    assert approved.json()["result"]["slug"] == "invoice-triage-2"


# ---------------------------------------------------------- create: roles

def test_viewer_cannot_propose_a_create(api, monkeypatch):
    client, _ = api
    _, owner_token, org, _ = _owner(client, workflow_names=())
    _, viewer_token = _add_member(client, owner_token, org["id"], "viewer")

    action_id, tool_result = _propose(
        client, monkeypatch, viewer_token, org["id"], "create_workflow",
        '{"name": "Sneaky"}',
    )

    assert action_id is None
    assert "Insufficient permissions" in tool_result
    assert _workflow_names(client, owner_token, org["id"]) == []


def test_editor_can_propose_and_approve_a_create(api, monkeypatch):
    client, _ = api
    _, owner_token, org, _ = _owner(client, workflow_names=())
    _, editor_token = _add_member(client, owner_token, org["id"], "editor")

    action_id, _ = _propose(
        client, monkeypatch, editor_token, org["id"], "create_workflow",
        '{"name": "Editor Flow"}',
    )
    approved = _approve(client, editor_token, action_id)

    assert approved.json()["status"] == "executed"
    assert _workflow_names(client, owner_token, org["id"]) == ["Editor Flow"]


def test_owner_can_approve_a_members_create(api, monkeypatch):
    client, _ = api
    _, owner_token, org, _ = _owner(client, workflow_names=())
    _, editor_token = _add_member(client, owner_token, org["id"], "editor")

    action_id, _ = _propose(
        client, monkeypatch, editor_token, org["id"], "create_workflow",
        '{"name": "Delegated Flow"}',
    )
    approved = _approve(client, owner_token, action_id)

    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"
    assert _workflow_names(client, owner_token, org["id"]) == ["Delegated Flow"]


# ----------------------------------------------------- replace draft: path

NEW_GRAPH = {
    "nodes": [
        {"id": "t1", "type": "trigger", "label": "New invoice"},
        {"id": "c1", "type": "condition", "label": "Amount > 1000"},
    ],
    "edges": [],
}


def test_replace_draft_waits_for_approval(api, monkeypatch):
    client, _ = api
    _, token, org, workflows = _owner(client)

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"slug": "invoice-triage", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )

    assert action_id is not None
    assert "pending_confirmation" in tool_result
    before = client.get(
        f"/api/workflows/{workflows[0]['id']}", headers=_auth(token)
    ).json()
    assert before["definition"] == GRAPH

    approved = _approve(client, token, action_id)

    assert approved.json()["status"] == "executed"
    after = client.get(
        f"/api/workflows/{workflows[0]['id']}", headers=_auth(token)
    ).json()
    assert after["definition"] == NEW_GRAPH
    assert after["draft_version"] == before["draft_version"]


def test_replace_draft_by_id(api, monkeypatch):
    client, _ = api
    _, token, org, workflows = _owner(client)

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"workflow_id": "' + workflows[0]["id"] + '", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )
    approved = _approve(client, token, action_id)

    assert approved.json()["status"] == "executed"
    assert approved.json()["result"]["definition"] == NEW_GRAPH


def test_replace_draft_rejects_an_incoherent_graph_at_proposal_time(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client)

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"slug": "invoice-triage", "definition": '
        + json.dumps(BROKEN_GRAPH) + "}",
    )

    assert action_id is None
    assert "Invalid workflow graph" in tool_result


def test_replace_draft_requires_a_definition(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client)

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"slug": "invoice-triage"}',
    )

    assert action_id is None
    assert "definition with nodes and edges is required" in tool_result


def test_replace_draft_does_not_reach_another_organization(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client)

    other_email = _register(client)
    other_token = _login(client, other_email)
    other_org = _create_org(client, other_token, "Globex")
    foreign = _create_workflow(client, other_token, other_org, "Secret Flows")

    action_id, tool_result = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"workflow_id": "' + foreign["id"] + '", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )

    assert action_id is None
    assert "Workflow not found" in tool_result
    untouched = client.get(
        f"/api/workflows/{foreign['id']}", headers=_auth(other_token)
    ).json()
    assert untouched["definition"] == GRAPH


def test_viewer_cannot_propose_a_draft_replacement(api, monkeypatch):
    client, _ = api
    _, owner_token, org, workflows = _owner(client)
    _, viewer_token = _add_member(client, owner_token, org["id"], "viewer")

    action_id, tool_result = _propose(
        client, monkeypatch, viewer_token, org["id"], "replace_workflow_draft",
        '{"workflow_id": "' + workflows[0]["id"] + '", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )

    assert action_id is None
    assert "Insufficient permissions" in tool_result


# ----------------------------------------------- approval-time re-checks

def test_approval_rechecks_the_approvers_role(api, monkeypatch):
    client, Session = api
    _, owner_token, org, workflows = _owner(client)
    editor_email, editor_token = _add_member(
        client, owner_token, org["id"], "editor"
    )

    action_id, _ = _propose(
        client, monkeypatch, editor_token, org["id"], "replace_workflow_draft",
        '{"workflow_id": "' + workflows[0]["id"] + '", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )
    # Demoted after proposing: the approval must not inherit old rights.
    _set_role(Session, org["id"], editor_email, "viewer")

    approved = _approve(client, editor_token, action_id)

    assert approved.json()["status"] == "failed"
    assert approved.json()["error"] == "Insufficient permissions"
    unchanged = client.get(
        f"/api/workflows/{workflows[0]['id']}", headers=_auth(owner_token)
    ).json()
    assert unchanged["definition"] == GRAPH


def test_approval_fails_loudly_when_the_workflow_vanished(api, monkeypatch):
    client, _ = api
    _, token, org, workflows = _owner(client)

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "replace_workflow_draft",
        '{"workflow_id": "' + workflows[0]["id"] + '", "definition": '
        + json.dumps(NEW_GRAPH) + "}",
    )
    deleted = client.delete(
        f"/api/workflows/{workflows[0]['id']}", headers=_auth(token)
    )
    assert deleted.status_code == 204, deleted.text

    approved = _approve(client, token, action_id)

    assert approved.json()["status"] == "failed"
    assert approved.json()["error"] == "Workflow not found"


def test_a_proposal_cannot_be_approved_twice(api, monkeypatch):
    client, _ = api
    _, token, org, _ = _owner(client, workflow_names=())

    action_id, _ = _propose(
        client, monkeypatch, token, org["id"], "create_workflow", '{"name": "Once"}'
    )
    first = _approve(client, token, action_id)
    second = _approve(client, token, action_id)

    assert first.json()["status"] == "executed"
    assert second.status_code == 409
    assert _workflow_names(client, token, org["id"]) == ["Once"]
