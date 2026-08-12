import asyncio

import httpx
import pytest

from app.carddav import CardDavClient, CardDavConflict
from app.config import Settings
from app.models import ContactWriteRequest


def _response(xml: str, url: str) -> httpx.Response:
    return httpx.Response(
        207,
        content=xml.encode("utf-8"),
        request=httpx.Request("PROPFIND", url),
    )


def _vcard_response(
    *,
    url: str,
    etag: str,
    uid: str,
    name: str,
    email: str,
    phone: str,
) -> httpx.Response:
    return httpx.Response(
        200,
        text=(
            "BEGIN:VCARD\r\n"
            "VERSION:4.0\r\n"
            f"UID:{uid}\r\n"
            f"FN:{name}\r\n"
            f"EMAIL:{email}\r\n"
            f"TEL:{phone}\r\n"
            "END:VCARD\r\n"
        ),
        headers={"ETag": etag},
        request=httpx.Request("GET", url),
    )


def _settings() -> Settings:
    return Settings(
        carddav_base_url="https://carddav.example.test",
        carddav_username="test-user",
        carddav_password="test-password",
        carddav_write_enabled=True,
    )


def test_discover_address_books(monkeypatch) -> None:
    client = CardDavClient(_settings())

    responses = iter(
        [
            _response(
                '''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/</d:href>
    <d:propstat>
      <d:prop>
        <d:current-user-principal>
          <d:href>/principals/test-user/</d:href>
        </d:current-user-principal>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>''',
                "https://carddav.example.test",
            ),
            _response(
                '''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:response>
    <d:href>/principals/test-user/</d:href>
    <d:propstat>
      <d:prop>
        <c:addressbook-home-set>
          <d:href>/test-user/</d:href>
        </c:addressbook-home-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>''',
                "https://carddav.example.test/principals/test-user/",
            ),
            _response(
                '''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:response>
    <d:href>/test-user/contacts/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Contacts</d:displayname>
        <d:resourcetype>
          <d:collection />
          <c:addressbook />
        </d:resourcetype>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>''',
                "https://carddav.example.test/test-user/",
            ),
        ]
    )

    async def fake_request(
        method,
        url,
        *,
        depth=None,
        body=None,
        headers=None,
        content_type=None,
    ):
        return next(responses)

    monkeypatch.setattr(client, "_request", fake_request)

    books = asyncio.run(client.discover_address_books())

    assert len(books) == 1
    assert books[0].href == "/test-user/contacts/"
    assert books[0].display_name == "Contacts"


def test_list_contacts(monkeypatch) -> None:
    client = CardDavClient(_settings())

    responses = iter(
        [
            _response(
                '''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/test-user/contacts/</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype><d:collection /></d:resourcetype>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/test-user/contacts/contact-001.vcf</d:href>
    <d:propstat>
      <d:prop>
        <d:getetag>"etag-001"</d:getetag>
        <d:resourcetype />
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>''',
                "https://carddav.example.test/test-user/contacts/",
            ),
            _response(
                '''<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:response>
    <d:href>/test-user/contacts/contact-001.vcf</d:href>
    <d:propstat>
      <d:prop>
        <d:getetag>"etag-001"</d:getetag>
        <c:address-data>BEGIN:VCARD
VERSION:4.0
UID:contact-001
FN:Jordan Example
EMAIL:jordan@example.test
TEL:+1-555-0100
END:VCARD
</c:address-data>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>''',
                "https://carddav.example.test/test-user/contacts/",
            ),
        ]
    )

    async def fake_request(
        method,
        url,
        *,
        depth=None,
        body=None,
        headers=None,
        content_type=None,
    ):
        return next(responses)

    monkeypatch.setattr(client, "_request", fake_request)

    contacts = asyncio.run(client.list_contacts("/test-user/contacts/"))

    assert len(contacts) == 1
    assert contacts[0].formatted_name == "Jordan Example"
    assert contacts[0].etag == '"etag-001"'
    assert contacts[0].emails == ["jordan@example.test"]


def test_create_contact_uses_if_none_match(monkeypatch) -> None:
    client = CardDavClient(_settings())
    calls: list[dict[str, object]] = []

    async def fake_request(
        method,
        url,
        *,
        depth=None,
        body=None,
        headers=None,
        content_type=None,
    ):
        calls.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": headers,
                "content_type": content_type,
            }
        )
        if method == "PUT":
            return httpx.Response(201, request=httpx.Request("PUT", url))

        return _vcard_response(
            url=url,
            etag='"created-etag"',
            uid="generated",
            name="Taylor Example",
            email="taylor@example.test",
            phone="+1-555-0199",
        )

    monkeypatch.setattr(client, "_request", fake_request)

    contact = asyncio.run(
        client.create_contact(
            "/test-user/contacts/",
            ContactWriteRequest(
                formatted_name="Taylor Example",
                emails=["taylor@example.test"],
                phones=["+1-555-0199"],
            ),
        )
    )

    put_call = calls[0]
    assert put_call["method"] == "PUT"
    assert put_call["headers"] == {"If-None-Match": "*"}
    assert put_call["content_type"] == "text/vcard; charset=utf-8"
    assert "FN:Taylor Example" in str(put_call["body"])
    assert contact.formatted_name == "Taylor Example"
    assert contact.etag == '"created-etag"'


def test_update_contact_uses_if_match_and_preserves_uid(monkeypatch) -> None:
    client = CardDavClient(_settings())
    calls: list[dict[str, object]] = []
    get_count = 0

    async def fake_request(
        method,
        url,
        *,
        depth=None,
        body=None,
        headers=None,
        content_type=None,
    ):
        nonlocal get_count
        calls.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": headers,
                "content_type": content_type,
            }
        )

        if method == "GET":
            get_count += 1
            return _vcard_response(
                url=url,
                etag='"etag-001"' if get_count == 1 else '"etag-002"',
                uid="contact-001",
                name="Jordan Example" if get_count == 1 else "Jordan Updated",
                email="jordan@example.test",
                phone="+1-555-0100",
            )

        return httpx.Response(204, request=httpx.Request("PUT", url))

    monkeypatch.setattr(client, "_request", fake_request)

    contact = asyncio.run(
        client.update_contact(
            "/test-user/contacts/contact-001.vcf",
            '"etag-001"',
            ContactWriteRequest(
                formatted_name="Jordan Updated",
                emails=["jordan@example.test"],
                phones=["+1-555-0100"],
            ),
        )
    )

    put_call = next(call for call in calls if call["method"] == "PUT")
    assert put_call["headers"] == {"If-Match": '"etag-001"'}
    assert "UID:contact-001" in str(put_call["body"])
    assert "FN:Jordan Updated" in str(put_call["body"])
    assert contact.formatted_name == "Jordan Updated"
    assert contact.etag == '"etag-002"'


def test_delete_contact_uses_if_match(monkeypatch) -> None:
    client = CardDavClient(_settings())
    calls: list[dict[str, object]] = []

    async def fake_request(
        method,
        url,
        *,
        depth=None,
        body=None,
        headers=None,
        content_type=None,
    ):
        calls.append({"method": method, "url": url, "headers": headers})
        return httpx.Response(204, request=httpx.Request(method, url))

    monkeypatch.setattr(client, "_request", fake_request)

    asyncio.run(
        client.delete_contact(
            "/test-user/contacts/contact-001.vcf",
            '"etag-001"',
        )
    )

    assert calls == [
        {
            "method": "DELETE",
            "url": "https://carddav.example.test/test-user/contacts/contact-001.vcf",
            "headers": {"If-Match": '"etag-001"'},
        }
    ]


def test_precondition_failure_becomes_conflict(monkeypatch) -> None:
    client = CardDavClient(_settings())

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, *, headers, content):
            return httpx.Response(412, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeAsyncClient())

    with pytest.raises(CardDavConflict):
        asyncio.run(
            client._request(
                "PUT",
                "https://carddav.example.test/test-user/contacts/contact-001.vcf",
                body="BEGIN:VCARD\r\nEND:VCARD\r\n",
                headers={"If-Match": '"stale-etag"'},
                content_type="text/vcard; charset=utf-8",
            )
        )
