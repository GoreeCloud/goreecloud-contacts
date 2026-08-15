# Production Readiness — Browser and Configuration Security

## Status

This increment implements source-level security controls for two GoreeCloud Contacts production-readiness gates: secure production session-cookie configuration and final browser CSRF protection by trusted Origin/Referer enforcement.

It does **not** approve GoreeCloud Contacts for production deployment or production-family contact use. The broader production-readiness checklist remains open.

## Production configuration fail-closed behavior

When `APP_ENV=production`, application startup now refuses configuration that does not satisfy all of the following source-enforced requirements:

- `SESSION_COOKIE_SECURE=true`.
- `CSRF_ORIGIN_CHECK_ENABLED=true`.
- `FRONTEND_ORIGIN` is one HTTPS origin with no path, query, fragment, or embedded credentials.
- `CARDDAV_BASE_URL` is configured and uses HTTPS.

Development remains intentionally compatible with local HTTP and may keep the CSRF origin check disabled while using isolated synthetic data. Production cannot silently inherit those development defaults.

## CSRF decision

The selected browser CSRF control for this increment is strict request-origin validation rather than a synchronizer token.

When `CSRF_ORIGIN_CHECK_ENABLED=true`, every `POST`, `PUT`, `PATCH`, and `DELETE` request is rejected with HTTP 403 unless browser provenance matches the configured `FRONTEND_ORIGIN`.

Validation order is:

1. Use the `Origin` header when present and require it to be an exact HTTP(S) origin matching `FRONTEND_ORIGIN` after scheme/host normalization.
2. If `Origin` is absent, use the origin portion of `Referer` as a fallback.
3. Reject the mutation when neither header is available or when either indicates another origin.

This applies centrally at the FastAPI application boundary, so it covers authentication mutations, ordinary CardDAV writes, VCF imports, duplicate merges, and future unsafe-method routes without relying on each route author to remember a separate CSRF dependency.

The existing session cookie remains `HttpOnly` and `SameSite=Strict`; production additionally requires the `Secure` flag.

## Security boundaries

Origin/Referer validation is a CSRF control, not an XSS defense and not a replacement for authentication or authorization. Existing per-user Radicale authentication, opaque session tokens, address-book isolation, write gating, and ETag preconditions remain required.

The configured trusted origin is explicit. Suffix, substring, and lookalike hostnames are not accepted. A request from `https://contacts.goreecloud.com.attacker.example` is not equivalent to `https://contacts.goreecloud.com`.

No CardDAV password, session token, private key, API token, or other reusable credential is introduced by this increment.

## Automated validation

The production-security tests cover:

- accepted secure production configuration;
- fail-closed rejection when Secure cookies are disabled;
- fail-closed rejection when CSRF origin checking is disabled;
- fail-closed rejection of an HTTP production frontend origin;
- fail-closed rejection of missing or insecure production CardDAV configuration;
- rejection of missing, hostile, and lookalike origins for browser mutations;
- acceptance of the exact trusted Origin;
- acceptance of a same-origin Referer fallback;
- continued availability of safe GET requests without mutation-origin headers.

Exact-head GitHub Actions validation is required before this increment can be accepted.

## Production-readiness gates still open

The following remain separate blockers and are not satisfied by this source change:

- Phase 4C isolated live acceptance and cleanup.
- Final production session-storage/worker model; the current session store remains process-local and backend restart invalidates sessions.
- Production-representative multi-user authentication and authorization validation.
- Backup and restoration of Radicale contacts/configuration and any required Contacts application state.
- Recovery and rollback procedures.
- Approved private publication through DNS, Caddy, NetBird, and firewall boundaries.
- Monitoring and health visibility.
- Production secret/credential storage, permissions, rotation, and recovery.
- Upgrade and rollback validation.
- Production-representative browser acceptance.
- DAVx5 and other approved client coexistence/conflict validation.
- Final data-export and portability acceptance.

Production approval must remain fail-closed until those applicable gates have separate evidence.
