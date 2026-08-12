# Security

## Purpose

I use this document to define the security requirements and implemented security boundaries for GoreeCloud Contacts.

## Credential Handling

I will not store active passwords, CardDAV credentials, private keys, tokens, recovery information, or session values in source control.

GoreeCloud Contacts no longer uses one application-wide CardDAV username and password from `.env`. Each user enters an approved Radicale/CardDAV username and password at sign-in.

The backend validates those credentials directly against Radicale. The plaintext CardDAV password is retained only in backend process memory for the lifetime of the authenticated session because the backend must present the user's credentials to Radicale for later CardDAV requests. It is not returned to the browser, written to the session cookie, persisted to disk, or intentionally written to logs.

## Authentication

`POST /api/auth/login` validates the supplied user credentials by performing CardDAV discovery against the configured Radicale service. A successful login creates a cryptographically random opaque session token.

The browser receives only that token in a cookie configured as:

- `HttpOnly`
- `SameSite=Strict`
- path `/`
- an explicit maximum age derived from `SESSION_TTL_SECONDS`
- `Secure` when `SESSION_COOKIE_SECURE=true`

`GET /api/auth/session` reports only the authenticated state, username, and session expiration time. `POST /api/auth/logout` invalidates the backend session and removes the cookie.

Expired, missing, or unknown session tokens cannot access protected CardDAV routes.

## Authorization and Multi-User Isolation

Authentication does not grant unrestricted CardDAV access.

For every signed-in session, GoreeCloud Contacts builds a CardDAV client using only that session user's credentials. Address books are discovered from that user's CardDAV principal and `addressbook-home-set`.

The backend then independently enforces application-level scope:

- a requested address-book URL must exactly match one of the address books discovered for the authenticated session;
- a requested contact resource must be a `.vcf` path beneath one of those discovered address books;
- CardDAV resource URLs must remain on the configured CardDAV origin;
- percent-decoded and normalized paths are checked before authorization decisions;
- requests outside the authenticated session's scope fail with authorization errors instead of being forwarded as arbitrary same-origin CardDAV requests.

Radicale access controls remain an additional authorization layer rather than the only isolation control.

## Conditional Write Protection

The Milestone 2 write-integrity rules remain active.

- Create uses `If-None-Match: *`.
- Update and delete require the current ETag through `If-Match`.
- CardDAV HTTP 412 precondition failures become API HTTP 409 conflicts.
- `CARDDAV_WRITE_ENABLED` remains disabled by default.

Authentication does not bypass the write safety gate.

## Session Storage Limitation

Milestone 3 uses process-local in-memory session storage. This is intentional for the current development foundation.

Consequences:

- a backend restart logs out all users;
- sessions are not shared between multiple backend processes or replicas;
- the current session store is not yet suitable for a horizontally scaled production deployment.

Before production deployment, I must either confirm that a single-process session model is acceptable or replace it with an approved protected shared session store while preserving the rule that CardDAV passwords are never placed in browser-readable storage.

## Cross-Site Request Protection

The application uses a narrowly configured frontend origin, credentialed CORS, and `SameSite=Strict` session cookies. Production deployment must use HTTPS and set `SESSION_COOKIE_SECURE=true`.

A production security review must determine whether an additional explicit CSRF token or Origin/Referer enforcement is required for the final deployment model.

## Network Exposure

The production application is intended to use the approved GoreeCloud private-service publication model. Backend application ports must not be exposed directly to the public Internet.

## Logging

Logs must minimize personal contact data. Routine logs should not include full vCards, contact notes, addresses, phone numbers, email addresses, credentials, or session values unless a narrowly scoped troubleshooting need requires temporary protected diagnostic output.

## Development and Testing

Automated tests and local development must use synthetic contact data and non-production credentials. Production contact collections must not be used as a convenient development dataset.

Authentication tests must verify that passwords and opaque tokens are not exposed through normal API responses or object representations. Authorization tests must include attempts to select another user's address book or contact path.

## Security Review Gate

Production deployment requires review of authentication, authorization, session protection, CSRF protections, dependency security, CardDAV conflict behavior, logging, container permissions, network exposure, backup, restoration, rollback, and multi-user validation with isolated non-production accounts.
