import asyncio

import httpx

from app.models import ContactDetail
from app.vcf_routes import create_imported_vcard, export_address_book_vcard


class FakeCardDavClient:
    def __init__(self) -> None:
        self.put_headers: dict[str, str] | None = None
        self.put_body: str | None = None

    async def _authorized_address_book_url(self, href: str) -> str:
        assert href == "/test-user/contacts/"
        return "https://carddav.example.test/test-user/contacts"

    async def _list_resource_refs(self, address_book_url: str):
        assert address_book_url.endswith("/test-user/contacts")
        return [
            type("Resource", (), {"href": "/test-user/contacts/one.vcf"})(),
            type("Resource", (), {"href": "/test-user/contacts/two.vcf"})(),
        ]

    def _validate_contact_href(self, href: str) -> None:
        assert href.endswith(".vcf")

    def _resolve_safe_url(self, href: str) -> str:
        return "https://carddav.example.test" + href

    async def _request(
        self,
        method: str,
        url: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> httpx.Response:
        if method == "GET":
            name = "One" if url.endswith("one.vcf") else "Two"
            return httpx.Response(
                200,
                text=(
                    "BEGIN:VCARD\\r\\n"
                    "VERSION:4.0\\r\\n"
                    f"FN:{name}\\r\\n"
                    f"X-UNKNOWN:{name.lower()}\\r\\n"
                    "END:VCARD\\r\\n"
                ),
            )

        assert method == "PUT"
        assert content_type == "text/vcard; charset=utf-8"
        self.put_headers = headers
        self.put_body = body
        return httpx.Response(201)

    async def _get_contact_unchecked(self, href: str) -> ContactDetail:
        return ContactDetail(
            href=href,
            etag='"created-etag"',
            uid="import-uid",
            formatted_name="Imported Example",
        )


def test_address_book_export_preserves_raw_unknown_properties() -> None:
    client = FakeCardDavClient()

    exported = asyncio.run(
        export_address_book_vcard(client, "/test-user/contacts/")
    )

    assert exported.count("BEGIN:VCARD") == 2
    assert "X-UNKNOWN:one" in exported
    assert "X-UNKNOWN:two" in exported


def test_import_creation_uses_conflict_safe_if_none_match() -> None:
    client = FakeCardDavClient()
    raw = """BEGIN:VCARD
VERSION:4.0
FN:Imported Example
X-UNKNOWN:preserve-me
END:VCARD
"""

    detail = asyncio.run(
        create_imported_vcard(
            client,
            "/test-user/contacts/",
            raw,
        )
    )

    assert detail.formatted_name == "Imported Example"
    assert client.put_headers == {"If-None-Match": "*"}
    assert client.put_body is not None
    assert "UID:" in client.put_body
    assert "X-UNKNOWN:preserve-me" in client.put_body
