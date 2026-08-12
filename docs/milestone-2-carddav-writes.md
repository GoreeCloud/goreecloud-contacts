# Milestone 2 — Conditional CardDAV Writes

## Status

Implementation and automated validation completed on August 12, 2026. Live API write validation against the isolated Radicale test address book also completed successfully. Browser-based create, edit, and delete validation remains required before merge.

## Purpose

I use this milestone to add controlled create, update, and delete operations to GoreeCloud Contacts without allowing stale browser state to silently overwrite contact changes made by DAVx5 or another CardDAV client.

## Safety Model

CardDAV writes remain disabled by default. I must explicitly set `CARDDAV_WRITE_ENABLED=true` in the protected local or deployment environment before the API will permit a write.

The write layer uses HTTP conditional requests:

- Create uses `If-None-Match: *` so a generated resource path cannot replace an existing contact.
- Update requires the ETag returned when the contact was read and sends it through `If-Match`.
- Delete also requires the current ETag and sends it through `If-Match`.
- A CardDAV HTTP `412 Precondition Failed` response is converted into an API HTTP `409 Conflict` instead of retrying or overwriting the resource.

This design makes concurrent modifications visible to the user. The application does not automatically force a stale write.

## API Scope

Milestone 2 adds:

- `POST /api/carddav/contacts?address_book_href=...`
- `PUT /api/carddav/contact?href=...&etag=...`
- `DELETE /api/carddav/contact?href=...&etag=...`

Existing discovery and read endpoints remain unchanged.

## vCard Scope

The write serializer intentionally supports the fields already exposed by the Milestone 1 interface:

- UID
- formatted name
- multiple email addresses
- multiple phone numbers

Create operations generate a new UUID-based vCard UID and resource name. Update operations preserve the existing UID when it is available.

Broader contact fields remain future work.

## User Interface

The frontend adds a controlled contact editor for:

- Creating a synthetic contact.
- Editing a contact that has an ETag.
- Deleting a contact that has an ETag.
- Entering multiple email addresses and phone numbers, one value per line.
- Displaying server-side conflict or write errors without forcing an overwrite.

When the write safety gate is disabled, the application remains in read-only safety mode and the create/edit controls are unavailable.

## Automated Validation

I completed the Milestone 2 automated validation on August 12, 2026.

Validation results:

- Backend test suite: `9 passed`.
- Existing Starlette `httpx` TestClient deprecation warning remained non-blocking.
- Frontend dependency installation with `npm ci` completed successfully.
- npm reported zero vulnerabilities for the installed frontend dependency set at validation time.
- Frontend lint completed with zero warnings and zero errors.
- Frontend TypeScript and Vite production build completed successfully.
- GitHub Actions continuous integration completed successfully for draft PR #4.

The automated test suite verifies:

- Existing CardDAV discovery and read behavior.
- vCard serialization and parse round-tripping.
- Create requests send `If-None-Match: *`.
- Update requests send `If-Match` and preserve the existing UID.
- Delete requests send `If-Match`.
- CardDAV HTTP `412` responses become explicit conflicts.
- Frontend lint and production build continue to pass.

## Live API Validation

I completed live API write validation against only the dedicated `goreecloud-contacts-test` Radicale identity and the `GoreeCloud Contacts Test` address book.

The validation sequence and results were:

1. Confirmed the application remained read-only while the write safety gate was disabled. `/api/carddav/status` returned `configured: true`, `read_only: true`, and `write_enabled: false`.
2. Enabled `CARDDAV_WRITE_ENABLED=true` only in the protected local `.env`, which remained mode `600`.
3. Restarted the local FastAPI development server and confirmed `/api/carddav/status` returned `write_enabled: true` and `read_only: false`.
4. Created a synthetic `Milestone Two Test` contact through the GoreeCloud Contacts API. The API returned HTTP `201` and Radicale assigned the resource an ETag.
5. Updated the synthetic contact to `Milestone Two Updated` using the original ETag. The API returned HTTP `200`, the UID remained unchanged, and the returned ETag changed.
6. Attempted another update using the stale original ETag. Radicale rejected the conditional request, and the API returned HTTP `409` with a CardDAV precondition-conflict message.
7. Re-read the address book and confirmed the stale update did not overwrite `Milestone Two Updated`.
8. Deleted the synthetic contact using its current ETag. The API returned HTTP `200`.
9. Re-read the address book and confirmed the synthetic Milestone 2 contact was removed.
10. Confirmed the existing `Jordan Example` synthetic fixture remained present and unchanged throughout the test.

The live API validation therefore passed the complete create → update → stale-ETag conflict → delete sequence, preserved the contact UID across update, prevented the stale write from winning, and removed the temporary test contact successfully.

No production family contact collection was used for Milestone 2 validation.

## Remaining Browser Validation

Before merge, I will validate the React interface against the same isolated test address book by:

1. Confirming the interface displays `Conditional writes enabled` while the local write gate is active.
2. Creating a synthetic browser test contact.
3. Editing the browser-created contact and confirming the refreshed contact list shows the updated values.
4. Deleting the browser-created contact through the confirmation flow.
5. Confirming the contact disappears after deletion and `Jordan Example` remains intact.
6. Re-running automated validation if any source code changes are required as a result of browser testing.
7. Disabling the local write gate again after Milestone 2 validation unless continued write development is required.

## Merge Gate

I will not merge Milestone 2 until automated CI passes, the conditional write behavior has been validated against the isolated Radicale test environment, and the browser create/edit/delete flow has been verified successfully.
