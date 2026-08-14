#!/usr/bin/env python3
"""Credential-safe live acceptance helper for GoreeCloud Contacts Phase 4C.

The helper uses only the isolated goreecloud-contacts-test identity and known
synthetic Phase 4C fixtures. Password input is interactive through getpass and
is never accepted on the command line, written to disk, or printed.

Run the stages in order and change CARDDAV_WRITE_ENABLED only when the stage
explicitly requires it:

  baseline  write gate false; read-only clean baseline
  seed      write gate true; create two disposable raw VCF duplicate fixtures
  review    write gate false; read-only scan/preview and merge-gate validation
  write     write gate true; stale-ETag test, reviewed merge, raw export, cleanup
  final     write gate false; confirm cleanup and restored safety state
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
JORDAN_NAME = "Jordan Example"
JORDAN_UID = "goreecloud-test-jordan-example-001"

PRIMARY_UID = "goreecloud-phase4c-duplicate-primary-001"
DUPLICATE_UID = "goreecloud-phase4c-duplicate-secondary-001"
DUPLICATE_NAME = "Phase 4C Duplicate Test"
MATCH_EMAIL = "phase4c-duplicate@example.test"
EXTRA_EMAIL = "phase4c-secondary@example.test"
MATCH_PHONE = "+1-555-0188"
PRIMARY_ORG = "GoreeCloud Primary Test"
DUPLICATE_ORG = "GoreeCloud Secondary Test"
PRIMARY_EXTENSION = "X-GOREECLOUD-PHASE4C:primary"
DUPLICATE_EXTENSION = "X-GOREECLOUD-PHASE4C:secondary"


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
        if len(detail) > 700:
            detail = detail[:700] + "..."
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
        _fail("CardDAV is not configured in the protected local environment.")

    write_enabled = carddav.get("write_enabled") is True
    if require_write and not write_enabled:
        _fail(
            "This Phase 4C stage requires CARDDAV_WRITE_ENABLED=true. Enable it only "
            "for the isolated synthetic stage, restart the backend, and rerun."
        )
    if not require_write and write_enabled:
        _fail(
            "This Phase 4C stage requires CARDDAV_WRITE_ENABLED=false. Restore the "
            "safety gate, restart the backend, and rerun."
        )

    _ok(
        "CardDAV is configured and the write gate is "
        + ("explicitly enabled for this isolated stage" if require_write else "safely disabled")
    )


def _login(client: httpx.Client) -> None:
    password = getpass(f"CardDAV password for {PRIMARY_USERNAME}: ")
    if not password:
        _fail(f"No password was supplied for {PRIMARY_USERNAME}.")

    payload = _expect_status(
        client.post(
            "/api/auth/login",
            json={"username": PRIMARY_USERNAME, "password": password},
        ),
        200,
        "Isolated test login",
    )
    if payload.get("authenticated") is not True or payload.get("username") != PRIMARY_USERNAME:
        _fail(f"Unexpected login response: {payload!r}")

    forbidden = {"password", "token", "session_token", "carddav_password"}.intersection(payload)
    if forbidden:
        _fail(f"Authentication response exposed forbidden fields: {sorted(forbidden)}")
    _ok("Radicale-backed sign-in succeeded for the isolated Phase 4C test identity")


def _logout(client: httpx.Client) -> None:
    payload = _expect_status(client.post("/api/auth/logout"), 200, "Logout")
    if payload.get("authenticated") is not False:
        _fail(f"Logout response remained authenticated: {payload!r}")
    _ok("Application session was invalidated")


def _validate_book(client: httpx.Client) -> None:
    books = _expect_status(client.get("/api/carddav/address-books"), 200, "Address books")
    match = next(
        (
            book
            for book in books
            if book.get("href") == PRIMARY_BOOK_HREF
            and book.get("display_name") == PRIMARY_BOOK_NAME
        ),
        None,
    )
    if match is None:
        _fail(f"Expected isolated address book was not discovered: {books!r}")
    _ok("Only the explicitly selected isolated address book is used by this helper")


def _contacts(client: httpx.Client) -> list[dict[str, Any]]:
    result = _expect_status(
        client.get(
            "/api/carddav/contacts",
            params={"address_book_href": PRIMARY_BOOK_HREF},
        ),
        200,
        "Contact list",
    )
    if not isinstance(result, list):
        _fail(f"Contact list response is not a list: {result!r}")
    return result


def _by_uid(contacts: list[dict[str, Any]], uid: str) -> dict[str, Any] | None:
    return next((contact for contact in contacts if contact.get("uid") == uid), None)


def _require_jordan(contacts: list[dict[str, Any]]) -> dict[str, Any]:
    jordan = _by_uid(contacts, JORDAN_UID)
    if jordan is None or jordan.get("formatted_name") != JORDAN_NAME:
        _fail("The retained Jordan Example synthetic fixture is missing or changed.")
    return jordan


def _require_clean_baseline(contacts: list[dict[str, Any]]) -> None:
    _require_jordan(contacts)
    if len(contacts) != 1:
        summary = [(item.get("formatted_name"), item.get("uid")) for item in contacts]
        _fail(
            "The isolated address book is not at the required one-contact baseline. "
            f"Current contacts: {summary!r}"
        )
    _ok("Jordan Example is the only retained contact in the isolated test address book")


def _scan(client: httpx.Client) -> dict[str, Any]:
    payload = _expect_status(
        client.get(
            "/api/carddav/duplicates",
            params={"address_book_href": PRIMARY_BOOK_HREF},
        ),
        200,
        "Duplicate scan",
    )
    if not isinstance(payload.get("candidates"), list):
        _fail(f"Duplicate scan returned an unexpected payload: {payload!r}")
    return payload


def _candidate_for_fixture(scan: dict[str, Any]) -> dict[str, Any]:
    expected_uids = {PRIMARY_UID, DUPLICATE_UID}
    for candidate in scan.get("candidates", []):
        left_uid = candidate.get("left", {}).get("uid")
        right_uid = candidate.get("right", {}).get("uid")
        if {left_uid, right_uid} == expected_uids:
            return candidate
    _fail(f"Phase 4C synthetic duplicate pair was not returned: {scan!r}")
    raise AssertionError


def _fixture_vcf() -> str:
    return (
        "BEGIN:VCARD\r\n"
        "VERSION:4.0\r\n"
        f"UID:{PRIMARY_UID}\r\n"
        f"FN:{DUPLICATE_NAME}\r\n"
        "N:Test;Phase 4C Duplicate;;;\r\n"
        f"EMAIL;TYPE=home:{MATCH_EMAIL}\r\n"
        f"TEL;TYPE=cell:{MATCH_PHONE}\r\n"
        f"ORG:{PRIMARY_ORG}\r\n"
        "TITLE:Primary Candidate\r\n"
        "URL:https://primary.phase4c.example.test\r\n"
        "CATEGORIES:Phase 4C,Synthetic\r\n"
        f"{PRIMARY_EXTENSION}\r\n"
        "END:VCARD\r\n"
        "BEGIN:VCARD\r\n"
        "VERSION:4.0\r\n"
        f"UID:{DUPLICATE_UID}\r\n"
        f"FN:{DUPLICATE_NAME}\r\n"
        "N:Test;Phase 4C Duplicate;;;\r\n"
        f"EMAIL;TYPE=work:{MATCH_EMAIL.upper()}\r\n"
        f"EMAIL;TYPE=work:{EXTRA_EMAIL}\r\n"
        "TEL;TYPE=work:+1 (555) 0188\r\n"
        f"ORG:{DUPLICATE_ORG}\r\n"
        "TITLE:Secondary Candidate\r\n"
        "NOTE:Disposable Phase 4C secondary duplicate.\r\n"
        "CATEGORIES:Phase 4C,Duplicate\r\n"
        f"{DUPLICATE_EXTENSION}\r\n"
        "END:VCARD\r\n"
    )


def _preview(
    client: httpx.Client,
    primary_href: str,
    duplicate_href: str,
) -> dict[str, Any]:
    return _expect_status(
        client.post(
            "/api/carddav/duplicates/preview",
            json={
                "address_book_href": PRIMARY_BOOK_HREF,
                "primary_href": primary_href,
                "duplicate_href": duplicate_href,
            },
        ),
        200,
        "Duplicate merge preview",
    )


def _write_payload(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "formatted_name": detail["formatted_name"],
        "structured_name": deepcopy(detail.get("structured_name") or {}),
        "emails": list(detail.get("emails") or []),
        "phones": list(detail.get("phones") or []),
        "organization": detail.get("organization"),
        "title": detail.get("title"),
        "addresses": deepcopy(detail.get("addresses") or []),
        "birthday": detail.get("birthday"),
        "websites": list(detail.get("websites") or []),
        "note": detail.get("note"),
        "categories": list(detail.get("categories") or []),
        "favorite": bool(detail.get("favorite")),
        "photo": detail.get("photo"),
    }


def _validate_preview(preview: dict[str, Any]) -> None:
    if preview.get("primary", {}).get("uid") != PRIMARY_UID:
        _fail(f"Preview did not retain the selected primary contact: {preview!r}")
    if preview.get("duplicate", {}).get("uid") != DUPLICATE_UID:
        _fail(f"Preview did not retain the selected duplicate contact: {preview!r}")

    proposed = preview.get("proposed") or {}
    normalized_emails = {str(value).casefold() for value in proposed.get("emails", [])}
    if MATCH_EMAIL.casefold() not in normalized_emails or EXTRA_EMAIL.casefold() not in normalized_emails:
        _fail(f"Preview did not union the expected email addresses: {proposed!r}")

    conflicts = {item.get("field"): item for item in preview.get("conflicts", [])}
    for field in ("organization", "title"):
        if field not in conflicts:
            _fail(f"Preview did not surface expected {field!r} conflict: {preview!r}")

    if proposed.get("organization") != PRIMARY_ORG:
        _fail("Default proposal did not prefer the explicitly selected primary organization.")
    _ok("Merge preview unions complementary fields and surfaces scalar conflicts for review")


def _blocked_merge_body(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "address_book_href": PRIMARY_BOOK_HREF,
        "primary_href": preview["primary"]["href"],
        "primary_etag": preview["primary"]["etag"],
        "duplicate_href": preview["duplicate"]["href"],
        "duplicate_etag": preview["duplicate"]["etag"],
        "merged": preview["proposed"],
    }


def _baseline(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    contacts = _contacts(client)
    _require_clean_baseline(contacts)

    scan = _scan(client)
    if scan.get("candidate_count") != 0:
        _fail(f"Clean one-contact baseline unexpectedly returned duplicates: {scan!r}")
    _ok("Read-only duplicate scan returns no candidate against the clean baseline")

    jordan = _require_jordan(contacts)
    blocked = client.post(
        "/api/carddav/duplicates/merge",
        json={
            "address_book_href": PRIMARY_BOOK_HREF,
            "primary_href": jordan["href"],
            "primary_etag": jordan["etag"],
            "duplicate_href": "/goreecloud-contacts-test/contacts-test/nonexistent-phase4c.vcf",
            "duplicate_etag": '"synthetic-etag"',
            "merged": {
                "formatted_name": JORDAN_NAME,
                "structured_name": {},
                "emails": [],
                "phones": [],
                "addresses": [],
                "websites": [],
                "categories": [],
                "favorite": False,
            },
        },
    )
    _expect_status(blocked, 403, "Write-gated duplicate merge")
    _ok("Duplicate merge endpoint is blocked before mutation while writes are disabled")
    _logout(client)


def _seed(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    contacts = _contacts(client)
    _require_clean_baseline(contacts)

    raw = _fixture_vcf()
    preview = _expect_status(
        client.post("/api/carddav/import/preview", json={"vcf_text": raw}),
        200,
        "Phase 4C fixture VCF preview",
    )
    if preview.get("total") != 2 or preview.get("valid") != 2 or preview.get("invalid") != 0:
        _fail(f"Synthetic Phase 4C fixture preview was unexpected: {preview!r}")

    imported = _expect_status(
        client.post(
            "/api/carddav/import",
            json={
                "address_book_href": PRIMARY_BOOK_HREF,
                "vcf_text": raw,
                "selected_indices": [0, 1],
            },
        ),
        201,
        "Phase 4C fixture import",
    )
    if imported.get("imported_count") != 2:
        _fail(f"Expected two seeded Phase 4C contacts: {imported!r}")

    contacts = _contacts(client)
    if _by_uid(contacts, PRIMARY_UID) is None or _by_uid(contacts, DUPLICATE_UID) is None:
        _fail("Both Phase 4C synthetic duplicate fixtures were not returned after seeding.")
    if len(contacts) != 3:
        _fail(f"Expected Jordan plus two Phase 4C fixtures after seed; found {len(contacts)} contacts.")
    _ok("Two disposable raw VCF duplicate fixtures were created in the isolated address book")
    _logout(client)
    print("\nNEXT  Restore CARDDAV_WRITE_ENABLED=false, restart the backend, then run --stage review.")


def _review(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    contacts = _contacts(client)
    _require_jordan(contacts)
    primary = _by_uid(contacts, PRIMARY_UID)
    duplicate = _by_uid(contacts, DUPLICATE_UID)
    if primary is None or duplicate is None:
        _fail("Phase 4C seed fixtures are missing. Run --stage seed with the write gate enabled first.")

    scan = _scan(client)
    candidate = _candidate_for_fixture(scan)
    if candidate.get("confidence") != "high":
        _fail(f"Expected high-confidence synthetic candidate: {candidate!r}")
    kinds = {item.get("kind") for item in candidate.get("signals", [])}
    if not {"email", "phone", "name"}.issubset(kinds):
        _fail(f"Synthetic pair did not return expected match signals: {candidate!r}")
    _ok("Read-only scan detects the seeded pair with expected strong matching signals")

    preview = _preview(client, primary["href"], duplicate["href"])
    _validate_preview(preview)

    blocked = client.post(
        "/api/carddav/duplicates/merge",
        json=_blocked_merge_body(preview),
    )
    _expect_status(blocked, 403, "Read-only reviewed merge")
    _ok("A valid reviewed merge remains disabled while the write safety gate is false")
    _logout(client)
    print("\nNEXT  Enable CARDDAV_WRITE_ENABLED=true only for the isolated test, restart the backend, then run --stage write.")


def _write(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    contacts = _contacts(client)
    _require_jordan(contacts)
    primary = _by_uid(contacts, PRIMARY_UID)
    duplicate = _by_uid(contacts, DUPLICATE_UID)
    if primary is None or duplicate is None:
        _fail("Phase 4C seed fixtures are missing; do not run write validation against other contacts.")

    preview = _preview(client, primary["href"], duplicate["href"])
    _validate_preview(preview)
    original_primary_etag = preview["primary"]["etag"]

    duplicate_payload = _write_payload(preview["duplicate"])
    duplicate_payload["note"] = "Phase 4C stale-ETag mutation; disposable validation data."
    updated_duplicate = _expect_status(
        client.put(
            "/api/carddav/contact",
            params={
                "href": preview["duplicate"]["href"],
                "etag": preview["duplicate"]["etag"],
            },
            json=duplicate_payload,
        ),
        200,
        "Controlled duplicate mutation for stale-ETag test",
    )
    if updated_duplicate.get("etag") == preview["duplicate"]["etag"]:
        _fail("Controlled duplicate mutation did not change the ETag.")

    stale = client.post(
        "/api/carddav/duplicates/merge",
        json=_blocked_merge_body(preview),
    )
    _expect_status(stale, 409, "Stale reviewed duplicate merge")

    primary_after_stale = _expect_status(
        client.get("/api/carddav/contact", params={"href": preview["primary"]["href"]}),
        200,
        "Primary after stale reviewed merge",
    )
    if primary_after_stale.get("etag") != original_primary_etag:
        _fail("Stale duplicate ETag rejection occurred after the primary contact changed.")
    _ok("Stale duplicate ETag rejects the merge before the survivor is mutated")

    fresh = _preview(client, primary["href"], duplicate["href"])
    _validate_preview(fresh)
    merged_payload = deepcopy(fresh["proposed"])
    org_conflict = next(
        (item for item in fresh.get("conflicts", []) if item.get("field") == "organization"),
        None,
    )
    if org_conflict is None or org_conflict.get("duplicate_value") != DUPLICATE_ORG:
        _fail(f"Fresh preview did not expose expected organization choice: {fresh!r}")
    merged_payload["organization"] = org_conflict["duplicate_value"]

    merge_result = _expect_status(
        client.post(
            "/api/carddav/duplicates/merge",
            json={
                "address_book_href": PRIMARY_BOOK_HREF,
                "primary_href": fresh["primary"]["href"],
                "primary_etag": fresh["primary"]["etag"],
                "duplicate_href": fresh["duplicate"]["href"],
                "duplicate_etag": fresh["duplicate"]["etag"],
                "merged": merged_payload,
            },
        ),
        200,
        "Reviewed Phase 4C merge",
    )
    merged = merge_result.get("merged") or {}
    if merged.get("uid") != PRIMARY_UID:
        _fail(f"Merge did not retain the selected survivor UID: {merge_result!r}")
    if merged.get("organization") != DUPLICATE_ORG:
        _fail("Merge did not apply the explicitly selected duplicate organization value.")
    normalized_emails = {str(value).casefold() for value in merged.get("emails", [])}
    if MATCH_EMAIL.casefold() not in normalized_emails or EXTRA_EMAIL.casefold() not in normalized_emails:
        _fail(f"Merged survivor did not retain the expected email union: {merged!r}")
    _ok("Reviewed merge preserved the primary UID, unioned fields, and applied the explicit conflict choice")

    _expect_status(
        client.get("/api/carddav/contact", params={"href": fresh["duplicate"]["href"]}),
        404,
        "Superseded duplicate after merge",
    )
    _ok("Superseded duplicate resource is no longer readable after the survivor write succeeded")

    exported = client.get(
        "/api/carddav/contact/export",
        params={"href": fresh["primary"]["href"]},
    )
    if exported.status_code != 200:
        _fail(f"Merged survivor export returned HTTP {exported.status_code}: {exported.text[:500]}")
    raw = exported.text
    for extension in (PRIMARY_EXTENSION, DUPLICATE_EXTENSION):
        if extension not in raw:
            _fail(f"Merged raw VCF did not preserve tested passthrough property {extension!r}.")
    _ok("Raw export preserved the tested unknown extension properties from both source vCards")

    survivor_etag = merged.get("etag")
    survivor_href = merged.get("href")
    if not isinstance(survivor_etag, str) or not isinstance(survivor_href, str):
        _fail(f"Merged survivor did not return a usable href and ETag: {merged!r}")
    deleted = _expect_status(
        client.delete(
            "/api/carddav/contact",
            params={"href": survivor_href, "etag": survivor_etag},
        ),
        200,
        "Phase 4C survivor cleanup",
    )
    if deleted.get("deleted") is not True:
        _fail(f"Synthetic survivor cleanup returned unexpected response: {deleted!r}")

    _require_clean_baseline(_contacts(client))
    _ok("All disposable Phase 4C contacts were removed after successful validation")
    _logout(client)
    print("\nNEXT  Restore CARDDAV_WRITE_ENABLED=false and SESSION_TTL_SECONDS=28800, restart the backend, then run --stage final.")


def _final(client: httpx.Client) -> None:
    _login(client)
    _validate_book(client)
    contacts = _contacts(client)
    _require_clean_baseline(contacts)
    scan = _scan(client)
    if scan.get("candidate_count") != 0:
        _fail(f"Final one-contact baseline unexpectedly returned duplicates: {scan!r}")
    _ok("Final duplicate scan is clean with the write gate disabled")
    _logout(client)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate GoreeCloud Contacts Milestone 4 Phase 4C against the live local API.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Local GoreeCloud Contacts backend URL (default: %(default)s)",
    )
    parser.add_argument(
        "--stage",
        choices=("baseline", "seed", "review", "write", "final"),
        required=True,
        help="Run one safety-bounded Phase 4C acceptance stage.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    base_url = args.api_base_url.rstrip("/")
    require_write = args.stage in {"seed", "write"}

    try:
        with httpx.Client(base_url=base_url, timeout=20.0, follow_redirects=False) as client:
            _validate_service(client, require_write=require_write)
            if args.stage == "baseline":
                _baseline(client)
            elif args.stage == "seed":
                _seed(client)
            elif args.stage == "review":
                _review(client)
            elif args.stage == "write":
                _write(client)
            else:
                _final(client)
    except (httpx.HTTPError, ValidationFailure) as exc:
        print(f"\nFAIL  {exc}", file=sys.stderr)
        return 1

    print(f"\nPhase 4C {args.stage} stage PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
