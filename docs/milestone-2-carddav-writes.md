# Milestone 2 — Conditional CardDAV Writes

## Status

Milestone 2 implementation and validation completed successfully on August 12, 2026 against the isolated Radicale test environment. Automated tests, live API validation, browser create/edit/delete validation, and restoration of the local read-only safety state all passed.

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
- GitHub Actions continuous integration passed on the Milestone 2 branch after the final validation documentation updates.

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

I completed browser validation on August 12, 2026 against only the isolated `GoreeCloud Contacts Test` address book.

Observed results:

1. The React interface loaded successfully with the backend online and displayed `Conditional writes enabled`.
2. The address book contained only the existing `Jordan Example` synthetic fixture before the browser write test.
3. Creating `Browser Milestone Two Test` succeeded. The contact count increased from one to two and the new contact appeared with the expected email address and phone number.
4. The first browser edit attempt returned `Unable to reach the configured CardDAV server.` The server-side state was checked before retrying and confirmed that the original contact values and original ETag remained intact, so the failed attempt did not modify Radicale.
5. A direct stability probe then read the exact browser-created vCard resource ten consecutive times through the backend CardDAV client. All ten reads succeeded and returned the same ETag, providing no evidence of a persistent DNS, TLS, NetBird, or direct-resource-read failure.
6. The frontend and backend development servers were restarted and verified independently. The frontend returned HTTP `200`, and `/api/carddav/status` again returned `configured: true`, `read_only: false`, and `write_enabled: true`.
7. Retrying the browser edit succeeded. The browser changed the contact to `Browser Milestone Two Updated`, and the backend logged HTTP `200` for the conditional PUT followed by HTTP `200` for the refreshed contact-list read.
8. The updated row displayed `browser-m2-updated@example.test` and `+1-555-0131`, confirming the browser refreshed from the successful server-side update.
9. The four-column contact table fix validated visually: Name, Email, Phone, and Actions remained aligned in one grid row and Edit controls stayed in the intended Actions column.
10. Deleting `Browser Milestone Two Updated` through the browser confirmation flow succeeded. The backend logged HTTP `200` for the ETag-protected DELETE followed by HTTP `200` for the final contact-list refresh.
11. The browser contact count returned from two to one, the browser-created test contact disappeared, and `Jordan Example` remained present with `jordan@example.test` and `+1-555-0100`.

The browser create → edit → delete flow therefore passed, including UI refresh after writes and preservation of the existing synthetic fixture.

## Safety Restoration

After live validation, I restored the protected local environment to its default safety posture:

- `CARDDAV_WRITE_ENABLED=false` was set in the local `.env`.
- The `.env` file remained mode `600`.
- FastAPI was restarted so the updated setting was loaded.
- `/api/carddav/status` returned `configured: true`, `read_only: true`, and `write_enabled: false`.

The local GoreeCloud Contacts development environment therefore ended Milestone 2 in read-only safety mode.

## Merge Gate

All Milestone 2 merge gates passed: automated tests and CI, isolated live API create/update/conflict/delete validation, isolated browser create/edit/delete validation, preservation of the existing synthetic fixture, and restoration of the local write gate to disabled/read-only state.
