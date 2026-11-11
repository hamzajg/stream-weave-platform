import uuid

from app.utils.auth import create_password_reset_token


def _register(client, password="correct-horse-123"):
    email = f"user-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return email, password, response.json()


def _login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_register_and_login_round_trip(client):
    email, password, user = _register(client)
    assert user["email"] == email
    assert "hashed_password" not in user

    tokens = _login(client, email, password)
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_register_rejects_duplicate_email(client):
    email, password, _ = _register(client)
    duplicate = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert duplicate.status_code == 400


def test_login_rejects_wrong_password(client):
    email, _, _ = _register(client)
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_valid_access_token(client):
    assert client.get("/api/auth/me").status_code == 403

    email, password, _ = _register(client)
    tokens = _login(client, email, password)

    # A refresh token must not be accepted where an access token is required.
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert response.status_code == 401


def test_refresh_issues_new_tokens(client):
    email, password, _ = _register(client)
    tokens = _login(client, email, password)

    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # An access token must not be accepted by the refresh endpoint.
    wrong_type = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert wrong_type.status_code == 401


def test_password_reset_request_does_not_leak_registration(client):
    email, _, _ = _register(client)

    known = client.post("/api/auth/password-reset/request", json={"email": email})
    unknown = client.post(
        "/api/auth/password-reset/request", json={"email": "nobody@example.com"}
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()


def test_password_reset_confirm_changes_password(client):
    email, old_password, user = _register(client)

    token = create_password_reset_token({"sub": user["id"], "email": email})
    new_password = "brand-new-password-1"

    confirm = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": new_password},
    )
    assert confirm.status_code == 200

    old_login = client.post(
        "/api/auth/login", json={"email": email, "password": old_password}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login", json={"email": email, "password": new_password}
    )
    assert new_login.status_code == 200


def test_password_reset_confirm_rejects_bad_tokens(client):
    email, password, _ = _register(client)
    tokens = _login(client, email, password)

    # Malformed token.
    malformed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "not-a-jwt", "new_password": "whatever-123"},
    )
    assert malformed.status_code == 401

    # Wrong token type (an access token, not a reset token).
    wrong_type = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": tokens["access_token"], "new_password": "whatever-123"},
    )
    assert wrong_type.status_code == 401


def test_password_reset_confirm_rejects_short_password(client):
    email, _, user = _register(client)
    token = create_password_reset_token({"sub": user["id"], "email": email})

    response = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "short"},
    )
    assert response.status_code == 422
