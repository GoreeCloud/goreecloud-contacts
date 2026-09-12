import re
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from .auth import SessionRecord, SessionStore
from .carddav import CardDavAuthorizationError, CardDavClient, CardDavError
from .carddav_errors import carddav_http_exception
from .config import Settings
from .models import MAX_RESOURCE_HREF_CHARS, ContactDetail
from .vcf import ensure_vcard_uid, inspect_vcard, normalize_vcard_record, split_vcards
from .vcf_models import (
    VcfImportPreviewItem,
    VcfImportPreviewRequest,
    VcfImportPreviewResponse,
    VcfImportRequest,
    VcfImportResponse,
    VcfImportResultItem,
)


def _safe_filename(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized[:120] or fallback


def _preview(raw: str) -> VcfImportPreviewResponse:
    records = split_vcards(raw)
    items: list[VcfImportPreviewItem] = []

    for index, record in enumerate(records):
        try:
            inspection = inspect_vcard(record, index=index)
            contact = inspection.contact
            items.append(
                VcfImportPreviewItem(
                    index=index,
                    valid=True,
                    version=inspection.version,
                    uid=contact.uid,
                    formatted_name=contact.formatted_name,
                    emails=contact.emails,
                    phones=contact.phones,
                    warnings=inspection.warnings,
                )
            )
        except ValueError as exc:
            items.append(
                VcfImportPreviewItem(
                    index=index,
                    valid=False,
                    errors=[str(exc)],
                )
            )

    valid = sum(item.valid for item in items)
    return VcfImportPreviewResponse(
        total=len(items),
        valid=valid,
        invalid=len(items) - valid,
        items=items,
    )


async def export_contact_vcard(client: CardDavClient, href: str) -> str:
    await client._authorized_contact_url(href)
    response = await client._request("GET", client._resolve_safe_url(href))
    return normalize_vcard_record(response.text)


async def export_address_book_vcard(
    client: CardDavClient,
    address_book_href: str,
) -> str:
    address_book_url = await client._authorized_address_book_url(address_book_href)
    resources = await client._list_resource_refs(address_book_url)
    records: list[str] = []

    for resource in resources:
        client._validate_contact_href(resource.href)
        response = await client._request(
            "GET",
            client._resolve_safe_url(resource.href),
        )
        records.append(normalize_vcard_record(response.text))

    return "".join(records)


async def create_imported_vcard(
    client: CardDavClient,
    address_book_href: str,
    raw_vcard: str,
) -> ContactDetail:
    address_book_url = await client._authorized_address_book_url(address_book_href)
    inspection = inspect_vcard(raw_vcard)
    prepared_vcard, _uid = ensure_vcard_uid(inspection.raw)

    resource_href = address_book_href.rstrip("/") + f"/{uuid4()}.vcf"
    resource_url = client._resolve_safe_url(resource_href)
    expected_prefix = address_book_url.rstrip("/") + "/"
    if not resource_url.startswith(expected_prefix):
        raise CardDavAuthorizationError(
            "Imported CardDAV contact resolved outside the selected address book."
        )

    await client._request(
        "PUT",
        resource_url,
        body=prepared_vcard,
        headers={"If-None-Match": "*"},
        content_type="text/vcard; charset=utf-8",
    )
    return await client._get_contact_unchecked(resource_href)


def build_vcf_router(settings: Settings, session_store: SessionStore) -> APIRouter:
    router = APIRouter()

    def require_session(request: Request) -> SessionRecord:
        record = session_store.get(request.cookies.get(settings.session_cookie_name))
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required.",
            )
        return record

    AuthenticatedSession = Annotated[SessionRecord, Depends(require_session)]

    def carddav_client(
        session: SessionRecord,
        *,
        require_write: bool = False,
    ) -> CardDavClient:
        if not settings.carddav_configured:
            raise HTTPException(
                status_code=503,
                detail="CardDAV is not configured. Set CARDDAV_BASE_URL outside source control.",
            )
        if require_write and not settings.carddav_write_enabled:
            raise HTTPException(
                status_code=403,
                detail=(
                    "CardDAV writes are disabled. Set CARDDAV_WRITE_ENABLED=true "
                    "only in an approved test or production environment."
                ),
            )
        return CardDavClient(
            settings,
            username=session.username,
            password=session.password,
        )

    @router.get("/api/carddav/contact/export")
    async def export_contact(
        session: AuthenticatedSession,
        href: Annotated[str, Query(min_length=1, max_length=MAX_RESOURCE_HREF_CHARS)],
    ) -> Response:
        client = carddav_client(session)
        try:
            raw = await export_contact_vcard(client, href)
            detail = await client.get_contact(href)
        except CardDavError as exc:
            raise carddav_http_exception(exc) from exc

        filename = _safe_filename(detail.formatted_name, "contact") + ".vcf"
        return Response(
            content=raw,
            media_type="text/vcard",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/carddav/address-book/export")
    async def export_address_book(
        session: AuthenticatedSession,
        address_book_href: Annotated[
            str,
            Query(min_length=1, max_length=MAX_RESOURCE_HREF_CHARS),
        ],
    ) -> Response:
        client = carddav_client(session)
        try:
            raw = await export_address_book_vcard(client, address_book_href)
            books = await client.discover_address_books()
        except CardDavError as exc:
            raise carddav_http_exception(exc) from exc

        book_name = next(
            (book.display_name for book in books if book.href == address_book_href),
            "address-book",
        )
        filename = _safe_filename(book_name, "address-book") + ".vcf"
        return Response(
            content=raw,
            media_type="text/vcard",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post(
        "/api/carddav/import/preview",
        response_model=VcfImportPreviewResponse,
    )
    async def import_preview(
        payload: VcfImportPreviewRequest,
        session: AuthenticatedSession,
    ) -> VcfImportPreviewResponse:
        carddav_client(session)
        try:
            return _preview(payload.vcf_text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/api/carddav/import",
        response_model=VcfImportResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def import_vcf(
        payload: VcfImportRequest,
        session: AuthenticatedSession,
    ) -> VcfImportResponse:
        client = carddav_client(session, require_write=True)

        try:
            records = split_vcards(payload.vcf_text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if payload.selected_indices is None:
            selected = list(range(len(records)))
        else:
            selected = list(dict.fromkeys(payload.selected_indices))

        if not selected:
            raise HTTPException(status_code=422, detail="Select at least one valid vCard to import.")

        if any(index < 0 or index >= len(records) for index in selected):
            raise HTTPException(
                status_code=422,
                detail="One or more selected vCard indices are outside the previewed file.",
            )

        validation_errors: list[str] = []
        for index in selected:
            try:
                inspect_vcard(records[index], index=index)
            except ValueError as exc:
                validation_errors.append(f"Record {index + 1}: {exc}")

        if validation_errors:
            raise HTTPException(status_code=422, detail=" ".join(validation_errors))

        created: list[ContactDetail] = []
        result_items: list[VcfImportResultItem] = []

        try:
            for index in selected:
                detail = await create_imported_vcard(
                    client,
                    payload.address_book_href,
                    records[index],
                )
                created.append(detail)
                result_items.append(
                    VcfImportResultItem(
                        index=index,
                        href=detail.href,
                        etag=detail.etag,
                        uid=detail.uid,
                        formatted_name=detail.formatted_name,
                    )
                )
        except CardDavError as exc:
            for detail in reversed(created):
                if not detail.etag:
                    continue
                try:
                    await client.delete_contact(detail.href, detail.etag)
                except CardDavError:
                    pass
            raise carddav_http_exception(exc) from exc
        except ValueError as exc:
            for detail in reversed(created):
                if not detail.etag:
                    continue
                try:
                    await client.delete_contact(detail.href, detail.etag)
                except CardDavError:
                    pass
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return VcfImportResponse(
            imported_count=len(result_items),
            items=result_items,
        )

    return router
