from __future__ import annotations

from tests.conftest import login


def register(client, username: str, password: str, **extra):
    return client.post(
        "/api/auth/register", json={"username": username, "password": password, **extra}
    )


def test_register_creates_officer_and_returns_token(client):
    response = register(client, "newbie42", "S3curePass!")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "newbie42"
    assert body["user"]["role"] == "OFFICER"
    assert body["access_token"]

    # the returned token is immediately usable
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "newbie42"

    # and the new credentials work with the regular login endpoint
    again = client.post(
        "/api/auth/login",
        json={"username": "newbie42", "password": "S3curePass!"},
    )
    assert again.status_code == 200, again.text


def test_register_stores_hashed_password(client, db_session):
    from app.models import User
    from app.security import verify_password

    response = register(client, "hashcheck9", "Whatever123")
    assert response.status_code == 201, response.text

    user = db_session.query(User).filter_by(username="hashcheck9").one()
    assert user.password_hash != "Whatever123"
    assert verify_password(user.password_hash, "Whatever123")
    assert not verify_password(user.password_hash, "Whatever124")
    # self-registered accounts can only be OFFICER
    assert user.role == "OFFICER"
    assert user.is_active


def test_register_rejects_duplicate_username_case_insensitive(client):
    first = register(client, "DupUser1", "AnotherPass9")
    assert first.status_code == 201, first.text
    dup = register(client, "dupuser1", "AnotherPass9")
    assert dup.status_code == 409
    assert "taken" in dup.json()["detail"]


def test_register_rejects_weak_password(client):
    response = register(client, "shorty1", "abc")
    assert response.status_code == 422
    assert "8-128 characters" in response.json()["detail"]


def test_register_rejects_invalid_usernames(client):
    for bad in ["ab", "has space", "bad!name", "a" * 33]:
        response = register(client, bad, "LongEnough1")
        assert response.status_code == 422, (bad, response.text)
        assert "Operator ID" in response.json()["detail"]


def test_register_ignores_role_field(client, db_session):
    from app.models import User

    response = register(client, "sneaky1", "LongEnough1", role="ADMIN")
    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == "OFFICER"
    user = db_session.query(User).filter_by(username="sneaky1").one()
    assert user.role == "OFFICER"


def test_register_rate_limited_after_repeated_failures(client):
    for _ in range(5):
        blocked = register(client, "ab", "LongEnough1")
        assert blocked.status_code == 422
    response = register(client, "validname", "LongEnough1")
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_register_audit_trail(client, db_session):
    from app.models import AuditLog

    register(client, "auditee1", "LongEnough1")
    rows = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "auth.register")
        .all()
    )
    assert rows, "auth.register audit row missing"
    assert rows[-1].actor_username == "auditee1"
    assert rows[-1].actor_role == "OFFICER"


def test_login_still_works_after_register_changes(client):
    # regression: the existing demo login flow is untouched
    headers = login(client, "officer1", "FieldProof#Demo1")
    assert client.get("/api/auth/me", headers=headers).status_code == 200
