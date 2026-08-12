from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .carddav import CardDavClient, CardDavError
from .config import get_settings
from .models import (
    AddressBook,
    CardDavStatusResponse,
    ContactSummary,
    HealthResponse,
)

settings = get_settings()

app = FastAPI(
    title="GoreeCloud Contacts API",
    version="0.1.0",
    description="Read-only CardDAV proof-of-concept API for GoreeCloud Contacts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


def _carddav_client() -> CardDavClient:
    if not settings.carddav_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "CardDAV is not configured. Set CARDDAV_BASE_URL, "
                "CARDDAV_USERNAME, and CARDDAV_PASSWORD outside source control."
            ),
        )
    return CardDavClient(settings)


def _carddav_failure(exc: CardDavError) -> HTTPException:
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
    return CardDavStatusResponse(configured=settings.carddav_configured)


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
