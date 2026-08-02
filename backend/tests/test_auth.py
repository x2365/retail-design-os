"""Login, /me, and token-required access."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_admin_login_returns_token_and_role(client: TestClient, db: Session):
    r = client.post("/api/auth/login", data={"username": "admin@retail.os", "password": "admin123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["user"]["role"] == "admin"
    assert body["user"]["email"] == "admin@retail.os"


def test_login_with_wrong_password_is_rejected(client: TestClient, db: Session):
    r = client.post("/api/auth/login", data={"username": "admin@retail.os", "password": "nope"})
    assert r.status_code == 401


def test_kpis_require_a_token(client: TestClient, db: Session):
    r = client.get("/api/dashboard/kpis")
    assert r.status_code == 401


def test_me_reflects_the_logged_in_user(client: TestClient, admin_headers: dict[str, str]):
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "admin@retail.os"
