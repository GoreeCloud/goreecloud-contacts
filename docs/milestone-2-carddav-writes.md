# Milestone 2 — Conditional CardDAV Writes

## Status

Implementation branch created on August 12, 2026. Automated validation and live Radicale write validation remain required before merge.

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

The Milestone 2 test suite must verify:

- Existing CardDAV discovery and read behavior.
- vCard serialization and parse round-tripping.
- Create requests send `If-None-Match: *`.
- Update requests send `If-Match` and preserve the existing UID.
- Delete requests send `If-Match`.
- CardDAV HTTP `412` responses become explicit conflicts.
- Frontend lint and production build continue to pass.

## Live Validation Plan

Live testing must use only the dedicated `goreecloud-contacts-test` Radicale identity and `GoreeCloud Contacts Test` address book.

The live sequence will be:

1. Confirm the application is still read-only while `CARDDAV_WRITE_ENABLED` is false.
2. Enable the write gate only in the protected local `.env`.
3. Create a new synthetic contact from the browser and confirm Radicale stores it.
4. Edit that synthetic contact and confirm the ETag changes.
5. Simulate a stale ETag and confirm the application reports a conflict instead of overwriting the newer server version.
6. Delete the synthetic contact using its current ETag.
7. Confirm the existing `Jordan Example` fixture remains intact unless deliberately used for a controlled update test.
8. Re-run backend tests, frontend lint, and frontend production build.
9. Disable the write gate again after testing unless continued write development is required.

No production family contact collection will be used for Milestone 2 validation.

## Merge Gate

I will not merge Milestone 2 until automated CI passes and the conditional write behavior has been validated against the isolated Radicale test environment.
