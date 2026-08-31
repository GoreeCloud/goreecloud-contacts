"""Privacy-safe translation from CardDAV adapter failures to API responses.

CardDAV transport and parsing errors can contain implementation details that are useful to
operators but unnecessary for browser users. Keep the public API surface intentionally small
and consistent while preserving the controlled authorization, conflict, and not-found messages
that explain recoverable user actions.
"""

from fastapi import HTTPException, status

from .carddav import (
    CardDavAuthenticationError,
    CardDavAuthorizationError,
    CardDavConflict,
    CardDavError,
    CardDavNotFound,
)


def carddav_http_exception(exc: CardDavError) -> HTTPException:
    """Map a CardDAV failure to the minimum useful browser-facing HTTP detail."""

    if isinstance(exc, CardDavAuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CardDAV authentication failed.",
        )
    if isinstance(exc, CardDavAuthorizationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, CardDavConflict):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if isinstance(exc, CardDavNotFound):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    # Unexpected transport/parser failures stay deliberately generic. Detailed exception
    # objects remain available to controlled server-side diagnostics when explicitly enabled;
    # they are not reflected to a browser by default.
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="CardDAV request could not be completed.",
    )
