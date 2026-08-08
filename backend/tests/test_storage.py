"""File storage backend selection — local disk unless all four R2_* settings
are configured. R2Storage itself isn't exercised end-to-end here (that needs
real R2 credentials / a network call), just that it constructs cleanly from
config without touching the network (boto3 client construction is local)."""

from __future__ import annotations

from app.config import Settings
from app.storage import LocalDiskStorage, R2Storage


def test_r2_disabled_without_all_four_settings():
    assert Settings(r2_account_id="acc").r2_enabled is False
    assert Settings(r2_account_id="acc", r2_access_key_id="key").r2_enabled is False
    assert Settings().r2_enabled is False


def test_r2_enabled_with_all_four_settings():
    s = Settings(
        r2_account_id="acc",
        r2_access_key_id="key",
        r2_secret_access_key="secret",
        r2_bucket_name="bucket",
    )
    assert s.r2_enabled is True


def test_local_disk_storage_round_trip(tmp_path):
    from app import storage as storage_module

    old_dir = storage_module.settings.upload_dir
    storage_module.settings.upload_dir = str(tmp_path)
    try:
        backend = LocalDiskStorage()
        backend.save("f.txt", b"hello", "text/plain")
        assert backend.read("f.txt") == b"hello"
        backend.delete("f.txt")
        assert backend.read("f.txt") is None
    finally:
        storage_module.settings.upload_dir = old_dir


def test_r2_storage_constructs_without_network_call():
    # boto3.client() only builds a local config object — no request is made
    # until an actual S3 call, so fake credentials are safe here.
    import app.storage as storage_module

    fake_settings = Settings(
        r2_account_id="acc",
        r2_access_key_id="key",
        r2_secret_access_key="secret",
        r2_bucket_name="bucket",
    )
    old_settings = storage_module.settings
    storage_module.settings = fake_settings
    try:
        backend = R2Storage()
        assert backend._bucket == "bucket"
    finally:
        storage_module.settings = old_settings
