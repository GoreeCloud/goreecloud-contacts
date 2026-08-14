from __future__ import annotations

from posixpath import dirname
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from .auth import SessionRecord, SessionStore
from .carddav import (
    CardDavAuthenticationError,
    CardDavAuthorizationError,
    CardDavClient,
    CardDavConflict,
    CardDavError,
    CardDavNotFound,
)
from .config import Settings
from .duplicate_models import (
    DuplicateMergePreviewRequest,
    DuplicateMergePreviewResponse,
    DuplicateMergeRequest,
    DuplicateMergeResponse,
    DuplicateScanResponse,
)
from .duplicates import (
    detect_duplicate_candidates,
    merge_vcard_preserving_passthrough,
    propose_duplicate_merge,
)
from .vcard import parse_vcard


def _carddav_failure(exc: CardDavError) -> HTTPException:
    if isinstance(exc, CardDavAuthenticationError):
        return HTTPException(status_code=401, detail="CardDAV authentication failed.")
    if isinstance(exc, CardDavAuthorizationError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, CardDavConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, CardDavNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


async def _require_contact_in_address_book(
    client: CardDavClient,
    address_book_href: str,
    contact_href: str,
) -> None:
    address_book_url = await client._authorized_address_book_url(address_book_href)
    contact_url = await client._authorized_contact_url(contact_href)

    book_path = client._canonical_path(address_book_url)
    contact_path = client._canonical_path(contact_url)
    if dirname(contact_path) != book_path:
        raise CardDavAuthorizationError(
            "Duplicate review is restricted to contacts in the selected address book."
        )


async def scan_duplicates(
    client: CardDavClient,
    address_book_href: str,
) -> DuplicateScanResponse:
    contacts = await client.list_contacts(address_book_href)
    candidates = detect_duplicate_candidates(contacts)
    return DuplicateScanResponse(
        candidate_count=len(candidates),
        candidates=candidates,
    )


async def preview_duplicate_merge(
    client: CardDavClient,
    request: DuplicateMergePreviewRequest,
) -> DuplicateMergePreviewResponse:
    if request.primary_href == request.duplicate_href:
        raise ValueError("Choose two different contact resources for duplicate review.")

    await _require_contact_in_address_book(
        client,
        request.address_book_href,
        request.primary_href,
    )
    await _require_contact_in_address_book(
        client,
        request.address_book_href,
        request.duplicate_href,
    )

    primary = await client.get_contact(request.primary_href)
    duplicate = await client.get_contact(request.duplicate_href)
    proposal = propose_duplicate_merge(primary, duplicate)

    return DuplicateMergePreviewResponse(
        primary=primary,
        duplicate=duplicate,
        proposed=proposal.payload,
        conflicts=proposal.conflicts,
    )


async def _raw_contact(client: CardDavClient, href: str) -> tuple[str, str]:
    await client._authorized_contact_url(href)
    response = await client._request("GET", client._resolve_safe_url(href))
    etag = (response.headers.get("etag") or "").strip()
    if not etag:
        raise CardDavConflict(
            "CardDAV did not return an ETag for a contact selected for duplicate merge."
        )
    return response.text, etag


def _require_current_etag(expected: str, actual: str, label: str) -> str:
    normalized_expected = expected.strip()
    if not normalized_expected:
        raise CardDavConflict(f"The {label} contact is missing its reviewed ETag.")
    if normalized_expected != actual.strip():
        raise CardDavConflict(
            f"The {label} contact changed after duplicate review. Refresh and review the merge again."
        )
    return normalized_expected


async def merge_duplicate_contacts(
    client: CardDavClient,
    request: DuplicateMergeRequest,
) -> DuplicateMergeResponse:
    if request.primary_href == request.duplicate_href:
        raise ValueError("Choose two different contact resources to merge.")

    await _require_contact_in_address_book(
        client,
        request.address_book_href,
        request.primary_href,
    )
    await _require_contact_in_address_book(
        client,
        request.address_book_href,
        request.duplicate_href,
    )

    primary_raw, current_primary_etag = await _raw_contact(
        client,
        request.primary_href,
    )
    duplicate_raw, current_duplicate_etag = await _raw_contact(
        client,
        request.duplicate_href,
    )

    primary_etag = _require_current_etag(
        request.primary_etag,
        current_primary_etag,
        "primary",
    )
    duplicate_etag = _require_current_etag(
        request.duplicate_etag,
        current_duplicate_etag,
        "duplicate",
    )

    primary_detail = parse_vcard(
        primary_raw,
        href=request.primary_href,
        etag=current_primary_etag,
    )
    primary_uid = primary_detail.uid or str(uuid4())
    merged_raw = merge_vcard_preserving_passthrough(
        primary_raw,
        duplicate_raw,
        primary_uid=primary_uid,
        payload=request.merged,
    )

    primary_url = client._resolve_safe_url(request.primary_href)
    await client._request(
        "PUT",
        primary_url,
        body=merged_raw,
        headers={"If-Match": primary_etag},
        content_type="text/vcard; charset=utf-8",
    )
    updated = await client._get_contact_unchecked(request.primary_href)

    try:
        await client.delete_contact(request.duplicate_href, duplicate_etag)
    except CardDavConflict as exc:
        raise CardDavConflict(
            "The merged survivor was saved, but the duplicate changed before it could be "
            "deleted. The duplicate was not deleted. Refresh both contacts and review the "
            "remaining duplicate before taking another action."
        ) from exc
    except CardDavError as exc:
        raise CardDavError(
            "The merged survivor was saved, but deletion of the duplicate could not be "
            "confirmed. No automatic rollback was attempted because the CardDAV delete "
            "outcome may be ambiguous after a transport or server failure. Refresh the "
            "address book and inspect both resources before retrying."
        ) from exc

    return DuplicateMergeResponse(
        merged=updated,
        deleted_href=request.duplicate_href,
    )


def build_duplicate_router(settings: Settings, session_store: SessionStore) -> APIRouter:
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

    @router.get(
        "/api/carddav/duplicates",
        response_model=DuplicateScanResponse,
    )
    async def duplicates(
        session: AuthenticatedSession,
        address_book_href: Annotated[str, Query(min_length=1)],
    ) -> DuplicateScanResponse:
        try:
            return await scan_duplicates(carddav_client(session), address_book_href)
        except CardDavError as exc:
            raise _carddav_failure(exc) from exc

    @router.post(
        "/api/carddav/duplicates/preview",
        response_model=DuplicateMergePreviewResponse,
    )
    async def duplicate_preview(
        payload: DuplicateMergePreviewRequest,
        session: AuthenticatedSession,
    ) -> DuplicateMergePreviewResponse:
        try:
            return await preview_duplicate_merge(carddav_client(session), payload)
        except CardDavError as exc:
            raise _carddav_failure(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/api/carddav/duplicates/merge",
        response_model=DuplicateMergeResponse,
    )
    async def duplicate_merge(
        payload: DuplicateMergeRequest,
        session: AuthenticatedSession,
    ) -> DuplicateMergeResponse:
        try:
            return await merge_duplicate_contacts(
                carddav_client(session, require_write=True),
                payload,
            )
        except CardDavError as exc:
            raise _carddav_failure(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
