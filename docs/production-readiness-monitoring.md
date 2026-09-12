# Production Readiness — Liveness and Dependency Readiness

## Status

This increment establishes source-level health signals suitable for future GoreeCloud Contacts monitoring without claiming that the application has been deployed or that production monitoring has been configured.

The production-readiness specification requires monitoring and health visibility. The repository previously exposed only `/api/health`, which always returned `status=ok` when the FastAPI process could answer. That behavior was useful as a development liveness check but could not distinguish a running process from an application that could no longer use its session store or reach the configured CardDAV service.

## Health endpoint roles

### `GET /api/health`

Retained as a backward-compatible liveness endpoint for existing development checks.

It confirms that the backend process can answer HTTP requests. It does not claim that dependencies are available.

### `GET /api/health/live`

Explicit process-liveness endpoint.

It returns HTTP 200 while the FastAPI process is responsive. Monitoring systems may use this signal to distinguish process failure from dependency-readiness failure.

### `GET /api/health/ready`

Dependency-readiness endpoint.

It returns HTTP 200 only when both of the following are ready:

- the configured session store can perform its required health operation;
- the configured CardDAV endpoint is reachable through the expected WebDAV transport path.

It returns HTTP 503 when either required dependency is unavailable or when CardDAV is not configured.

## Session-store readiness

The in-memory development store reports ready while the process is operating.

The SQLite production store verifies that it can:

- open the configured shared database;
- acquire an immediate SQLite transaction;
- access the expected `sessions` table through a no-row update operation;
- roll the transaction back without mutating session content.

A missing/broken session table, inaccessible database, SQLite error, or filesystem/open failure causes the session-store readiness check to fail.

This check is intended to detect failures relevant to authentication state without exposing session counts, usernames, tokens, encrypted credentials, database paths, or encryption-key information.

## Credential-free CardDAV readiness

The CardDAV readiness probe deliberately does **not** use a user CardDAV username or password.

It sends a minimal depth-zero WebDAV `PROPFIND` to the configured CardDAV base URL asking for `current-user-principal`.

The following outcomes are considered evidence that the CardDAV/WebDAV transport is reachable:

- a successful 2xx WebDAV/HTTP response;
- a redirect successfully followed to a 2xx response;
- HTTP 401 or 403, because a private CardDAV service may correctly require authentication before answering the request.

The following cause readiness failure:

- transport, DNS, TLS, or connection errors;
- HTTP 404 or 405 endpoint mismatch;
- HTTP 5xx server errors;
- missing CardDAV configuration.

The probe timeout is bounded to a maximum of five seconds so a failed dependency cannot hold the readiness endpoint open for the full normal CardDAV request timeout.

## Privacy boundary

Readiness output is intentionally narrow. It reports only:

- overall `ready` or `not_ready` state;
- `session_store` as `ok` or `unavailable`;
- `carddav` as `ok`, `not_configured`, or `unavailable`.

It does not expose:

- CardDAV hostnames or URLs;
- contact records;
- usernames;
- session identifiers;
- credential values;
- database paths;
- encryption state or keys;
- internal exception text.

This keeps monitoring useful without turning the health endpoint into an infrastructure or personal-data disclosure surface.

## Automated validation

Automated tests verify:

- `/api/health` remains compatible and returns process liveness;
- `/api/health/live` returns process liveness independently of dependency state;
- readiness succeeds only when both the session store and CardDAV transport are ready;
- readiness returns HTTP 503 for an unavailable session store;
- readiness returns HTTP 503 when CardDAV is not configured;
- readiness returns HTTP 503 when CardDAV transport is unavailable;
- readiness output contains only the approved narrow status fields;
- the SQLite health check detects a broken session-store schema;
- the CardDAV probe sends no Authorization header or user credential;
- HTTP 401/403 from the private CardDAV endpoint are treated as reachable/auth-required rather than as transport failure;
- endpoint mismatch, server errors, and transport failures fail closed.

Exact-head GitHub Actions validation is required before this source increment is accepted.

## Remaining monitoring gate

This increment creates monitoring-compatible signals; it does not configure production monitoring.

Target-environment work must still establish and validate, as applicable:

- the final monitoring service and monitor names;
- private-network reachability to the liveness/readiness endpoint;
- check intervals and timeout values;
- notification routing and out-of-band alert behavior;
- alert behavior for process failure versus dependency failure;
- monitoring during restart, upgrade, rollback, CardDAV outage, and session-store failure tests;
- documentation/inventory updates for the final production monitor configuration.

Production approval remains blocked until monitoring is actually configured and validated together with the other production-readiness gates.
