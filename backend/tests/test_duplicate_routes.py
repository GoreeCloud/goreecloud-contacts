import asyncio
from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, session_store, settings

from app.carddav import CardDavConflict, CardDavError
from app.duplicate_models import DuplicateMergeRequest
from app.duplicate_routes import merge_duplicate_contacts
from app.duplicates import propose_duplicate_merge
from app.models import ContactDetail
from app.vcard import parse_vcard


class FakeCardDavClient:
    def __init__(
        self,
        *,
        fail_delete: bool = False,
        conflict_delete: bool = False,
    ) -> None:
        self.raw = {
            "/test-user/contacts/primary.vcf": (
                "BEGIN:VCARD\r\n"
                "VERSION:4.0\r\n"
                "UID:primary-uid\r\n"
                "FN:Jordan Example\r\n"
                "EMAIL:jordan@example.test\r\n"
                "X-PRIMARY:one\r\n"
                "END:VCARD\r\n"
            ),
            "/test-user/contacts/duplicate.vcf": (
                "BEGIN:VCARD\r\n"
                "VERSION:4.0\r\n"
                "UID:duplicate-uid\r\n"
                "FN:Jordan Example\r\n"
                "TEL:+1-555-0100\r\n"
                "X-DUPLICATE:two\r\n"
                "END:VCARD\r\n"
            ),
        }
        self.etags = {
            "/test-user/contacts/primary.vcf": '"primary-etag"',
            "/test-user/contacts/duplicate.vcf": '"duplicate-etag"',
        }
        self.puts: list[tuple[str, dict[str, str] | None, str | None]] = []
        self.deletes: list[tuple[str, str]] = []
        self.fail_delete = fail_delete
        self.conflict_delete = conflict_delete

    async def _authorized_address_book_url(self, href: str) -> str:
        assert href == "/test-user/contacts/"
        return "https://carddav.example.test/test-user/contacts/"

    async def _authorized_contact_url(self, href: str) -> str:
        assert href in self.raw
        return self._resolve_safe_url(href)

    def _canonical_path(self, href: str) -> str:
        return urlparse(href).path.rstrip("/") or "/"

    def _resolve_safe_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return "https://carddav.example.test" + href

    @staticmethod
    def _href_from_url(url: str) -> str:
        return urlparse(url).path

    async def _request(
        self,
        method: str,
        url: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> httpx.Response:
        href = self._href_from_url(url)
        if method == "GET":
            return httpx.Response(
                200,
                text=self.raw[href],
                headers={"etag": self.etags[href]},
            )
        if method == "PUT":
            assert content_type == "text/vcard; charset=utf-8"
            if headers != {"If-Match": self.etags[href]}:
                raise CardDavConflict("stale primary")
            self.puts.append((href, headers, body))
            assert body is not None
            self.raw[href] = body
            self.etags[href] = '"updated-primary"'
            return httpx.Response(204)
        raise AssertionError(f"Unexpected method {method}")

    async def _get_contact_unchecked(self, href: str) -> ContactDetail:
        return parse_vcard(self.raw[href], href=href, etag=self.etags[href])

    async def delete_contact(self, href: str, etag: str) -> None:
        if etag != self.etags[href]:
            raise CardDavConflict("stale duplicate")
        if self.conflict_delete:
            raise CardDavConflict("duplicate changed after survivor write")
        if self.fail_delete:
            raise CardDavError("transport outcome unknown")
        self.deletes.append((href, etag))
        del self.raw[href]
        del self.etags[href]


def _request(
    client: FakeCardDavClient,
    *,
    primary_etag: str = '"primary-etag"',
    duplicate_etag: str = '"duplicate-etag"',
) -> DuplicateMergeRequest:
    primary = parse_vcard(
        client.raw["/test-user/contacts/primary.vcf"],
        href="/test-user/contacts/primary.vcf",
        etag='"primary-etag"',
    )
    duplicate = parse_vcard(
        client.raw["/test-user/contacts/duplicate.vcf"],
        href="/test-user/contacts/duplicate.vcf",
        etag='"duplicate-etag"',
    )
    proposal = propose_duplicate_merge(primary, duplicate)
    return DuplicateMergeRequest(
        address_book_href="/test-user/contacts/",
        primary_href=primary.href,
        primary_etag=primary_etag,
        duplicate_href=duplicate.href,
        duplicate_etag=duplicate_etag,
        merged=proposal.payload,
    )


def test_merge_updates_primary_conditionally_preserves_passthrough_and_deletes_duplicate() -> None:
    client = FakeCardDavClient()

    result = asyncio.run(merge_duplicate_contacts(client, _request(client)))

    assert result.merged.uid == "primary-uid"
    assert result.deleted_href == "/test-user/contacts/duplicate.vcf"
    assert client.deletes == [
        ("/test-user/contacts/duplicate.vcf", '"duplicate-etag"')
    ]
    assert len(client.puts) == 1
    merged_raw = client.puts[0][2]
    assert merged_raw is not None
    assert "UID:primary-uid" in merged_raw
    assert "TEL:+1-555-0100" in merged_raw
    assert "X-PRIMARY:one" in merged_raw
    assert "X-DUPLICATE:two" in merged_raw
    assert "/test-user/contacts/duplicate.vcf" not in client.raw


def test_stale_primary_etag_aborts_before_any_write() -> None:
    client = FakeCardDavClient()

    with pytest.raises(CardDavConflict, match="primary contact changed"):
        asyncio.run(
            merge_duplicate_contacts(
                client,
                _request(client, primary_etag='"stale-primary"'),
            )
        )

    assert client.puts == []
    assert client.deletes == []
    assert "/test-user/contacts/primary.vcf" in client.raw
    assert "/test-user/contacts/duplicate.vcf" in client.raw


def test_stale_duplicate_etag_aborts_before_primary_write() -> None:
    client = FakeCardDavClient()

    with pytest.raises(CardDavConflict, match="duplicate contact changed"):
        asyncio.run(
            merge_duplicate_contacts(
                client,
                _request(client, duplicate_etag='"stale-duplicate"'),
            )
        )

    assert client.puts == []
    assert client.deletes == []


def test_delete_conflict_keeps_merged_survivor_and_duplicate_for_fresh_review() -> None:
    client = FakeCardDavClient(conflict_delete=True)

    with pytest.raises(CardDavConflict, match="duplicate changed before it could be deleted"):
        asyncio.run(merge_duplicate_contacts(client, _request(client)))

    assert len(client.puts) == 1
    assert "TEL:+1-555-0100" in client.raw["/test-user/contacts/primary.vcf"]
    assert "/test-user/contacts/duplicate.vcf" in client.raw
    assert client.deletes == []


def test_ambiguous_delete_failure_keeps_merged_survivor_and_duplicate_for_review() -> None:
    client = FakeCardDavClient(fail_delete=True)

    with pytest.raises(CardDavError, match="No automatic rollback was attempted"):
        asyncio.run(merge_duplicate_contacts(client, _request(client)))

    assert len(client.puts) == 1
    assert "TEL:+1-555-0100" in client.raw["/test-user/contacts/primary.vcf"]
    assert "/test-user/contacts/duplicate.vcf" in client.raw
    assert client.deletes == []


def test_duplicate_scan_uses_authenticated_session_dependency() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/carddav/duplicates",
            params={"address_book_href": "/test-user/contacts/"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}


def test_duplicate_merge_is_separately_disabled_by_default() -> None:
    assert settings.duplicate_merge_enabled is False
    record = session_store.create(username="stable-user", password="synthetic-secret")

    try:
        with TestClient(app) as client:
            client.cookies.set(settings.session_cookie_name, record.token)
            response = client.post(
                "/api/carddav/duplicates/merge",
                json={
                    "address_book_href": "/test-user/contacts/",
                    "primary_href": "/test-user/contacts/primary.vcf",
                    "primary_etag": '"primary-etag"',
                    "duplicate_href": "/test-user/contacts/duplicate.vcf",
                    "duplicate_etag": '"duplicate-etag"',
                    "merged": {"formatted_name": "Jordan Example"},
                },
            )
    finally:
        session_store.delete(record.token)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Duplicate merge is disabled until Phase 4C live acceptance is approved."
    }
