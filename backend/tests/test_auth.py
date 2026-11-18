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


def test_login_is_rate_limited_after_repeated_failures(client: TestClient, db: Session):
    # default budget is 5/minute (settings.login_rate_limit) — burn it, then
    # confirm the *next* attempt (whether the password is right or wrong) is
    # throttled rather than evaluated.
    for _ in range(5):
        client.post("/api/auth/login", data={"username": "admin@retail.os", "password": "nope"})

    r = client.post("/api/auth/login", data={"username": "admin@retail.os", "password": "admin123"})
    assert r.status_code == 429


def test_demo_login_signs_in_as_the_configured_user(client: TestClient, db: Session):
    r = client.post("/api/auth/demo")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == "manager@retail.os"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["role"] == "manager"


def test_demo_login_is_off_when_not_configured(client: TestClient, db: Session, monkeypatch):
    from app.routers import auth

    monkeypatch.setattr(auth.settings, "demo_autologin_email", "")
    assert client.post("/api/auth/demo").status_code == 404


def test_demo_account_password_cannot_be_changed(client: TestClient, db: Session):
    token = client.post("/api/auth/demo").json()["access_token"]
    r = client.post(
        "/api/me/password",
        json={"current_password": "manager123", "new_password": "hijacked123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
