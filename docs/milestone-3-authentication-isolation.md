# Milestone 3 — Authentication and Multi-User Isolation

## Goal

Milestone 3 replaces the single application-wide CardDAV identity with per-user Radicale authentication and enforces strict session-bound access to each user's discovered CardDAV address books.

Radicale remains the authoritative contact store. GoreeCloud Contacts does not create a second contacts database.

## Implemented Foundation

### Radicale-Backed Sign-In

The frontend now provides a username/password sign-in flow. The backend validates those credentials by performing CardDAV discovery with the supplied identity.

Successful authentication creates an opaque server-side session. The browser receives only a random HTTP-only session token.

### Server-Side Sessions

The initial session store is process-local and in memory.

Each session records:

- the authenticated username;
- the CardDAV password required for server-side CardDAV requests;
- a cryptographically random opaque token;
- an expiration timestamp.

The password and token are excluded from the session record representation and are not returned by authentication API responses.

Session endpoints:

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

All CardDAV data routes now require an authenticated session.

### Per-User CardDAV Clients

Every protected request constructs a CardDAV client from the authenticated session's credentials. The backend no longer uses `CARDDAV_USERNAME`, `CARDDAV_PASSWORD`, or a globally configured address-book home path for normal application access.

The protected environment now supplies the CardDAV service endpoint rather than one shared CardDAV identity.

### Application-Level Collection Isolation

The CardDAV client discovers address books from the authenticated user's current principal and `addressbook-home-set`.

Before contact operations are performed, the application verifies that:

- a selected address book exactly matches a discovered address book for the current session;
- a contact path is a `.vcf` resource beneath one of those discovered address books;
- the target remains on the configured CardDAV server origin;
- normalized, percent-decoded paths remain inside the authorized collection boundary.

This application-level authorization supplements Radicale's own permissions.

### Existing Write Protections Preserved

Milestone 2 conditional writes remain unchanged in principle:

- create requires `If-None-Match: *`;
- update and delete require `If-Match` with the current ETag;
- stale writes remain conflict failures;
- `CARDDAV_WRITE_ENABLED` still defaults to `false`.

Authentication does not automatically enable writes.

## Automated Test Coverage Added

The branch adds tests for:

- opaque session creation;
- password/token exclusion from session representations;
- successful login, session retrieval, and logout;
- invalid CardDAV credential rejection;
- authentication requirements on CardDAV routes;
- rejection of an address book outside the authenticated user's discovered scope;
- rejection of a contact resource outside the authenticated user's discovered scope;
- preservation of existing conditional create/update/delete behavior.

## Validation Still Required Before Merge

- GitHub Actions backend tests must pass.
- Frontend lint and production build must pass.
- Live login must be tested against the isolated `goreecloud-contacts-test` Radicale principal.
- The browser must confirm that the isolated `GoreeCloud Contacts Test` address book loads only after login.
- Logout must remove access to CardDAV routes without restarting the backend.
- Session expiration behavior must be validated.
- A second isolated Radicale principal should be created or selected for a negative multi-user test proving one user cannot select another user's address book through GoreeCloud Contacts.
- The local write gate must remain disabled unless a controlled synthetic write validation is intentionally performed.

## Current Limitation

The session store is process-local. Backend restarts invalidate all sessions, and multiple backend workers would not share session state. This is acceptable for the current development milestone but must be reviewed before production deployment.

## Merge Gate

Do not merge Milestone 3 until automated CI succeeds and the required isolated live multi-user validation is complete.
