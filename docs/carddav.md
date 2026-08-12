# CardDAV Integration

## Purpose

I use this document to define the initial CardDAV integration boundary for GoreeCloud Contacts.

## Authoritative Service

Radicale is the authoritative CardDAV server. The application must discover and operate on authorized address books through standards-based CardDAV requests.

## Initial Proof of Concept

The first CardDAV milestone must demonstrate the following against a controlled test account:

1. Authenticate successfully.
2. Discover the user's CardDAV home and address books.
3. Enumerate contact resources.
4. Retrieve vCard records.
5. Parse common contact properties.
6. Preserve resource identifiers and ETags where provided.
7. Render retrieved contacts without altering them.

Write operations will be added only after the read path is stable and tested.

## Concurrency and Data Integrity

The application must preserve CardDAV resource identity and use server-provided version or ETag information where available. Update and delete operations must avoid silently overwriting a resource that changed after it was read.

## Portability

GoreeCloud-specific UI behavior must not make ordinary contact data dependent on a proprietary format. Contacts must remain usable by standards-compliant CardDAV and vCard clients if GoreeCloud Contacts is unavailable or retired.

## Development Data

Real family contact data should not be required for normal development or automated testing. Test fixtures must use synthetic names, phone numbers, addresses, email addresses, and photos.
