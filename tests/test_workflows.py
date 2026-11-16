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
