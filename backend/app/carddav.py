from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx

from .config import Settings
from .models import AddressBook, ContactSummary
from .vcard import parse_vcard


DAV = "DAV:"
CARDDAV = "urn:ietf:params:xml:ns:carddav"
NS = {"d": DAV, "c": CARDDAV}


class CardDavError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResourceRef:
    href: str
    etag: str | None


class CardDavClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(
            self.settings.carddav_username,
            self.settings.carddav_password,
        )

    def _resolve_safe_url(self, href: str) -> str:
        base = self.settings.carddav_base_url.rstrip("/") + "/"
        target = urljoin(base, href)

        base_parts = urlparse(base)
        target_parts = urlparse(target)

        if (
            target_parts.scheme != base_parts.scheme
            or target_parts.netloc != base_parts.netloc
        ):
            raise CardDavError("CardDAV resource resolved outside the configured server.")

        return target

    async def _request(
        self,
        method: str,
        url: str,
        *,
        depth: str | None = None,
        body: str | None = None,
    ) -> httpx.Response:
        headers = {
            "Accept": "application/xml, text/xml, text/vcard",
        }
        if depth is not None:
            headers["Depth"] = depth
        if body is not None:
            headers["Content-Type"] = "application/xml; charset=utf-8"

        try:
            async with httpx.AsyncClient(
                auth=self._auth(),
                timeout=self.settings.carddav_timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    content=body,
                )
        except httpx.HTTPError as exc:
            raise CardDavError("Unable to reach the configured CardDAV server.") from exc

        if response.status_code >= 400:
            raise CardDavError(
                f"CardDAV server returned HTTP {response.status_code}."
            )

        return response

    @staticmethod
    def _xml(response: httpx.Response) -> ET.Element:
        try:
            return ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise CardDavError("CardDAV server returned invalid XML.") from exc

    @staticmethod
    def _response_prop(response_node: ET.Element, tag: str) -> ET.Element | None:
        for propstat in response_node.findall("d:propstat", NS):
            status = propstat.findtext("d:status", default="", namespaces=NS)
            if " 200 " not in f" {status} ":
                continue
            prop = propstat.find("d:prop", NS)
            if prop is None:
                continue
            value = prop.find(tag, NS)
            if value is not None:
                return value
        return None

    async def _discover_home_url(self) -> str:
        if self.settings.carddav_addressbook_home_url:
            return self._resolve_safe_url(
                self.settings.carddav_addressbook_home_url
            )

        base_url = self.settings.carddav_base_url
        principal_body = '''<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:current-user-principal />
  </d:prop>
</d:propfind>'''

        principal_response = await self._request(
            "PROPFIND",
            base_url,
            depth="0",
            body=principal_body,
        )
        principal_root = self._xml(principal_response)
        principal_href = principal_root.findtext(
            ".//d:current-user-principal/d:href",
            default="",
            namespaces=NS,
        )

        if not principal_href:
            raise CardDavError("CardDAV principal discovery returned no principal URL.")

        principal_url = self._resolve_safe_url(principal_href)
        home_body = '''<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <c:addressbook-home-set />
  </d:prop>
</d:propfind>'''

        home_response = await self._request(
            "PROPFIND",
            principal_url,
            depth="0",
            body=home_body,
        )
        home_root = self._xml(home_response)
        home_href = home_root.findtext(
            ".//c:addressbook-home-set/d:href",
            default="",
            namespaces=NS,
        )

        if not home_href:
            raise CardDavError(
                "CardDAV principal did not expose an address-book home set."
            )

        return self._resolve_safe_url(home_href)

    async def discover_address_books(self) -> list[AddressBook]:
        home_url = await self._discover_home_url()
        body = '''<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <d:displayname />
    <d:resourcetype />
  </d:prop>
</d:propfind>'''

        response = await self._request("PROPFIND", home_url, depth="1", body=body)
        root = self._xml(response)
        address_books: list[AddressBook] = []

        for response_node in root.findall("d:response", NS):
            href = response_node.findtext("d:href", default="", namespaces=NS)
            if not href:
                continue

            resource_type = self._response_prop(response_node, "d:resourcetype")
            if (
                resource_type is None
                or resource_type.find("c:addressbook", NS) is None
            ):
                continue

            display_name_node = self._response_prop(response_node, "d:displayname")
            display_name = (
                (display_name_node.text or "").strip()
                if display_name_node is not None
                else ""
            )

            address_books.append(
                AddressBook(
                    href=href,
                    display_name=display_name or href.rstrip("/").split("/")[-1],
                )
            )

        return sorted(address_books, key=lambda item: item.display_name.casefold())

    async def _list_resource_refs(self, address_book_url: str) -> list[ResourceRef]:
        body = '''<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:getetag />
    <d:resourcetype />
  </d:prop>
</d:propfind>'''

        response = await self._request(
            "PROPFIND",
            address_book_url,
            depth="1",
            body=body,
        )
        root = self._xml(response)
        resources: list[ResourceRef] = []

        for response_node in root.findall("d:response", NS):
            href = response_node.findtext("d:href", default="", namespaces=NS)
            if not href:
                continue

            resource_type = self._response_prop(response_node, "d:resourcetype")
            if (
                resource_type is not None
                and resource_type.find("d:collection", NS) is not None
            ):
                continue

            etag_node = self._response_prop(response_node, "d:getetag")
            etag = (
                (etag_node.text or "").strip()
                if etag_node is not None
                else None
            )
            resources.append(ResourceRef(href=href, etag=etag or None))

        return resources

    async def list_contacts(self, address_book_href: str) -> list[ContactSummary]:
        address_book_url = self._resolve_safe_url(address_book_href)
        resource_refs = await self._list_resource_refs(address_book_url)

        if not resource_refs:
            return []

        href_xml = "\n".join(
            f"  <d:href>{_xml_escape(item.href)}</d:href>"
            for item in resource_refs
        )
        body = f'''<?xml version="1.0" encoding="utf-8" ?>
<c:addressbook-multiget
    xmlns:d="DAV:"
    xmlns:c="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <d:getetag />
    <c:address-data />
  </d:prop>
{href_xml}
</c:addressbook-multiget>'''

        response = await self._request(
            "REPORT",
            address_book_url,
            depth="1",
            body=body,
        )
        root = self._xml(response)
        contacts: list[ContactSummary] = []

        for response_node in root.findall("d:response", NS):
            href = response_node.findtext("d:href", default="", namespaces=NS)
            if not href:
                continue

            etag_node = self._response_prop(response_node, "d:getetag")
            etag = (
                (etag_node.text or "").strip()
                if etag_node is not None
                else None
            )

            address_data = self._response_prop(response_node, "c:address-data")
            if address_data is None or not address_data.text:
                continue

            contacts.append(
                parse_vcard(
                    address_data.text,
                    href=href,
                    etag=etag or None,
                )
            )

        return sorted(contacts, key=lambda item: item.formatted_name.casefold())


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
