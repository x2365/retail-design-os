"""Rate limiting: the app-wide default plus a tighter explicit limit on the
LLM assistant endpoint (the highest-cost route in the app)."""

from __future__ import annotations

from app.services import assistant as assistant_service
from fastapi.testclient import TestClient


def test_assistant_endpoint_is_rate_limited_tighter_than_default(
    client: TestClient, manager_headers: dict[str, str], monkeypatch
):
    # Force the fast "disabled" short-circuit (app.services.assistant.settings
    # is a module-level cached Settings instance) so this test exercises rate
    # limiting itself, not a real LLM call — this environment's .env may have
    # a live LLM configured, and hitting it 11x here would be slow, flaky,
    # and burn real API quota for no reason.
    monkeypatch.setattr(assistant_service.settings, "llm_enabled", False)

    # settings.default_rate_limit is 60/minute, but /assistant is explicitly
    # decorated with a tighter 10/minute — the 11th call in the same minute
    # should be throttled well before the app-wide default would kick in.
    for _ in range(10):
        r = client.post("/api/assistant", headers=manager_headers, json={"query": "hi"})
        assert r.status_code == 200, r.text

    r = client.post("/api/assistant", headers=manager_headers, json={"query": "hi"})
    assert r.status_code == 429
