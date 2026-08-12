import asyncio

import httpx

from app.carddav import CardDavClient
from app.config import Settings


def _response(xml: str, url: str) -> httpx.Response:
    return httpx.Response(
        207,
        content=xml.encode("utf-8"),
        request=httpx.Request("PROPFIND", url),
    )


def test_discover_address_books(monkeypatch) -> None:
    settings = Settings(
        carddav_base_url="https://carddav.example.test",
        carddav_username="test-user",
        carddav_password="test-password",
    )
    client = CardDavClient(settings)

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

    async def fake_request(method, url, *, depth=None, body=None):
        return next(responses)

    monkeypatch.setattr(client, "_request", fake_request)

    books = asyncio.run(client.discover_address_books())

    assert len(books) == 1
    assert books[0].href == "/test-user/contacts/"
    assert books[0].display_name == "Contacts"


def test_list_contacts(monkeypatch) -> None:
    settings = Settings(
        carddav_base_url="https://carddav.example.test",
        carddav_username="test-user",
        carddav_password="test-password",
    )
    client = CardDavClient(settings)

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

    async def fake_request(method, url, *, depth=None, body=None):
        return next(responses)

    monkeypatch.setattr(client, "_request", fake_request)

    contacts = asyncio.run(client.list_contacts("/test-user/contacts/"))

    assert len(contacts) == 1
    assert contacts[0].formatted_name == "Jordan Example"
    assert contacts[0].etag == '"etag-001"'
    assert contacts[0].emails == ["jordan@example.test"]
