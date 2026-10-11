from __future__ import annotations

import os
from pathlib import Path

# Environment must be configured BEFORE any app import (settings are cached).
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

os.environ["FIELDPROOF_DATABASE_URL"] = f"sqlite:///{DATA_DIR / 'test_fieldproof.db'}"
os.environ["FIELDPROOF_JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
os.environ["FIELDPROOF_SEED_DEMO"] = "false"
os.environ["FIELDPROOF_ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionFactory, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rate_limit import login_limiter  # noqa: E402
from app.seed import seed_demo  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionFactory() as db:
        seed_demo(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    login_limiter.clear()
    yield
    login_limiter.clear()


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    with SessionFactory() as session:
        yield session


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
