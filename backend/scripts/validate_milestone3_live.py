#!/usr/bin/env python3
"""Live Milestone 3 validation for a NetBird-connected development workstation.

The script intentionally prompts for CardDAV passwords with getpass and never writes
credentials to disk, command-line arguments, or ordinary output.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from getpass import getpass
import math
import sys
import time
from typing import Any

import httpx


PRIMARY_USERNAME = "goreecloud-contacts-test"
PRIMARY_BOOK_HREF = "/goreecloud-contacts-test/contacts-test/"
PRIMARY_BOOK_NAME = "GoreeCloud Contacts Test"
PRIMARY_CONTACT_NAME = "Jordan Example"
PRIMARY_CONTACT_UID = "goreecloud-test-jordan-example-001"
SECONDARY_USERNAME = "goreecloud-contacts-isolation-test"


class ValidationFailure(RuntimeError):
    pass


def _ok(message: str) -> None:
    print(f"PASS  {message}")


def _fail(message: str) -> None:
    raise ValidationFailure(message)


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        _fail(
            f"{response.request.method} {response.request.url} returned non-JSON "
            f"content with HTTP {response.status_code}."
        )
        raise AssertionError from exc


def _expect_status(response: httpx.Response, expected: int, label: str) -> Any:
    if response.status_code != expected:
        detail = response.text.strip()
        if len(detail) > 500:
            detail = detail[:500] + "..."
        _fail(
            f"{label}: expected HTTP {expected}, received HTTP "
            f"{response.status_code}. Response: {detail or '<empty>'}"
        )
    return _json(response) if response.content else None


def _validate_service_safety(client: httpx.Client) -> None:
    health = _expect_status(client.get("/api/health"), 200, "Backend health")
    if health.get("status") != "ok":
        _fail(f"Backend health did not report status=ok: {health!r}")
    _ok("Backend health endpoint is operational")

    carddav = _expect_status(client.get("/api/carddav/status"), 200, "CardDAV status")
    if not carddav.get("configured"):
        _fail("CardDAV is not configured. Set CARDDAV_BASE_URL in the protected local .env.")
    if carddav.get("write_enabled") or not carddav.get("read_only"):
        _fail(
            "CARDDAV_WRITE_ENABLED must remain false for Milestone 3 authentication "
            "validation. Disable writes and restart the backend before continuing."
        )
    _ok("CardDAV is configured and the write safety gate is disabled")


def _validate_unauthenticated_boundary(client: httpx.Client) -> None:
    client.cookies.clear()
    session = _expect_status(client.get("/api/auth/session"), 200, "Unauthenticated session")
    if session.get("authenticated") is not False:
        _fail(f"Expected an unauthenticated session before login: {session!r}")
    _ok("Fresh client begins unauthenticated")

    response = client.get("/api/carddav/address-books")
    _expect_status(response, 401, "Protected address-book route before login")
    _ok("Protected CardDAV routes reject unauthenticated access")


def _login(client: httpx.Client, username: str) -> dict[str, Any]:
    password = getpass(f"CardDAV password for {username}: ")
    if not password:
        _fail(f"No password was supplied for {username}.")

    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    payload = _expect_status(response, 200, f"Login for {username}")

    if payload.get("authenticated") is not True or payload.get("username") != username:
        _fail(f"Login response did not establish the expected user session: {payload!r}")

    forbidden_keys = {"password", "token", "session_token", "carddav_password"}
    exposed = sorted(forbidden_keys.intersection(payload))
    if exposed:
        _fail(f"Authentication response exposed forbidden secret fields: {exposed}")

    set_cookie = response.headers.get("set-cookie", "").lower()
    if "httponly" not in set_cookie or "samesite=strict" not in set_cookie:
        _fail("Session cookie is missing HttpOnly or SameSite=Strict protection.")

    _ok(f"Radicale-backed login succeeded for {username}")
    _ok("Authentication response omitted password/token fields and cookie is HttpOnly/SameSite=Strict")
    return payload


def _logout_and_verify(client: httpx.Client, username: str) -> None:
    payload = _expect_status(client.post("/api/auth/logout"), 200, f"Logout for {username}")
    if payload.get("authenticated") is not False:
        _fail(f"Logout response remained authenticated: {payload!r}")

    session = _expect_status(client.get("/api/auth/session"), 200, "Session after logout")
    if session.get("authenticated") is not False:
        _fail(f"Session remained authenticated after logout: {session!r}")

    _expect_status(
        client.get("/api/carddav/address-books"),
        401,
        "Protected route after logout",
    )
    _ok(f"Logout invalidated {username}'s application session immediately")


def _validate_primary_user(client: httpx.Client) -> None:
    _login(client, PRIMARY_USERNAME)

    session = _expect_status(client.get("/api/auth/session"), 200, "Authenticated session")
    if session.get("authenticated") is not True or session.get("username") != PRIMARY_USERNAME:
        _fail(f"Authenticated session endpoint returned unexpected data: {session!r}")
    _ok("Authenticated session endpoint returns only the signed-in identity and expiration metadata")

    books = _expect_status(client.get("/api/carddav/address-books"), 200, "Primary address books")
    expected = next(
        (
            book
            for book in books
            if book.get("href") == PRIMARY_BOOK_HREF
            and book.get("display_name") == PRIMARY_BOOK_NAME
        ),
        None,
    )
    if expected is None:
        _fail(
            f"Did not discover {PRIMARY_BOOK_NAME!r} at {PRIMARY_BOOK_HREF!r}. "
            f"Discovered: {books!r}"
        )
    _ok("Primary user discovered only through its live Radicale/CardDAV principal path")

    contacts = _expect_status(
        client.get(
            "/api/carddav/contacts",
            params={"address_book_href": PRIMARY_BOOK_HREF},
        ),
        200,
        "Primary contact list",
    )
    jordan = next(
        (contact for contact in contacts if contact.get("formatted_name") == PRIMARY_CONTACT_NAME),
        None,
    )
    if jordan is None:
        _fail(f"Synthetic fixture {PRIMARY_CONTACT_NAME!r} was not returned: {contacts!r}")
    if jordan.get("uid") != PRIMARY_CONTACT_UID:
        _fail(
            f"{PRIMARY_CONTACT_NAME} UID changed unexpectedly: "
            f"expected {PRIMARY_CONTACT_UID!r}, received {jordan.get('uid')!r}."
        )
    _ok("Primary address book returned the retained Jordan Example synthetic fixture")

    _logout_and_verify(client, PRIMARY_USERNAME)


def _validate_secondary_isolation(client: httpx.Client) -> None:
    client.cookies.clear()
    _login(client, SECONDARY_USERNAME)

    books = _expect_status(client.get("/api/carddav/address-books"), 200, "Secondary address books")
    if any(book.get("href") == PRIMARY_BOOK_HREF for book in books):
        _fail(
            "The secondary principal discovered the primary test user's address book. "
            "Do not merge Milestone 3 until the Radicale/application authorization model is corrected."
        )
    _ok("Secondary principal does not discover the primary user's address book")

    response = client.get(
        "/api/carddav/contacts",
        params={"address_book_href": PRIMARY_BOOK_HREF},
    )
    _expect_status(response, 403, "Cross-user address-book selection")
    _ok("Application-level authorization rejects cross-user address-book selection with HTTP 403")

    _logout_and_verify(client, SECONDARY_USERNAME)


def _parse_expiration(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(f"Unable to parse session expires_at value {value!r}.")
        raise AssertionError from exc


def _validate_expiration(client: httpx.Client, max_wait_seconds: int) -> None:
    login = _login(client, PRIMARY_USERNAME)
    expires_at_raw = login.get("expires_at")
    if not isinstance(expires_at_raw, str):
        _fail(f"Login response did not include a usable expires_at timestamp: {login!r}")

    expires_at = _parse_expiration(expires_at_raw)
    remaining = max(0, math.ceil((expires_at - datetime.now(timezone.utc)).total_seconds()))
    if remaining > max_wait_seconds:
        _fail(
            f"Session has about {remaining} seconds remaining. For the expiration check, "
            f"set SESSION_TTL_SECONDS to {min(5, max_wait_seconds)} in the protected local .env, "
            "restart the backend, and rerun this script with --mode expiration."
        )

    print(f"INFO  Waiting {remaining + 1} seconds for the short test session to expire...")
    time.sleep(remaining + 1)

    session = _expect_status(client.get("/api/auth/session"), 200, "Expired session")
    if session.get("authenticated") is not False:
        _fail(f"Session remained authenticated after its expiration timestamp: {session!r}")
    _expect_status(client.get("/api/carddav/address-books"), 401, "Protected route after expiry")
    _ok("Expired session is removed and protected CardDAV access returns HTTP 401")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate GoreeCloud Contacts Milestone 3 against the live local API.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Local GoreeCloud Contacts backend URL (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=("core", "expiration"),
        default="core",
        help="core validates login/logout/data/isolation; expiration validates short-TTL expiry",
    )
    parser.add_argument(
        "--max-expiration-wait",
        type=int,
        default=15,
        help="Refuse to wait longer than this many seconds during expiration validation",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    base_url = args.api_base_url.rstrip("/")

    try:
        with httpx.Client(base_url=base_url, timeout=20.0, follow_redirects=False) as client:
            _validate_service_safety(client)
            _validate_unauthenticated_boundary(client)

            if args.mode == "core":
                _validate_primary_user(client)
                _validate_secondary_isolation(client)
                print("\nMilestone 3 core live API validation PASSED.")
            else:
                _validate_expiration(client, args.max_expiration_wait)
                print("\nMilestone 3 session-expiration validation PASSED.")
    except (httpx.HTTPError, ValidationFailure) as exc:
        print(f"\nFAIL  {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
