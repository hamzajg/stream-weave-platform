"""Read-only workflow tools in the agent registry.

`list_workflows` / `get_workflow` let the agent answer questions about the
organization's workflow definitions. They are read tools: no confirmation, no
pending action, no write path — and they are scoped to the conversation's
organization exactly like the API is.
"""

import uuid
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import llm, tools
from app.database import Base, get_db
from app.main import app
from app.models import AgentPendingAction, User

PASSWORD = "correct-horse-123"

GRAPH = {
    "nodes": [
        {"id": "t1", "type": "trigger", "label": "New invoice"},
        {"id": "a1", "type": "agent", "label": "Classify", "config": {"model": "small"}},
    ],
    "edges": [{"source": "t1", "target": "a1"}],
}


@pytest.fixture()
def api():
    """TestClient plus a session factory (for asserting on pending actions)."""
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


def _create_workflow(client, token, org, name="Invoice Triage", graph=None):
    response = client.post(
        "/api/workflows",
        json={"organization_id": org["id"], "name": name},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    workflow = response.json()
    if graph is not None:
        draft = client.put(
            f"/api/workflows/{workflow['id']}/draft", json=graph, headers=_auth(token)
        )
        assert draft.status_code == 200, draft.text
        workflow = client.get(
            f"/api/workflows/{workflow['id']}", headers=_auth(token)
        ).json()
    return workflow


def _owner(client, org_name="Acme Corp", workflow_names=("Invoice Triage",), graph=GRAPH):
    """A user owning a fresh org with the named workflows; returns (email, org, workflows)."""
    email = _register(client)
    token = _login(client, email)
    org = _create_org(client, token, org_name)
    workflows = [
        _create_workflow(client, token, org, name, graph) for name in workflow_names
    ]
    return email, org, workflows


def _run(Session, email, org, name, args):
    """Execute a tool as `email` acting in `org` — the agent's own call path."""
    db = Session()
    try:
        user = db.query(User).filter(User.email == email).one()
        return tools.execute_tool(db, user, UUID(org["id"]), name, args)
    finally:
        db.close()


# ------------------------------------------------------------------- registry

def test_read_only_workflow_tools_are_registered():
    for name in ("list_workflows", "get_workflow"):
        tool = tools.get_tool(name)
        assert tool is not None, name
        assert tool.requires_confirmation is False
        assert tool.authorize is None
        assert tool.spec()["function"]["name"] == name


def test_tools_endpoint_lists_workflow_tools(api):
    client, _ = api
    email, _, _ = _owner(client)

    response = client.get("/api/agents/tools", headers=_auth(_login(client, email)))

    assert response.status_code == 200
    assert {"list_workflows", "get_workflow"} <= {t["name"] for t in response.json()}


# -------------------------------------------------------------------- listing

def test_list_workflows_scopes_to_the_organization(api):
    client, Session = api
    email, org, _ = _owner(client, workflow_names=("Invoice Triage", "Onboarding"))

    other_email = _register(client)
    other_org = _create_org(client, _login(client, other_email), "Globex")
    _create_workflow(client, _login(client, other_email), other_org, "Globex Only")

    result = _run(Session, email, org, "list_workflows", {})

    assert result["ok"] is True, result
    names = [w["name"] for w in result["result"]["workflows"]]
    assert sorted(names) == ["Invoice Triage", "Onboarding"]
    assert result["result"]["organization"]["name"] == "Acme Corp"


def test_list_workflows_reports_graph_size_and_versions(api):
    client, Session = api
    email, org, workflows = _owner(client)

    result = _run(Session, email, org, "list_workflows", {})

    summary = result["result"]["workflows"][0]
    assert summary["id"] == workflows[0]["id"]
    assert summary["slug"] == "invoice-triage"
    assert summary["draft_version"] == 1
    assert summary["published_version"] is None
    assert summary["node_count"] == 2
    assert summary["edge_count"] == 1


def test_list_workflows_query_matches_name_or_slug(api):
    client, Session = api
    email, org, _ = _owner(client, workflow_names=("Invoice Triage", "Onboarding"))

    by_name = _run(Session, email, org, "list_workflows", {"query": "INVOICE"})
    by_slug = _run(Session, email, org, "list_workflows", {"query": "onboard"})

    assert [w["name"] for w in by_name["result"]["workflows"]] == ["Invoice Triage"]
    assert [w["name"] for w in by_slug["result"]["workflows"]] == ["Onboarding"]


def test_list_workflows_on_an_empty_organization(api):
    client, Session = api
    email, org, _ = _owner(client, workflow_names=())

    result = _run(Session, email, org, "list_workflows", {})

    assert result["ok"] is True
    assert result["result"]["workflows"] == []


# ---------------------------------------------------------------------- fetch

def test_get_workflow_returns_the_draft_graph(api):
    client, Session = api
    email, org, workflows = _owner(client)

    result = _run(
        Session, email, org, "get_workflow", {"workflow_id": workflows[0]["id"]}
    )

    assert result["ok"] is True, result
    assert result["result"]["name"] == "Invoice Triage"
    assert result["result"]["definition"] == GRAPH
    assert result["result"]["node_count"] == 2


def test_get_workflow_by_slug(api):
    client, Session = api
    email, org, _ = _owner(client)

    result = _run(Session, email, org, "get_workflow", {"slug": "invoice-triage"})

    assert result["ok"] is True, result
    assert result["result"]["slug"] == "invoice-triage"


def test_get_workflow_needs_exactly_one_selector(api):
    client, Session = api
    email, org, workflows = _owner(client)

    neither = _run(Session, email, org, "get_workflow", {})
    both = _run(
        Session, email, org, "get_workflow",
        {"workflow_id": workflows[0]["id"], "slug": "invoice-triage"},
    )

    assert neither["ok"] is False
    assert "either workflow_id or slug" in neither["error"]
    assert both["ok"] is False
    assert "not both" in both["error"]


def test_get_workflow_rejects_a_non_uuid_id(api):
    client, Session = api
    email, org, _ = _owner(client)

    result = _run(Session, email, org, "get_workflow", {"workflow_id": "not-a-uuid"})

    assert result["ok"] is False
    assert "must be a UUID" in result["error"]


def test_get_workflow_does_not_leak_other_organizations(api):
    client, Session = api
    email, org, _ = _owner(client)

    other_email = _register(client)
    other_org = _create_org(client, _login(client, other_email), "Globex")
    foreign = _create_workflow(
        client, _login(client, other_email), other_org, "Secret Flows"
    )

    by_id = _run(Session, email, org, "get_workflow", {"workflow_id": foreign["id"]})
    by_slug = _run(Session, email, org, "get_workflow", {"slug": "secret-flows"})

    for result in (by_id, by_slug):
        assert result["ok"] is False
        assert result["error"] == "Workflow not found"


def test_unknown_workflow_id_is_an_error(api):
    client, Session = api
    email, org, _ = _owner(client)

    result = _run(
        Session, email, org, "get_workflow", {"workflow_id": str(uuid.uuid4())}
    )

    assert result["ok"] is False
    assert result["error"] == "Workflow not found"


# ------------------------------------------------------------ authorization

def test_non_member_cannot_use_workflow_tools(api):
    client, Session = api
    _, org, workflows = _owner(client)
    outsider_email = _register(client)

    listed = _run(Session, outsider_email, org, "list_workflows", {})
    fetched = _run(
        Session, outsider_email, org, "get_workflow",
        {"workflow_id": workflows[0]["id"]},
    )

    for result in (listed, fetched):
        assert result["ok"] is False
        assert result["error"] == "Not a member of this organization"


def test_read_tools_never_park_a_pending_action(api):
    client, Session = api
    email, org, workflows = _owner(client)

    _run(Session, email, org, "list_workflows", {})
    _run(Session, email, org, "get_workflow", {"workflow_id": workflows[0]["id"]})

    db = Session()
    try:
        assert db.query(AgentPendingAction).count() == 0
    finally:
        db.close()


# ------------------------------------------------------------------ the loop

class FakeLLM:
    """Replays queued assistant messages in place of a real model."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.offered_tools = []

    async def __call__(self, messages, tools=None):
        self.offered_tools.append({t["function"]["name"] for t in (tools or [])})
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


def test_agent_loop_reads_a_workflow(api, monkeypatch):
    client, _ = api
    email, org, _ = _owner(client)
    token = _login(client, email)

    conversation = client.post(
        "/api/agents/conversations",
        json={"organization_id": org["id"]},
        headers=_auth(token),
    ).json()

    fake = FakeLLM([
        _tool_call("call_1", "list_workflows", "{}"),
        _tool_call("call_2", "get_workflow", '{"slug": "invoice-triage"}'),
        {"role": "assistant", "content": "Invoice Triage has two nodes."},
    ])
    monkeypatch.setattr(llm, "chat_completion", fake)

    response = client.post(
        f"/api/agents/conversations/{conversation['id']}/messages",
        json={"content": "What does the Invoice Triage workflow do?"},
        headers=_auth(token),
    )

    assert response.status_code == 200, response.text
    tool_messages = [m for m in response.json()["messages"] if m["role"] == "tool"]
    assert [m["tool_name"] for m in tool_messages] == ["list_workflows", "get_workflow"]
    assert "Invoice Triage" in tool_messages[0]["content"]
    assert '"node_count": 2' in tool_messages[1]["content"]
    assert response.json()["messages"][-1]["content"] == "Invoice Triage has two nodes."

    # Both read tools were offered to the model on the first turn.
    assert {"list_workflows", "get_workflow"} <= fake.offered_tools[0]
