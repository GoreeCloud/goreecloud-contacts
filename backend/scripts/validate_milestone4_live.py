#!/usr/bin/env python3
"""Live Milestone 4 validation for a NetBird-connected development workstation.

The script prompts for the isolated CardDAV test password with getpass and never
accepts credentials on the command line or writes them to disk or ordinary output.

Read mode requires the write gate to remain disabled. Write mode requires the
administrator to enable the write gate explicitly and uses only synthetic data.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from getpass import getpass
import sys
from typing import Any

import httpx


PRIMARY_USERNAME = "goreecloud-contacts-test"
PRIMARY_BOOK_HREF = "/goreecloud-contacts-test/contacts-test/"
PRIMARY_BOOK_NAME = "GoreeCloud Contacts Test"
PRIMARY_CONTACT_NAME = "Jordan Example"
PRIMARY_CONTACT_UID = "goreecloud-test-jordan-example-001"

SYNTHETIC_NAME = "Milestone Four Example"
SYNTHETIC_PHOTO = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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


def _validate_service(client: httpx.Client, *, require_write: bool) -> None:
    health = _expect_status(client.get("/api/health"), 200, "Backend health")
    if health.get("status") != "ok":
        _fail(f"Backend health did not report status=ok: {health!r}")
    _ok("Backend health endpoint is operational")

    carddav = _expect_status(client.get("/api/carddav/status"), 200, "CardDAV status")
    if not carddav.get("configured"):
        _fail("CardDAV is not configured. Set CARDDAV_BASE_URL in the protected local .env.")

    write_enabled = carddav.get("write_enabled") is True
    if require_write and not write_enabled:
        _fail(
            "Milestone 4 write validation requires CARDDAV_WRITE_ENABLED=true. "
            "Enable it only for this isolated synthetic test, restart the backend, and rerun."
        )
    if not require_write and write_enabled:
        _fail(
            "Milestone 4 read validation requires CARDDAV_WRITE_ENABLED=false. "
            "Disable writes, restart the backend, and rerun."
        )

    _ok(
        "CardDAV is configured and the write gate is "
        + ("explicitly enabled for isolated validation" if require_write else "safely disabled")
    )


def _login(client: httpx.Client) -> None:
    password = getpass(f"CardDAV password for {PRIMARY_USERNAME}: ")
    if not password:
        _fail(f"No password was supplied for {PRIMARY_USERNAME}.")

    response = client.post(
        "/api/auth/login",
        json={"username": PRIMARY_USERNAME, "password": password},
    )
    payload = _expect_status(response, 200, "Primary test login")

    if payload.get("authenticated") is not True or payload.get("username") != PRIMARY_USERNAME:
        _fail(f"Login response did not establish the expected test session: {payload!r}")

    forbidden_keys = {"password", "token", "session_token", "carddav_password"}
    exposed = sorted(forbidden_keys.intersection(payload))
    if exposed:
        _fail(f"Authentication response exposed forbidden secret fields: {exposed}")

    _ok("Radicale-backed login succeeded for the isolated Milestone 4 test principal")


def _logout(client: httpx.Client) -> None:
    payload = _expect_status(client.post("/api/auth/logout"), 200, "Logout")
    if payload.get("authenticated") is not False:
        _fail(f"Logout response remained authenticated: {payload!r}")
    _ok("Application session was invalidated after validation")


def _validate_book(client: httpx.Client) -> None:
    books = _expect_status(client.get("/api/carddav/address-books"), 200, "Address books")
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
    _ok("Isolated GoreeCloud Contacts test address book is available")


def _find_jordan(client: httpx.Client) -> dict[str, Any]:
    contacts = _expect_status(
        client.get(
            "/api/carddav/contacts",
            params={"address_book_href": PRIMARY_BOOK_HREF},
        ),
        200,
        "Contact list",
    )
    jordan = next(
        (contact for contact in contacts if contact.get("formatted_name") == PRIMARY_CONTACT_NAME),
        None,
    )
    if jordan is None:
        _fail(f"Retained synthetic fixture {PRIMARY_CONTACT_NAME!r} was not returned.")
    if jordan.get("uid") != PRIMARY_CONTACT_UID:
        _fail(
            f"{PRIMARY_CONTACT_NAME} UID changed unexpectedly: "
            f"expected {PRIMARY_CONTACT_UID!r}, received {jordan.get('uid')!r}."
        )
    return jordan


def _validate_read_mode(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    jordan = _find_jordan(client)
    _ok("Expanded summary listing retained the existing Jordan Example fixture")

    detail = _expect_status(
        client.get("/api/carddav/contact", params={"href": jordan["href"]}),
        200,
        "Expanded contact detail",
    )

    if detail.get("uid") != PRIMARY_CONTACT_UID:
        _fail(f"Expanded detail returned unexpected UID: {detail!r}")
    if not isinstance(detail.get("structured_name"), dict):
        _fail(f"Expanded detail did not expose structured_name: {detail!r}")
    for field in ("addresses", "websites", "categories"):
        if not isinstance(detail.get(field), list):
            _fail(f"Expanded detail field {field!r} is not a list: {detail!r}")
    for field in ("favorite", "has_photo"):
        if not isinstance(detail.get(field), bool):
            _fail(f"Expanded detail field {field!r} is not boolean: {detail!r}")

    _ok("Authenticated detail endpoint returns the expanded Milestone 4 model")
    _logout(client)


def _synthetic_payload() -> dict[str, Any]:
    return {
        "formatted_name": SYNTHETIC_NAME,
        "structured_name": {
            "family_name": "Example",
            "given_name": "Milestone",
            "additional_names": "Four",
            "honorific_prefixes": "Mx.",
            "honorific_suffixes": "Test",
        },
        "emails": ["milestone4@example.test", "alternate@example.test"],
        "phones": ["+1-555-0140"],
        "organization": "GoreeCloud",
        "title": "Milestone 4 Synthetic Contact",
        "addresses": [
            {
                "types": ["home"],
                "po_box": "",
                "extended_address": "",
                "street_address": "400 Test Avenue",
                "locality": "Birmingham",
                "region": "AL",
                "postal_code": "35203",
                "country": "USA",
            }
        ],
        "birthday": "1994-08-12",
        "websites": ["https://example.test/milestone4"],
        "note": "Synthetic Milestone 4 validation contact. Safe to delete.",
        "categories": ["Milestone 4", "Synthetic, Validation"],
        "favorite": True,
        "photo": SYNTHETIC_PHOTO,
    }


def _assert_expanded_payload(detail: dict[str, Any], expected: dict[str, Any]) -> None:
    checks = {
        "formatted_name": expected["formatted_name"],
        "emails": expected["emails"],
        "phones": expected["phones"],
        "organization": expected["organization"],
        "title": expected["title"],
        "birthday": expected["birthday"],
        "websites": expected["websites"],
        "note": expected["note"],
        "categories": expected["categories"],
        "favorite": expected["favorite"],
    }
    for field, value in checks.items():
        if detail.get(field) != value:
            _fail(
                f"Expanded field {field!r} did not round-trip. "
                f"Expected {value!r}, received {detail.get(field)!r}."
            )

    if detail.get("structured_name") != expected["structured_name"]:
        _fail("Structured name did not round-trip through live CardDAV storage.")
    if detail.get("addresses") != expected["addresses"]:
        _fail("Postal address did not round-trip through live CardDAV storage.")
    if detail.get("has_photo") is not True or detail.get("photo") != expected["photo"]:
        _fail("Photo URI/data value did not round-trip through live CardDAV storage.")


def _best_effort_cleanup(
    client: httpx.Client,
    href: str | None,
    etag: str | None,
) -> None:
    if not href or not etag:
        return
    try:
        response = client.delete(
            "/api/carddav/contact",
            params={"href": href, "etag": etag},
        )
        if response.status_code in {200, 404}:
            print("INFO  Best-effort synthetic cleanup completed.")
        else:
            print(
                f"WARN  Best-effort cleanup returned HTTP {response.status_code}; "
                "inspect the isolated test address book manually.",
                file=sys.stderr,
            )
    except httpx.HTTPError:
        print(
            "WARN  Best-effort cleanup could not reach the backend; inspect the isolated "
            "test address book manually.",
            file=sys.stderr,
        )


def _validate_write_mode(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)

    payload = _synthetic_payload()
    href: str | None = None
    current_etag: str | None = None

    try:
        created = _expect_status(
            client.post(
                "/api/carddav/contacts",
                params={"address_book_href": PRIMARY_BOOK_HREF},
                json=payload,
            ),
            201,
            "Expanded contact creation",
        )
        href = created.get("href")
        original_etag = created.get("etag")
        current_etag = original_etag
        uid = created.get("uid")
        if not isinstance(href, str) or not isinstance(original_etag, str) or not uid:
            _fail(f"Create response did not return href/etag/uid: {created!r}")
        _assert_expanded_payload(created, payload)
        _ok("Expanded synthetic contact was created with all Phase 4A fields")

        detail = _expect_status(
            client.get("/api/carddav/contact", params={"href": href}),
            200,
            "Expanded contact detail after create",
        )
        if detail.get("uid") != uid:
            _fail("UID changed between create response and explicit detail read.")
        _assert_expanded_payload(detail, payload)
        _ok("Explicit detail read round-tripped expanded data through Radicale")

        updated_payload = deepcopy(payload)
        updated_payload["title"] = "Milestone 4 Synthetic Contact Updated"
        updated_payload["note"] = "Synthetic Milestone 4 contact updated through ETag protection."
        updated_payload["favorite"] = False

        updated = _expect_status(
            client.put(
                "/api/carddav/contact",
                params={"href": href, "etag": original_etag},
                json=updated_payload,
            ),
            200,
            "Expanded contact update",
        )
        if updated.get("uid") != uid:
            _fail("Expanded update did not preserve the contact UID.")
        if updated.get("etag") == original_etag:
            _fail("Expanded update did not produce a new ETag.")
        current_etag = updated.get("etag")
        if not isinstance(current_etag, str):
            _fail(f"Expanded update returned no usable ETag: {updated!r}")
        _assert_expanded_payload(updated, updated_payload)
        _ok("Expanded update preserved UID, changed ETag, and retained Phase 4A fields")

        stale = client.put(
            "/api/carddav/contact",
            params={"href": href, "etag": original_etag},
            json=payload,
        )
        _expect_status(stale, 409, "Stale expanded contact update")
        _ok("Stale ETag update was rejected with HTTP 409")

        after_stale = _expect_status(
            client.get("/api/carddav/contact", params={"href": href}),
            200,
            "Expanded contact detail after stale update",
        )
        _assert_expanded_payload(after_stale, updated_payload)
        current_etag = after_stale.get("etag")
        if not isinstance(current_etag, str):
            _fail("Detail read after stale update returned no ETag.")
        _ok("Rejected stale write did not replace the newer expanded contact state")

        deleted = _expect_status(
            client.delete(
                "/api/carddav/contact",
                params={"href": href, "etag": current_etag},
            ),
            200,
            "Expanded contact delete",
        )
        if deleted.get("deleted") is not True or deleted.get("href") != href:
            _fail(f"Delete response was unexpected: {deleted!r}")
        current_etag = None
        _ok("Expanded synthetic contact was deleted with the current ETag")

        _expect_status(
            client.get("/api/carddav/contact", params={"href": href}),
            404,
            "Detail read after delete",
        )
        _ok("Deleted synthetic contact is no longer readable")
    finally:
        _best_effort_cleanup(client, href, current_etag)

    _logout(client)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate GoreeCloud Contacts Milestone 4 against the live local API.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Local GoreeCloud Contacts backend URL (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=("read", "write"),
        default="read",
        help="read requires the safety gate off; write requires explicit temporary write enablement",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    base_url = args.api_base_url.rstrip("/")

    try:
        with httpx.Client(base_url=base_url, timeout=20.0, follow_redirects=False) as client:
            if args.mode == "read":
                _validate_service(client, require_write=False)
                _validate_read_mode(client)
                print("\nMilestone 4 expanded-model read validation PASSED.")
            else:
                _validate_service(client, require_write=True)
                _validate_write_mode(client)
                print("\nMilestone 4 expanded-model write validation PASSED.")
    except (httpx.HTTPError, ValidationFailure) as exc:
        print(f"\nFAIL  {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
