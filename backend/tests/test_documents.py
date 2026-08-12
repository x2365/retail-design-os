"""Document upload validation, download, and RBAC-gated delete."""

from __future__ import annotations

from app.routers import documents as documents_router
from fastapi.testclient import TestClient


def _create_task(client: TestClient, headers: dict[str, str]) -> str:
    r = client.post(
        "/api/tasks", headers=headers, json={"name": "doc-test", "brand": "Darling", "tt_total": 0}
    )
    assert r.status_code == 201, r.text
    return r.json()["code"]


def test_disallowed_file_extension_is_rejected(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "other", "stage": "1"},
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 415


def test_uploaded_document_can_be_downloaded_and_deleted(
    client: TestClient, manager_headers: dict[str, str], viewer_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    upload = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("sketch.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    dl = client.get(f"/api/documents/{doc_id}/download", headers=manager_headers)
    assert dl.status_code == 200
    assert dl.content == b"\x89PNG\r\n\x1a\n"

    # a viewer (read-only role) may not delete
    assert client.delete(f"/api/documents/{doc_id}", headers=viewer_headers).status_code == 403

    assert client.delete(f"/api/documents/{doc_id}", headers=manager_headers).status_code == 204

    # the document row is gone entirely (not just the file) after delete
    r = client.get(f"/api/documents/{doc_id}/download", headers=manager_headers)
    assert r.status_code == 404


def test_spoofed_content_is_rejected_even_with_allowed_extension(
    client: TestClient, manager_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={"file": ("photo.png", b"this is not actually a png", "image/png")},
    )
    assert r.status_code == 415


def test_svg_with_embedded_script_is_rejected(client: TestClient, manager_headers: dict[str, str]):
    code = _create_task(client, manager_headers)
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "sketch", "stage": "2"},
        files={
            "file": (
                "logo.svg",
                b"<svg><script>alert(1)</script></svg>",
                "image/svg+xml",
            )
        },
    )
    assert r.status_code == 415


def test_oversized_upload_is_rejected(
    client: TestClient, manager_headers: dict[str, str], monkeypatch
):
    monkeypatch.setattr(documents_router.settings, "max_upload_mb", 1)
    code = _create_task(client, manager_headers)
    oversized = b"x" * (2 * 1024 * 1024)  # 2MB > the 1MB cap set above
    r = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "other", "stage": "1"},
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert r.status_code == 413


def test_download_cyrillic_filename_content_disposition(
    client: TestClient, manager_headers: dict[str, str]
):
    code = _create_task(client, manager_headers)
    upload = client.post(
        f"/api/tasks/{code}/documents",
        headers=manager_headers,
        data={"kind": "brief", "stage": "1"},
        files={"file": ("тз_эскиз.pdf", b"%PDF", "application/pdf")},
    )
    doc_id = upload.json()["id"]

    dl = client.get(f"/api/documents/{doc_id}/download", headers=manager_headers)
    assert dl.status_code == 200
    assert "filename*=UTF-8''" in dl.headers["content-disposition"]
