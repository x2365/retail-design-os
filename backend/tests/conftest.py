"""Pytest fixtures shared by the whole suite.

Isolation strategy: reference data (users/groups/brands/retail points) is
seeded once per test session via the app's own `lifespan` (create_all + seed).
Each test then runs inside its own DB transaction wrapping a SAVEPOINT
(`Session(bind=connection, join_transaction_mode="create_savepoint")`), which
is rolled back in teardown — so a test that creates tasks, documents, etc.
never leaks state into the next test, without re-seeding 90 retail points
before every single test.

Env vars are set at module import time (before `app.main` is imported
anywhere) because `get_settings()` is `lru_cache`d and reads them once.
"""

from __future__ import annotations

import os
import pathlib

_TEST_DB = pathlib.Path(__file__).parent / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ.setdefault("UPLOAD_DIR", str(pathlib.Path(__file__).parent / "test_uploads"))
os.environ["ENVIRONMENT"] = "development"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["ONEC_SERVICE_TOKEN"] = "test-1c-token"

if _TEST_DB.exists():
    _TEST_DB.unlink()

import pytest  # noqa: E402
from app.database import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import limiter  # noqa: E402
from app.seed import USERS  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# email -> plaintext password, from the seed data (see app/seed.py)
_PASSWORDS: dict[str, str] = {email: pw for email, _name, _role, pw in USERS}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The login rate limiter is a process-wide singleton (in-memory storage);
    without this every test after test_login_rate_limit would inherit its
    429s, since TestClient requests all share the same 'testclient' remote
    address."""
    limiter.reset()
    yield


@pytest.fixture(scope="session")
def client() -> TestClient:
    """One TestClient for the whole session: triggers `lifespan` exactly
    once, so create_all + seed() run a single time."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(client: TestClient) -> Session:
    """Function-scoped session bound to a SAVEPOINT that's rolled back after
    the test. Overrides `get_db` so every request the test makes through
    `client` stays inside this transaction."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _login(client: TestClient, email: str) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": _PASSWORDS[email]},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    return _login(client, "admin@retail.os")


@pytest.fixture()
def manager_headers(client: TestClient, db: Session) -> dict[str, str]:
    return _login(client, "manager@retail.os")


@pytest.fixture()
def viewer_headers(client: TestClient, db: Session) -> dict[str, str]:
    return _login(client, "viewer@retail.os")


@pytest.fixture()
def brand_headers(client: TestClient, db: Session) -> dict[str, str]:
    return _login(client, "brand@retail.os")


@pytest.fixture()
def retailer_headers(client: TestClient, db: Session) -> dict[str, str]:
    return _login(client, "retailer@retail.os")
