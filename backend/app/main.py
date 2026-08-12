from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .carddav import (
    CardDavClient,
    CardDavConflict,
    CardDavError,
    CardDavNotFound,
)
from .config import get_settings
from .models import (
    AddressBook,
    CardDavStatusResponse,
    ContactDeleteResponse,
    ContactSummary,
    ContactWriteRequest,
    HealthResponse,
)

settings = get_settings()

app = FastAPI(
    title="GoreeCloud Contacts API",
    version="0.2.0",
    description="CardDAV API for GoreeCloud Contacts with conditional write protection.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
)


def _carddav_client(*, require_write: bool = False) -> CardDavClient:
    if not settings.carddav_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "CardDAV is not configured. Set CARDDAV_BASE_URL, "
                "CARDDAV_USERNAME, and CARDDAV_PASSWORD outside source control."
            ),
        )

    if require_write and not settings.carddav_write_enabled:
        raise HTTPException(
            status_code=403,
            detail=(
                "CardDAV writes are disabled. Set CARDDAV_WRITE_ENABLED=true "
                "only in an approved test or production environment."
            ),
        )

    return CardDavClient(settings)


def _carddav_failure(exc: CardDavError) -> HTTPException:
    if isinstance(exc, CardDavConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, CardDavNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="goreecloud-contacts-backend",
        environment=settings.app_env,
    )


@app.get("/api/carddav/status", response_model=CardDavStatusResponse)
async def carddav_status() -> CardDavStatusResponse:
    return CardDavStatusResponse(
        configured=settings.carddav_configured,
        read_only=not settings.carddav_write_enabled,
        write_enabled=settings.carddav_write_enabled,
    )


@app.get("/api/carddav/address-books", response_model=list[AddressBook])
async def address_books() -> list[AddressBook]:
    try:
        return await _carddav_client().discover_address_books()
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.get("/api/carddav/contacts", response_model=list[ContactSummary])
async def contacts(
    address_book_href: Annotated[str, Query(min_length=1)],
) -> list[ContactSummary]:
    try:
        return await _carddav_client().list_contacts(address_book_href)
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.post(
    "/api/carddav/contacts",
    response_model=ContactSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: ContactWriteRequest,
    address_book_href: Annotated[str, Query(min_length=1)],
) -> ContactSummary:
    try:
        return await _carddav_client(require_write=True).create_contact(
            address_book_href,
            payload,
        )
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.put("/api/carddav/contact", response_model=ContactSummary)
async def update_contact(
    payload: ContactWriteRequest,
    href: Annotated[str, Query(min_length=1)],
    etag: Annotated[str, Query(min_length=1)],
) -> ContactSummary:
    try:
        return await _carddav_client(require_write=True).update_contact(
            href,
            etag,
            payload,
        )
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.delete("/api/carddav/contact", response_model=ContactDeleteResponse)
async def delete_contact(
    href: Annotated[str, Query(min_length=1)],
    etag: Annotated[str, Query(min_length=1)],
) -> ContactDeleteResponse:
    try:
        await _carddav_client(require_write=True).delete_contact(href, etag)
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc

    return ContactDeleteResponse(deleted=True, href=href)
