from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import SessionRecord, SessionStore
from .carddav import (
    CardDavAuthenticationError,
    CardDavAuthorizationError,
    CardDavClient,
    CardDavConflict,
    CardDavError,
    CardDavNotFound,
)
from .config import get_settings
from .models import (
    AddressBook,
    AuthSessionResponse,
    CardDavStatusResponse,
    ContactDeleteResponse,
    ContactSummary,
    ContactWriteRequest,
    HealthResponse,
    LoginRequest,
)

settings = get_settings()
session_store = SessionStore(settings.session_ttl_seconds)

app = FastAPI(
    title="GoreeCloud Contacts API",
    version="0.3.0",
    description=(
        "CardDAV API for GoreeCloud Contacts with Radicale-backed authentication, "
        "per-user collection isolation, and conditional write protection."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
)


def _require_session(request: Request) -> SessionRecord:
    record = session_store.get(request.cookies.get(settings.session_cookie_name))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    return record


AuthenticatedSession = Annotated[SessionRecord, Depends(_require_session)]


def _carddav_client(
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


def _session_response(record: SessionRecord | None) -> AuthSessionResponse:
    if record is None:
        return AuthSessionResponse(authenticated=False)
    return AuthSessionResponse(
        authenticated=True,
        username=record.username,
        expires_at=record.expires_at,
    )


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


@app.post("/api/auth/login", response_model=AuthSessionResponse)
async def login(payload: LoginRequest, response: Response) -> AuthSessionResponse:
    if not settings.carddav_configured:
        raise HTTPException(
            status_code=503,
            detail="CardDAV is not configured. Set CARDDAV_BASE_URL outside source control.",
        )

    username = payload.username.strip()
    password = payload.password.get_secret_value()
    client = CardDavClient(settings, username=username, password=password)

    try:
        await client.discover_address_books()
    except (CardDavAuthenticationError, CardDavAuthorizationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to sign in with the supplied CardDAV credentials.",
        ) from exc
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc

    record = session_store.create(username=username, password=password)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=record.token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    return _session_response(record)


@app.get("/api/auth/session", response_model=AuthSessionResponse)
async def auth_session(request: Request) -> AuthSessionResponse:
    record = session_store.get(request.cookies.get(settings.session_cookie_name))
    return _session_response(record)


@app.post("/api/auth/logout", response_model=AuthSessionResponse)
async def logout(request: Request, response: Response) -> AuthSessionResponse:
    token = request.cookies.get(settings.session_cookie_name)
    session_store.delete(token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return AuthSessionResponse(authenticated=False)


@app.get("/api/carddav/address-books", response_model=list[AddressBook])
async def address_books(session: AuthenticatedSession) -> list[AddressBook]:
    try:
        return await _carddav_client(session).discover_address_books()
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.get("/api/carddav/contacts", response_model=list[ContactSummary])
async def contacts(
    session: AuthenticatedSession,
    address_book_href: Annotated[str, Query(min_length=1)],
) -> list[ContactSummary]:
    try:
        return await _carddav_client(session).list_contacts(address_book_href)
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.post(
    "/api/carddav/contacts",
    response_model=ContactSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: ContactWriteRequest,
    session: AuthenticatedSession,
    address_book_href: Annotated[str, Query(min_length=1)],
) -> ContactSummary:
    try:
        return await _carddav_client(session, require_write=True).create_contact(
            address_book_href,
            payload,
        )
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.put("/api/carddav/contact", response_model=ContactSummary)
async def update_contact(
    payload: ContactWriteRequest,
    session: AuthenticatedSession,
    href: Annotated[str, Query(min_length=1)],
    etag: Annotated[str, Query(min_length=1)],
) -> ContactSummary:
    try:
        return await _carddav_client(session, require_write=True).update_contact(
            href,
            etag,
            payload,
        )
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc


@app.delete("/api/carddav/contact", response_model=ContactDeleteResponse)
async def delete_contact(
    session: AuthenticatedSession,
    href: Annotated[str, Query(min_length=1)],
    etag: Annotated[str, Query(min_length=1)],
) -> ContactDeleteResponse:
    try:
        await _carddav_client(session, require_write=True).delete_contact(href, etag)
    except CardDavError as exc:
        raise _carddav_failure(exc) from exc

    return ContactDeleteResponse(deleted=True, href=href)
