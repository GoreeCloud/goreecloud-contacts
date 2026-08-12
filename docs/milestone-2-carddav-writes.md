# Milestone 2 — Conditional CardDAV Writes

## Status

Implementation and automated validation completed on August 12, 2026. Live API write validation against the isolated Radicale test address book also completed successfully. Browser create validation succeeded, but browser edit validation exposed a CardDAV transport failure that must be diagnosed before merge.

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

## Browser Validation

Browser validation began on August 12, 2026 against only the isolated `GoreeCloud Contacts Test` address book.

Observed results:

1. The React interface loaded successfully with the backend online and displayed `Conditional writes enabled`.
2. The address book contained only the existing `Jordan Example` synthetic fixture before the browser write test.
3. Creating `Browser Milestone Two Test` succeeded. The contact count increased from one to two and the new contact appeared with the expected email address and phone number.
4. Editing that browser-created contact to `Browser Milestone Two Updated` did not complete. The editor displayed `Unable to reach the configured CardDAV server.` and the visible contact row remained at its original values.
5. Because the update path performs network work before and after the conditional PUT, the server-side state must be checked before retrying the save. A transport failure after a successful PUT could leave the browser with stale display state even though the CardDAV resource changed.
6. The screenshots also exposed a presentation defect in the four-column contact table: the Actions heading and Edit control wrapped into an implicit second grid row because the base three-column rule overrode the Milestone 2 four-column rule. The branch was updated to give the Milestone 2 table rule sufficient specificity so the action column remains in the intended fourth column.

Browser delete validation remains pending until the update transport failure is diagnosed and the actual CardDAV state of the browser-created contact is confirmed.

## Merge Gate

I will not merge Milestone 2 until the browser edit transport failure is understood, browser create/edit/delete validation passes against the isolated test address book, automated CI passes after any required fixes, and the local write gate is disabled again after validation unless continued write development is required.
