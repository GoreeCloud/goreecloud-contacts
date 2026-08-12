from __future__ import annotations

from dataclasses import dataclass
from posixpath import normpath
from urllib.parse import unquote, urljoin, urlparse
from uuid import uuid4
import xml.etree.ElementTree as ET

import httpx

from .config import Settings
from .models import AddressBook, ContactDetail, ContactSummary, ContactWriteRequest
from .vcard import build_vcard, parse_vcard


DAV = "DAV:"
CARDDAV = "urn:ietf:params:xml:ns:carddav"
NS = {"d": DAV, "c": CARDDAV}


class CardDavError(RuntimeError):
    pass


class CardDavAuthenticationError(CardDavError):
    pass


class CardDavAuthorizationError(CardDavError):
    pass


class CardDavConflict(CardDavError):
    pass


class CardDavNotFound(CardDavError):
    pass


@dataclass(frozen=True, slots=True)
class ResourceRef:
    href: str
    etag: str | None


class CardDavClient:
    def __init__(
        self,
        settings: Settings,
        *,
        username: str,
        password: str,
    ) -> None:
        self.settings = settings
        self.username = username
        self.password = password

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self.username, self.password)

    def _resolve_safe_url(self, href: str) -> str:
        base = self.settings.carddav_base_url.rstrip("/") + "/"
        target = urljoin(base, href)

        base_parts = urlparse(base)
        target_parts = urlparse(target)

        if (
            target_parts.scheme != base_parts.scheme
            or target_parts.netloc != base_parts.netloc
        ):
            raise CardDavAuthorizationError(
                "CardDAV resource resolved outside the configured server."
            )

        return target

    def _canonical_path(self, href: str) -> str:
        target = self._resolve_safe_url(href)
        decoded_path = unquote(urlparse(target).path)
        normalized = normpath("/" + decoded_path.lstrip("/"))
        return normalized.rstrip("/") or "/"

    @staticmethod
    def _validate_contact_href(href: str) -> None:
        path = unquote(urlparse(href).path)
        if not path.lower().endswith(".vcf"):
            raise CardDavError("CardDAV contact resource must use a .vcf path.")

    @staticmethod
    def _validate_etag(etag: str) -> str:
        normalized = etag.strip()
        if not normalized:
            raise CardDavError("An ETag is required for this CardDAV write operation.")
        return normalized

    async def _request(
        self,
        method: str,
        url: str,
        *,
        depth: str | None = None,
        body: str | None = None,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> httpx.Response:
        request_headers = {
            "Accept": "application/xml, text/xml, text/vcard",
        }
        if depth is not None:
            request_headers["Depth"] = depth
        if content_type is not None:
            request_headers["Content-Type"] = content_type
        elif body is not None:
            request_headers["Content-Type"] = "application/xml; charset=utf-8"
        if headers:
            request_headers.update(headers)

        try:
            async with httpx.AsyncClient(
                auth=self._auth(),
                timeout=self.settings.carddav_timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    headers=request_headers,
                    content=body,
                )
        except httpx.HTTPError as exc:
            raise CardDavError("Unable to reach the configured CardDAV server.") from exc

        if response.status_code == 401:
            raise CardDavAuthenticationError("CardDAV authentication failed.")
        if response.status_code == 403:
            raise CardDavAuthorizationError("CardDAV server denied access.")
        if response.status_code == 404:
            raise CardDavNotFound("CardDAV resource was not found.")
        if response.status_code == 412:
            raise CardDavConflict(
                "CardDAV precondition failed because the resource changed or already exists."
            )
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

    async def _authorized_address_book_url(self, href: str) -> str:
        target_url = self._resolve_safe_url(href)
        target_path = self._canonical_path(target_url)
        address_books = await self.discover_address_books()

        if any(
            target_path == self._canonical_path(book.href)
            for book in address_books
        ):
            return target_url

        raise CardDavAuthorizationError(
            "The selected address book is not authorized for this session."
        )

    async def _authorized_contact_url(self, href: str) -> str:
        self._validate_contact_href(href)
        target_url = self._resolve_safe_url(href)
        target_path = self._canonical_path(target_url)
        address_books = await self.discover_address_books()

        for book in address_books:
            book_path = self._canonical_path(book.href)
            prefix = book_path.rstrip("/") + "/"
            if target_path.startswith(prefix):
                return target_url

        raise CardDavAuthorizationError(
            "The contact resource is not authorized for this session."
        )

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
        address_book_url = await self._authorized_address_book_url(address_book_href)
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

    async def _get_contact_unchecked(self, href: str) -> ContactDetail:
        url = self._resolve_safe_url(href)
        response = await self._request("GET", url)
        etag = response.headers.get("etag")
        return parse_vcard(response.text, href=href, etag=etag)

    async def get_contact(self, href: str) -> ContactDetail:
        await self._authorized_contact_url(href)
        return await self._get_contact_unchecked(href)

    @staticmethod
    def _build_contact_vcard(uid: str, payload: ContactWriteRequest) -> str:
        return build_vcard(
            uid=uid,
            formatted_name=payload.formatted_name,
            structured_name=payload.structured_name,
            emails=payload.emails,
            phones=payload.phones,
            organization=payload.organization,
            title=payload.title,
            addresses=payload.addresses,
            birthday=payload.birthday,
            websites=payload.websites,
            note=payload.note,
            categories=payload.categories,
            favorite=payload.favorite,
            photo=payload.photo,
        )

    async def create_contact(
        self,
        address_book_href: str,
        payload: ContactWriteRequest,
    ) -> ContactDetail:
        address_book_url = await self._authorized_address_book_url(address_book_href)
        uid = str(uuid4())
        resource_href = address_book_href.rstrip("/") + f"/{uid}.vcf"
        resource_url = self._resolve_safe_url(resource_href)

        expected_prefix = address_book_url.rstrip("/") + "/"
        if not resource_url.startswith(expected_prefix):
            raise CardDavAuthorizationError(
                "CardDAV contact resolved outside the selected address book."
            )

        vcard = self._build_contact_vcard(uid, payload)
        await self._request(
            "PUT",
            resource_url,
            body=vcard,
            headers={"If-None-Match": "*"},
            content_type="text/vcard; charset=utf-8",
        )
        return await self._get_contact_unchecked(resource_href)

    async def update_contact(
        self,
        href: str,
        etag: str,
        payload: ContactWriteRequest,
    ) -> ContactDetail:
        resource_url = await self._authorized_contact_url(href)
        normalized_etag = self._validate_etag(etag)
        current = await self._get_contact_unchecked(href)
        uid = current.uid or str(uuid4())
        vcard = self._build_contact_vcard(uid, payload)

        await self._request(
            "PUT",
            resource_url,
            body=vcard,
            headers={"If-Match": normalized_etag},
            content_type="text/vcard; charset=utf-8",
        )
        return await self._get_contact_unchecked(href)

    async def delete_contact(self, href: str, etag: str) -> None:
        resource_url = await self._authorized_contact_url(href)
        normalized_etag = self._validate_etag(etag)
        await self._request(
            "DELETE",
            resource_url,
            headers={"If-Match": normalized_etag},
        )


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
