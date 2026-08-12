# CardDAV Integration

## Purpose

I use this document to define the CardDAV integration boundary for GoreeCloud Contacts.

## Authoritative Service

Radicale is the authoritative CardDAV server. The application must discover and operate on authorized address books through standards-based CardDAV requests.

## Read Path

The application must:

1. Authenticate successfully.
2. Discover the user's CardDAV home and address books.
3. Enumerate contact resources.
4. Retrieve vCard records.
5. Parse supported contact properties.
6. Preserve resource identifiers and ETags where provided.
7. Render retrieved contacts without altering them.

Milestone 1 completed and live-validated this path with a dedicated synthetic Radicale account and address book.

## Write Path

Write support is conditional and disabled by default.

Create operations must use a unique resource path and `If-None-Match: *`.

Update operations must require the ETag associated with the version the user actually viewed and send that ETag through `If-Match`.

Delete operations must also require the current ETag and send it through `If-Match`.

The application must treat a CardDAV precondition failure as a conflict. It must not automatically remove the precondition, retry as an unconditional write, or silently replace the newer server version.

## Concurrency and Data Integrity

The application must preserve CardDAV resource identity and server-provided ETag information. A stale browser session must not silently overwrite a resource changed by DAVx5, Android Contacts, another browser session, or another standards-compliant CardDAV client.

If a conflict occurs, the user must reload the current server state before attempting another update or delete.

## Write Safety Gate

The backend configuration value `CARDDAV_WRITE_ENABLED` defaults to `false`.

Read operations may remain available while this gate is disabled. Create, update, and delete endpoints must reject writes until the gate is explicitly enabled in the protected environment configuration.

This control is independent from CardDAV credentials and is intended to reduce the risk of accidentally enabling writes against an unintended account or address book.

## Portability

GoreeCloud-specific UI behavior must not make ordinary contact data dependent on a proprietary format. Contacts must remain usable by standards-compliant CardDAV and vCard clients if GoreeCloud Contacts is unavailable or retired.

## Development Data

Real family contact data should not be required for normal development or automated testing. Test fixtures must use synthetic names, phone numbers, addresses, email addresses, and photos.

Live write testing must remain isolated to an approved non-production CardDAV identity and address book until the write path has passed its merge gate.
