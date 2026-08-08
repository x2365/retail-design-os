"""File storage backend: local disk by default (dev/tests, zero setup),
Cloudflare R2 (S3-compatible object storage) when settings.r2_enabled —
required in production, since Render's free-tier filesystem is ephemeral and
wipes UPLOAD_DIR on every restart/redeploy, silently breaking every download
link for previously-uploaded files.

Mirrors the sqlite/postgres DATABASE_URL pattern in database.py: same code
path, backend picked once from settings at import time.
"""

from __future__ import annotations

import os
from typing import Protocol

from .config import get_settings

settings = get_settings()


class FileStorage(Protocol):
    def save(self, storage_name: str, data: bytes, content_type: str) -> None: ...
    def read(self, storage_name: str) -> bytes | None: ...
    def delete(self, storage_name: str) -> None: ...


class LocalDiskStorage:
    def save(self, storage_name: str, data: bytes, content_type: str) -> None:
        os.makedirs(settings.upload_dir, exist_ok=True)
        with open(os.path.join(settings.upload_dir, storage_name), "wb") as fh:
            fh.write(data)

    def read(self, storage_name: str) -> bytes | None:
        # Defence in depth: never serve a file outside the upload directory
        # (storage_name is our own uuid-based name, but stay paranoid).
        base = os.path.realpath(settings.upload_dir)
        path = os.path.realpath(os.path.join(base, storage_name))
        if not (path == base or path.startswith(base + os.sep)) or not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def delete(self, storage_name: str) -> None:
        path = os.path.join(settings.upload_dir, storage_name)
        if os.path.exists(path):
            os.remove(path)


class R2Storage:
    def __init__(self) -> None:
        import boto3
        from botocore.client import Config as BotoConfig

        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="auto",
        )
        self._bucket = settings.r2_bucket_name

    def save(self, storage_name: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket, Key=storage_name, Body=data, ContentType=content_type
        )

    def read(self, storage_name: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=storage_name)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        return obj["Body"].read()

    def delete(self, storage_name: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=storage_name)


def _build_storage() -> FileStorage:
    if settings.r2_enabled:
        return R2Storage()
    return LocalDiskStorage()


storage: FileStorage = _build_storage()
