"""Evidence on the server's disk (campus servers without S3): stored, linked with signed and
expiring URLs, and never served without a valid signature."""

import base64
import importlib
import time

import pytest
from httpx import AsyncClient

JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes\xff\xd9"


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path))
    monkeypatch.delenv("AWS_BUCKET_NAME", raising=False)
    monkeypatch.setenv("PUBLIC_API_URL", "")
    from app.services import storage_service as module

    service = module.StorageService()
    monkeypatch.setattr(module, "storage_service", service)
    from app.api import evidence

    monkeypatch.setattr(evidence, "storage_service", service)
    return service


async def test_store_link_and_serve(local_storage, async_client: AsyncClient):
    ref = local_storage.upload_base64_image("data:image/jpeg;base64," + base64.b64encode(JPEG).decode(), "evidence/1a2b-3c")
    assert ref.startswith("local://evidence/1a2b-3c/") and local_storage.is_own_reference(ref)
    url = local_storage.presign(ref)
    assert url.startswith("/api/evidence/evidence/1a2b-3c/") and "signature=" in url

    r = await async_client.get(url)
    assert r.status_code == 200 and r.content == JPEG and r.headers["content-type"] == "image/jpeg"
    assert "private" in r.headers["cache-control"]


async def test_forged_expired_and_unknown_links_are_refused(local_storage, async_client: AsyncClient):
    ref = local_storage.upload_base64_image(base64.b64encode(JPEG).decode(), "evidence/abc")
    key = ref[len("local://"):]
    good = local_storage.presign(ref)

    assert (await async_client.get(good.replace("signature=", "signature=0"))).status_code == 404  # forged
    past = int(time.time()) - 10
    expired = f"/api/evidence/{key}?expires={past}&signature={local_storage._signature(key, past)}"
    assert (await async_client.get(expired)).status_code == 404
    later = int(time.time()) + 600
    other_key = "evidence/abc/" + "0" * 32 + ".jpg"  # well-formed, signed, but no such file
    assert (await async_client.get(f"/api/evidence/{other_key}?expires={later}&signature={local_storage._signature(other_key, later)}")).status_code == 404
    traversal = "../../etc/passwd"
    assert local_storage.local_file(traversal, later, local_storage._signature(traversal, later)) is None
    assert not local_storage.is_own_reference("local://../../secret.jpg")
    assert not local_storage.is_own_reference("https://evil.example/x.jpg")


def test_without_storage_nothing_is_kept(monkeypatch):
    monkeypatch.delenv("EVIDENCE_DIR", raising=False)
    monkeypatch.delenv("AWS_BUCKET_NAME", raising=False)
    from app.services.storage_service import StorageService

    service = StorageService()
    assert not service.enabled and service.upload_base64_image(base64.b64encode(JPEG).decode()) == ""
    assert service.presign("local://evidence/abc/" + "0" * 32 + ".jpg") is None
