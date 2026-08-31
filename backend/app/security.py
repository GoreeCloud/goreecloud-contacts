from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def normalize_origin(value: str) -> str | None:
    """Return the HTTP(S) origin portion of a URL-like value, or None when invalid."""

    candidate = value.strip()
    if not candidate or candidate == "null":
        return None

    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def configured_frontend_origin(value: str) -> str | None:
    """Validate that a value is an origin, not a full URL path."""

    candidate = value.strip()
    parsed = urlsplit(candidate)
    origin = normalize_origin(candidate)
    if origin is None:
        return None
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return origin


def request_origin_is_trusted(request: Request, expected_origin: str) -> bool:
    """Validate browser mutation provenance using Origin, then Referer as fallback."""

    trusted = configured_frontend_origin(expected_origin)
    if trusted is None:
        return False

    origin_header = request.headers.get("origin")
    if origin_header is not None:
        return configured_frontend_origin(origin_header) == trusted

    referer_header = request.headers.get("referer")
    if referer_header is None:
        return False

    return normalize_origin(referer_header) == trusted
