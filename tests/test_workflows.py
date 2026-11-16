"""Tests for the workflow definition API (specs/workflow-definitions)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import OrganizationMember, OrganizationRole, User

PASSWORD = "correct-horse-123"


@pytest.fixture()
def api():
    """TestClient plus a session factory so tests can set member roles."""
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


def _member(client, Session, org):
    """Register a second user and attach them to `org` with the owner's role set later."""
    email = _register(client)
    token = _login(client, email)
    session = Session()
    try:
        user = session.query(User).filter(User.email == email).one()
        session.add(
            OrganizationMember(
                organization_id=uuid.UUID(org["id"]),
                user_id=user.id,
                role=OrganizationRole.VIEWER,
            )
        )
        session.commit()
    finally:
        session.close()
    return email, token


def _set_role(Session, org, email, role):
    session = Session()
    try:
        user = session.query(User).filter(User.email == email).one()
        member = (
            session.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == uuid.UUID(org["id"]),
                OrganizationMember.user_id == user.id,
            )
            .one()
        )
        member.role = role
        session.commit()
    finally:
        session.close()


def _create_workflow(client, token, org, name="Invoice Triage"):
    response = client.post(
        "/api/workflows",
        json={
            "organization_id": org["id"],
            "name": name,
            "description": "Route invoices to the right agent",
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------- US1 / AC-1

def test_editor_creates_workflow_with_empty_draft(api):
    client, Session = api
    email = _register(client)
    token = _login(client, email)
    org = _create_org(client, token)

    workflow = _create_workflow(client, token, org)

    assert workflow["slug"] == "invoice-triage"
    assert workflow["draft_version"] == 1
    assert workflow["published_version"] is None
    assert workflow["definition"] == {"nodes": [], "edges": []}
    assert workflow["organization_id"] == org["id"]

    listed = client.get("/api/workflows", headers=_auth(token))
    assert listed.status_code == 200
    assert [w["id"] for w in listed.json()] == [workflow["id"]]


def test_slugs_are_unique_within_an_organization(api):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)

    first = _create_workflow(client, token, org, "Invoice Triage")
    second = _create_workflow(client, token, org, "Invoice Triage")

    assert first["slug"] == "invoice-triage"
    assert second["slug"] == "invoice-triage-2"


def test_rename_keeps_the_slug_stable(api):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)

    renamed = client.patch(
        f"/api/workflows/{workflow['id']}",
        json={"name": "Invoice Triage v2"},
        headers=_auth(token),
    )

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Invoice Triage v2"
    assert renamed.json()["slug"] == "invoice-triage"


# ------------------------------------------------------- US2 / AC-2 tenancy

def test_other_organizations_cannot_see_the_workflow(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    acme = _create_org(client, owner_token, "Acme Corp")
    workflow = _create_workflow(client, owner_token, acme)

    outsider_token = _login(client, _register(client))
    globex = _create_org(client, outsider_token, "Globex")

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(outsider_token))
    assert fetched.status_code == 404

    listed = client.get("/api/workflows", headers=_auth(outsider_token))
    assert listed.status_code == 200
    assert listed.json() == []

    # Filtering by someone else's organization is a 404, not an empty list.
    filtered = client.get(
        f"/api/workflows?organization_id={acme['id']}", headers=_auth(outsider_token)
    )
    assert filtered.status_code == 404
    assert globex["id"] != acme["id"]


# -------------------------------------------------- US3 / AC-3 role checks

def test_viewer_is_read_only(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)
    workflow = _create_workflow(client, owner_token, org)

    _, viewer_token = _member(client, Session, org)

    assert client.get("/api/workflows", headers=_auth(viewer_token)).status_code == 200
    assert (
        client.get(f"/api/workflows/{workflow['id']}", headers=_auth(viewer_token)).status_code
        == 200
    )

    created = client.post(
        "/api/workflows",
        json={"organization_id": org["id"], "name": "Sneaky"},
        headers=_auth(viewer_token),
    )
    assert created.status_code == 403

    patched = client.patch(
        f"/api/workflows/{workflow['id']}",
        json={"name": "Hijacked"},
        headers=_auth(viewer_token),
    )
    assert patched.status_code == 403

    deleted = client.delete(f"/api/workflows/{workflow['id']}", headers=_auth(viewer_token))
    assert deleted.status_code == 403

    # And nothing changed.
    still_there = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(owner_token))
    assert still_there.status_code == 200
    assert still_there.json()["name"] == "Invoice Triage"


def test_editor_may_write_but_not_delete(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)
    workflow = _create_workflow(client, owner_token, org)

    editor_email, editor_token = _member(client, Session, org)
    _set_role(Session, org, editor_email, OrganizationRole.EDITOR)

    created = client.post(
        "/api/workflows",
        json={"organization_id": org["id"], "name": "Second Flow"},
        headers=_auth(editor_token),
    )
    assert created.status_code == 201, created.text

    assert (
        client.delete(f"/api/workflows/{workflow['id']}", headers=_auth(editor_token)).status_code
        == 403
    )


def test_admin_can_delete_and_it_disappears(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)
    workflow = _create_workflow(client, owner_token, org)

    admin_email, admin_token = _member(client, Session, org)
    _set_role(Session, org, admin_email, OrganizationRole.ADMIN)

    deleted = client.delete(f"/api/workflows/{workflow['id']}", headers=_auth(admin_token))
    assert deleted.status_code == 204

    assert client.get(f"/api/workflows/{workflow['id']}", headers=_auth(owner_token)).status_code == 404
    assert client.get("/api/workflows", headers=_auth(owner_token)).json() == []


def test_unknown_workflow_id_is_404(api):
    client, Session = api
    token = _login(client, _register(client))
    _create_org(client, token)

    response = client.get(f"/api/workflows/{uuid.uuid4()}", headers=_auth(token))
    assert response.status_code == 404


def test_create_in_foreign_organization_is_404(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    acme = _create_org(client, owner_token, "Acme Corp")

    outsider_token = _login(client, _register(client))

    response = client.post(
        "/api/workflows",
        json={"organization_id": acme["id"], "name": "Sneaky"},
        headers=_auth(outsider_token),
    )
    assert response.status_code == 404


# ------------------------------------------------- US4/US5 / AC-4..AC-6

VALID_GRAPH = {
    "nodes": [
        {"id": "t1", "type": "trigger", "label": "New invoice"},
        {"id": "a1", "type": "agent", "label": "Classify"},
        {"id": "x1", "type": "action", "label": "File it", "config": {"queue": "ap"}},
    ],
    "edges": [
        {"source": "t1", "target": "a1"},
        {"source": "a1", "target": "x1"},
    ],
}


def _put_draft(client, token, workflow_id, graph):
    return client.put(
        f"/api/workflows/{workflow_id}/draft",
        json=graph,
        headers=_auth(token),
    )


def test_valid_draft_graph_is_persisted(api):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)

    saved = _put_draft(client, token, workflow["id"], VALID_GRAPH)

    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 1
    assert saved.json()["status"] == "draft"
    assert saved.json()["definition"] == VALID_GRAPH

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token))
    assert fetched.json()["definition"] == VALID_GRAPH
    assert fetched.json()["draft_version"] == 1

    # Replacing again overwrites the same draft row rather than adding a version.
    trimmed = {
        "nodes": VALID_GRAPH["nodes"][:2],
        "edges": [{"source": "t1", "target": "a1"}],
    }
    replaced = _put_draft(client, token, workflow["id"], trimmed)
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["version"] == 1
    assert replaced.json()["definition"] == trimmed


def test_edge_to_undeclared_node_is_rejected_and_draft_unchanged(api):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)
    assert _put_draft(client, token, workflow["id"], VALID_GRAPH).status_code == 200

    broken = {
        "nodes": VALID_GRAPH["nodes"],
        "edges": [{"source": "t1", "target": "ghost"}],
    }
    rejected = _put_draft(client, token, workflow["id"], broken)

    assert rejected.status_code == 422, rejected.text
    assert "ghost" in str(rejected.json())

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token))
    assert fetched.json()["definition"] == VALID_GRAPH


@pytest.mark.parametrize(
    "graph,reason",
    [
        (
            {
                "nodes": [
                    {"id": "t1", "type": "trigger"},
                    {"id": "t1", "type": "action"},
                ],
                "edges": [],
            },
            "duplicate node",
        ),
        (
            {
                "nodes": [{"id": "a1", "type": "agent"}],
                "edges": [],
            },
            "trigger",
        ),
        (
            {
                "nodes": [
                    {"id": "t1", "type": "trigger"},
                    {"id": "t2", "type": "trigger"},
                ],
                "edges": [],
            },
            "trigger",
        ),
        (
            {
                "nodes": [
                    {"id": "t1", "type": "trigger"},
                    {"id": "u1", "type": "teleport"},
                ],
                "edges": [],
            },
            "unknown type",
        ),
    ],
)
def test_malformed_graph_is_rejected(api, graph, reason):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)

    rejected = _put_draft(client, token, workflow["id"], graph)

    assert rejected.status_code == 422, rejected.text
    assert reason in str(rejected.json())

    # The empty draft from creation is untouched.
    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token))
    assert fetched.json()["definition"] == {"nodes": [], "edges": []}
    assert fetched.json()["draft_version"] == 1


def test_viewer_cannot_replace_the_draft(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)
    workflow = _create_workflow(client, owner_token, org)
    _, viewer_token = _member(client, Session, org)

    rejected = _put_draft(client, viewer_token, workflow["id"], VALID_GRAPH)

    assert rejected.status_code == 403


def test_draft_of_a_foreign_workflow_is_404(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    acme = _create_org(client, owner_token, "Acme Corp")
    workflow = _create_workflow(client, owner_token, acme)

    outsider_token = _login(client, _register(client))
    _create_org(client, outsider_token, "Globex")

    rejected = _put_draft(client, outsider_token, workflow["id"], VALID_GRAPH)
    assert rejected.status_code == 404


# ------------------------------------------------- US6..US8 / AC-7..AC-10

def _publish(client, token, workflow_id):
    return client.post(f"/api/workflows/{workflow_id}/publish", headers=_auth(token))


def _versions(client, token, workflow_id):
    return client.get(f"/api/workflows/{workflow_id}/versions", headers=_auth(token))


def _published_workflow(api, token=None):
    """Owner token, org, and a workflow whose version 1 is published."""
    client, Session = api
    token = token or _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)
    assert _put_draft(client, token, workflow["id"], VALID_GRAPH).status_code == 200
    published = _publish(client, token, workflow["id"])
    assert published.status_code == 200, published.text
    return client, Session, token, org, workflow


def test_publish_freezes_version_and_opens_next_draft(api):
    client, Session, token, org, workflow = _published_workflow(api)

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token)).json()
    assert fetched["published_version"] == 1
    assert fetched["draft_version"] == 2

    versions = _versions(client, token, workflow["id"])
    assert versions.status_code == 200
    assert [(v["version"], v["status"]) for v in versions.json()] == [
        (2, "draft"),
        (1, "published"),
    ]
    assert versions.json()[1]["definition"] == VALID_GRAPH
    assert versions.json()[1]["published_at"] is not None


def test_published_snapshot_never_changes(api):
    client, Session, token, org, workflow = _published_workflow(api)

    different = {
        "nodes": [
            {"id": "t1", "type": "trigger", "label": "Nightly"},
            {"id": "x1", "type": "action", "label": "Email report"},
        ],
        "edges": [{"source": "t1", "target": "x1"}],
    }
    assert _put_draft(client, token, workflow["id"], different).status_code == 200

    versions = {v["version"]: v for v in _versions(client, token, workflow["id"]).json()}
    assert versions[1]["status"] == "published"
    assert versions[1]["definition"] == VALID_GRAPH
    assert versions[2]["status"] == "draft"
    assert versions[2]["definition"] == different


def test_invalid_draft_cannot_be_published(api):
    client, Session = api
    token = _login(client, _register(client))
    org = _create_org(client, token)
    workflow = _create_workflow(client, token, org)

    rejected = _publish(client, token, workflow["id"])

    assert rejected.status_code == 422, rejected.text
    assert "trigger" in str(rejected.json())

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token)).json()
    assert fetched["draft_version"] == 1
    assert fetched["published_version"] is None


def test_viewer_cannot_publish(api):
    client, Session = api
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)
    workflow = _create_workflow(client, owner_token, org)
    assert _put_draft(client, owner_token, workflow["id"], VALID_GRAPH).status_code == 200
    _, viewer_token = _member(client, Session, org)

    assert _publish(client, viewer_token, workflow["id"]).status_code == 403
    # A viewer may still read history.
    assert _versions(client, viewer_token, workflow["id"]).status_code == 200


def test_delete_removes_workflow_and_history(api):
    client, Session, token, org, workflow = _published_workflow(api)

    session = Session()
    try:
        admin_email = _register(client)
        admin_token = _login(client, admin_email)
        user = session.query(User).filter(User.email == admin_email).one()
        session.add(
            OrganizationMember(
                organization_id=uuid.UUID(org["id"]),
                user_id=user.id,
                role=OrganizationRole.ADMIN,
            )
        )
        session.commit()
    finally:
        session.close()

    deleted = client.delete(f"/api/workflows/{workflow['id']}", headers=_auth(admin_token))
    assert deleted.status_code == 204

    assert _versions(client, token, workflow["id"]).status_code == 404
    assert client.get(f"/api/workflows/{workflow['id']}", headers=_auth(token)).status_code == 404
