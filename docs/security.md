# Security

## Purpose

I use this document to define the security requirements and implemented security boundaries for GoreeCloud Contacts.

## Credential Handling

I will not store active passwords, CardDAV credentials, private keys, tokens, recovery information, or session values in source control or ordinary documentation.

GoreeCloud Contacts does not use one application-wide CardDAV username and password for normal user access. Each user enters an approved Radicale/CardDAV username and password at sign-in.

The backend validates those credentials directly against Radicale. CardDAV credentials remain backend-only and are protected as part of the encrypted server-side session record. They are not returned to the browser, written into the browser session cookie, or intentionally written to logs.

## Authentication

`POST /api/auth/login` validates supplied credentials by performing CardDAV discovery against the configured Radicale service. A successful login creates a cryptographically random opaque session token.

The browser receives only that token in a cookie configured as:

- `HttpOnly`;
- `SameSite=Strict`;
- path `/`;
- an explicit maximum age derived from `SESSION_TTL_SECONDS`;
- `Secure` when `SESSION_COOKIE_SECURE=true`.

`GET /api/auth/session` reports only authenticated state, username, and session expiration. `POST /api/auth/logout` invalidates the backend session and removes the cookie.

Expired, missing, or unknown session tokens cannot access protected CardDAV routes.

Authentication abuse is bounded by configurable sign-in throttling. Development/test memory sessions use a process-local throttle. When the shared SQLite session backend is selected, the throttle uses the same protected SQLite database so all backend workers enforce one attempt budget instead of maintaining independent per-process counters. The normalized username is converted to a one-way SHA-256 digest before persistence; passwords, session tokens, request bodies, contact data, and client addresses are not retained by the throttle. Exhausted attempt budgets return HTTP 429 with `Retry-After`, and a successful login resets the identity window across workers.

## Authorization and Multi-User Isolation

Authentication does not grant unrestricted CardDAV access.

For every signed-in session, GoreeCloud Contacts builds a CardDAV client using only that session user's credentials. Address books are discovered from that user's CardDAV principal and `addressbook-home-set`.

The backend independently enforces application-level scope:

- a requested address-book URL must exactly match an address book discovered for the authenticated session;
- a requested contact resource must be a `.vcf` path beneath an authorized address book;
- CardDAV resource URLs must remain on the configured CardDAV origin;
- percent-decoded and normalized paths are checked before authorization decisions;
- requests outside the authenticated session's scope fail instead of being forwarded as arbitrary CardDAV requests.

Radicale access controls remain an additional authorization layer rather than the only isolation control.

## Conditional Write Protection

The existing write-integrity rules remain active.

- Create uses `If-None-Match: *`.
- Update and delete require the current ETag through `If-Match`.
- CardDAV HTTP 412 precondition failures become API HTTP 409 conflicts.
- `CARDDAV_WRITE_ENABLED` remains an explicit safety gate and defaults to disabled.
- Duplicate merge has its own explicit mutation gate.

Authentication does not bypass mutation safety gates.

## Session Storage

The production-shaped runtime supports encrypted shared SQLite-backed sessions so multiple configured backend workers can share application sessions. Session encryption key material is supplied separately from ordinary environment configuration and is not embedded in the image.

The shared login-throttle table is colocated in the protected session database but stores only one-way username digests and attempt timestamps. It does not store credentials or contact content. SQLite write transactions serialize check-and-record decisions across workers, preventing the production two-worker runtime from multiplying the configured attempt allowance.

The production container uses a dedicated writable data location for session and throttle state while the remainder of the container filesystem is read-only. CI verifies non-root runtime identity, secret-file permissions, dependency consistency, hardened container startup, production-shaped session configuration, process-local throttle behavior, shared cross-instance throttle behavior, reset behavior, expiry, and plaintext-username non-persistence.

Actual target-environment backup, restore, key rotation, rollback, worker behavior, throttle behavior through the final reverse-proxy path, and recovery validation remain production-approval gates.

## Cross-Site Request Protection

The application uses a narrowly configured frontend origin, credentialed CORS, `SameSite=Strict` session cookies, and optional strict Origin/Referer enforcement for unsafe requests through `CSRF_ORIGIN_CHECK_ENABLED`.

Production deployment requires HTTPS, `SESSION_COOKIE_SECURE=true`, and target-environment validation of the Origin/Referer policy through the final private-publication path.

## API Privacy Controls

API responses receive privacy-oriented headers including `Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`.

Production access logging is configured to minimize query-string exposure so CardDAV resource identifiers and other request parameters are not routinely copied into access logs.

## Production Browser Security Policy

The production application entry point applies a same-origin browser-security policy to API responses, HTML, the web app manifest, and static assets. The local development entry point does not apply this production-only policy.

The production policy includes:

- a strict `Content-Security-Policy` limited to same-origin scripts, styles, fonts, connections, and manifest resources;
- framing blocked through CSP `frame-ancestors 'none'` and `X-Frame-Options: DENY`;
- objects and workers blocked;
- `Cross-Origin-Opener-Policy: same-origin`;
- `Cross-Origin-Resource-Policy: same-origin`;
- `Referrer-Policy: no-referrer`;
- `X-Content-Type-Options: nosniff`;
- a restrictive `Permissions-Policy` disabling camera, geolocation, microphone, payment, and USB access.

The CSP intentionally does not permit `unsafe-inline`, `unsafe-eval`, or generic external `http:`/`https:` source schemes. CI unit-tests the policy and the production-image smoke test fetches real HTML and API responses from the hardened container and requires the expected headers to be present.

The runtime smoke test verifies each required CSP directive individually rather than depending on directive ordering. It also explicitly rejects `unsafe-inline` and `unsafe-eval`. Exact head `f95aec7c52822e2d79409e97c579cd9447359ca7` passed Continuous Integration run #137 / workflow run `32450163475`, including production-image construction, hardened-container startup, and the runtime browser-security header checks.

HTTP Strict Transport Security is intentionally not emitted by application middleware. HTTPS termination and HSTS remain responsibilities of the validated Caddy/private-publication layer so local HTTP development and internal health probes are not unintentionally upgraded by application code.

## Network Exposure

The production application is intended to use the approved GoreeCloud private-service publication model. Backend application ports must not be directly exposed outside the approved reverse-proxy/network boundary.

## Dependency and Runtime Security

CI performs frontend dependency auditing, backend project and locked-runtime dependency auditing, backend tests across supported Python versions, frontend validation/lint/build, production Compose validation, production image construction, package consistency checks, and hardened-container smoke testing.

The production container runs as a dedicated non-root UID/GID, drops Linux capabilities, enables `no-new-privileges`, limits PIDs, uses a read-only root filesystem in the production-shaped test, and keeps writable state in explicitly scoped tmpfs/data locations.

Source and CI validation do not replace target-environment validation.

## Logging

Logs must minimize personal contact data. Routine logs should not include full vCards, contact notes, addresses, phone numbers, email addresses, credentials, session values, or sensitive query strings unless a narrowly scoped troubleshooting need requires temporary protected diagnostic output.

## Development and Testing

Automated tests and local development use synthetic contact data and non-production credentials. Production-family contact collections must not be used as a convenient development dataset.

Authentication tests must verify that passwords and opaque tokens are not exposed through normal API responses or object representations. Authorization tests must include attempts to select another user's address book or contact path.

## Security Review Gate

Production deployment still requires target-environment review and evidence for authentication, authorization, shared-worker throttle enforcement through the deployed runtime, session protection, CSRF enforcement, Caddy/HTTPS/HSTS behavior, logging, request limits, container permissions, network exposure, monitoring, backup, restoration, key rotation, rollback, DAVx5 coexistence, browser/mobile acceptance, and controlled production-family onboarding.
