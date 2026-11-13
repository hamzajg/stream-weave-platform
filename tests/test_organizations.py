import uuid


def _register(client, email=None, password="correct-horse-123"):
    email = email or f"user-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return email


def _login(client, email, password="correct-horse-123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_org(client, token, name="Acme Corp"):
    response = client.post(
        "/api/orgs",
        json={
            "name": name,
            "industry": "manufacturing",
            "size": "11-50",
            "description": "A test organization",
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_org_makes_creator_owner(client):
    email = _register(client)
    token = _login(client, email)

    org = _create_org(client, token)

    assert org["slug"] == "acme-corp"
    assert org["member_count"] == 1

    listing = client.get("/api/orgs", headers=_auth(token))
    assert listing.status_code == 200
    assert [o["id"] for o in listing.json()] == [org["id"]]
    assert listing.json()[0]["role"] == "owner"


def test_duplicate_org_names_get_unique_slugs(client):
    token = _login(client, _register(client))

    first = _create_org(client, token, "Acme!")
    second = _create_org(client, token, "Acme!")

    assert first["slug"] == "acme"
    assert second["slug"] == "acme-1"


def test_get_org_forbidden_for_non_member(client):
    owner_token = _login(client, _register(client))
    outsider_token = _login(client, _register(client))
    org = _create_org(client, owner_token)

    response = client.get(f"/api/orgs/{org['id']}", headers=_auth(outsider_token))
    assert response.status_code == 403

    response = client.get(f"/api/orgs/{org['id']}", headers=_auth(owner_token))
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


def test_update_org_requires_admin_or_owner(client):
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)

    updated = client.put(
        f"/api/orgs/{org['id']}",
        json={"name": "Acme International", "description": "Renamed"},
        headers=_auth(owner_token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Acme International"
    assert updated.json()["description"] == "Renamed"

    outsider_token = _login(client, _register(client))
    forbidden = client.put(
        f"/api/orgs/{org['id']}",
        json={"name": "Hijacked"},
        headers=_auth(outsider_token),
    )
    assert forbidden.status_code == 403


def test_invite_and_accept_adds_member(client):
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)

    invitee_email = f"invitee-{uuid.uuid4().hex}@example.com"
    invite = client.post(
        f"/api/orgs/{org['id']}/invite",
        json={"email": invitee_email, "role": "viewer"},
        headers=_auth(owner_token),
    )
    assert invite.status_code == 200, invite.text
    token_value = invite.json()["token"]

    # A pending invitation blocks a duplicate.
    duplicate = client.post(
        f"/api/orgs/{org['id']}/invite",
        json={"email": invitee_email, "role": "viewer"},
        headers=_auth(owner_token),
    )
    assert duplicate.status_code == 400

    # A different user cannot accept the invitation.
    wrong_email = _register(client)
    wrong_token = _login(client, wrong_email)
    wrong_accept = client.post(
        "/api/orgs/invitations/accept",
        json={"token": token_value},
        headers=_auth(wrong_token),
    )
    assert wrong_accept.status_code == 403

    # The invited email accepts and becomes a member.
    _register(client, email=invitee_email)
    invitee_token = _login(client, invitee_email)
    accept = client.post(
        "/api/orgs/invitations/accept",
        json={"token": token_value},
        headers=_auth(invitee_token),
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["role"] == "viewer"
    assert accept.json()["user"]["email"] == invitee_email

    members = client.get(f"/api/orgs/{org['id']}/members", headers=_auth(owner_token))
    assert members.status_code == 200
    assert len(members.json()) == 2

    # Accepting twice is rejected.
    again = client.post(
        "/api/orgs/invitations/accept",
        json={"token": token_value},
        headers=_auth(invitee_token),
    )
    assert again.status_code == 400


def test_onboarding_skip_creates_personal_workspace(client):
    token = _login(client, _register(client))

    skipped = client.post("/api/onboarding/skip", headers=_auth(token))
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["organization_name"].endswith("'s Workspace")

    status = client.get("/api/onboarding/status", headers=_auth(token))
    assert status.status_code == 200
    assert status.json()["is_complete"] is True


def test_delete_org_owner_only(client):
    owner_token = _login(client, _register(client))
    org = _create_org(client, owner_token)

    outsider_token = _login(client, _register(client))
    forbidden = client.delete(f"/api/orgs/{org['id']}", headers=_auth(outsider_token))
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/orgs/{org['id']}", headers=_auth(owner_token))
    assert deleted.status_code == 204

    gone = client.get(f"/api/orgs/{org['id']}", headers=_auth(owner_token))
    assert gone.status_code == 403
