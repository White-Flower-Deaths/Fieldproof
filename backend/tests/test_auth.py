from __future__ import annotations

from tests.conftest import login


def test_login_success_returns_token_and_user(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "officer1", "password": "FieldProof#Demo1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "OFFICER"
    assert body["user"]["badge_number"] == "FP-1042"
    assert body["access_token"]


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "officer1"


def test_wrong_password_rejected(client):
    response = client.post(
        "/api/auth/login", json={"username": "officer1", "password": "nope"}
    )
    assert response.status_code == 401


def test_unknown_user_rejected(client):
    response = client.post(
        "/api/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_rate_limited(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "officer1", "password": "bad"})
    response = client.post(
        "/api/auth/login", json={"username": "officer1", "password": "bad"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    # correct credentials are still refused while limited
    blocked = client.post(
        "/api/auth/login",
        json={"username": "officer1", "password": "FieldProof#Demo1"},
    )
    assert blocked.status_code == 429


def test_role_gate_admin_only(client):
    officer = login(client, "officer1", "FieldProof#Demo1")
    assert client.get("/api/admin/users", headers=officer).status_code == 403

    admin = login(client, "admin", "FieldProof#Admin1")
    response = client.get("/api/admin/users", headers=admin)
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert {"officer1", "officer2", "lab1", "admin"} <= usernames


def test_lab_role_cannot_admin(client):
    lab = login(client, "lab1", "FieldProof#Lab1")
    assert client.get("/api/admin/users", headers=lab).status_code == 403


def test_health_and_meta(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ok"

    meta = client.get("/api/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["app_name"] == "FieldProof"
    assert "PRESUMPTIVE" in body["disclaimer"]
    assert "not determinable" in body["concentration_note"]
    assert set(body["roles"]) == {"OFFICER", "LAB", "ADMIN"}


def test_seed_rows_carry_source_citations(client, db_session):
    from app.enums import DEMO_CITATION
    from app.models import ExpectedReaction, Kit, Substance, TestOutcome
    from app.seed import CITATION_MARKERS

    kit_cites = [r.source_citation for r in db_session.query(Kit).all()]
    outcome_cites = [r.source_citation for r in db_session.query(TestOutcome).all()]
    reaction_cites = [
        r.source_citation for r in db_session.query(ExpectedReaction).all()
    ]
    assert kit_cites and outcome_cites and reaction_cites, "seed data missing"

    # Kits, outcomes and expected reactions must cite real published sources -
    # no placeholders, no blanks, no unlabelled rows.
    for row in kit_cites + outcome_cites + reaction_cites:
        assert row and row.strip(), "empty citation"
        assert row != DEMO_CITATION, f"placeholder citation on reference row: {row[:60]}"
        assert any(marker in row for marker in CITATION_MARKERS), (
            f"citation without a recognisable source: {row[:80]}"
        )

    # Substance descriptions are generic field metadata (not reaction data)
    # and may keep DEMO_CITATION - but must still be labelled.
    subs = db_session.query(Substance).all()
    assert all(s.source_citation for s in subs)

    # size guards: 5-6 kits, 5-6 substances, the documented reaction set
    kits = db_session.query(Kit).count()
    nsubs = db_session.query(Substance).count()
    assert 5 <= kits <= 6, kits
    assert 5 <= nsubs <= 6, nsubs
    n_reactions = db_session.query(ExpectedReaction).count()
    assert 30 <= n_reactions <= 60, n_reactions

    # Cells with no published data must stay empty (docs/reaction-data.md),
    # while the best-sourced cell must be present.
    kits_by_id = {k.id: k.code for k in db_session.query(Kit).all()}
    subs_by_id = {s.id: s.code for s in db_session.query(Substance).all()}
    seeded_pairs = {
        (subs_by_id[r.substance_id], kits_by_id[r.kit_id])
        for r in db_session.query(ExpectedReaction).all()
    }
    assert ("CANNABIS", "DUQUENOIS_LEVINE") in seeded_pairs
    assert ("CANNABIS", "MARQUIS") not in seeded_pairs
    assert ("FENTANYL", "DUQUENOIS_LEVINE") not in seeded_pairs
