# Production Readiness — API Response Privacy and Caching

## Status

This increment strengthens the GoreeCloud Contacts API privacy boundary by preventing browser and intermediary caching of application API responses.

It addresses a source-level privacy requirement. It does **not** complete the separate production logging, reverse-proxy, browser-acceptance, or deployment gates.

## API response cache policy

Every response whose path begins with `/api/` now receives:

- `Cache-Control: no-store, max-age=0`
- `Pragma: no-cache`
- `Expires: 0`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`

The policy applies to:

- successful contact and address-book responses;
- authentication/session responses;
- health/readiness responses;
- validation and authorization errors;
- CSRF-origin rejections;
- VCF and duplicate-workflow endpoints;
- future endpoints added beneath the `/api/` namespace unless deliberately changed through a reviewed source update.

The backend applies the headers centrally rather than relying on every route to repeat them.

## Browser request behavior

The shared frontend API helper now also sets the Fetch API request cache mode to `no-store`.

The response headers remain the authoritative server-side privacy control. The browser request setting is an additional client-side safeguard and does not replace server policy.

## Why this matters

GoreeCloud Contacts responses may contain personal information such as names, phone numbers, email addresses, postal addresses, birthdays, notes, organizations, and contact metadata. Authentication endpoints also expose authenticated-state metadata.

These responses should not be retained as reusable cached representations by a browser or intermediary merely because they were retrieved with an HTTP GET.

The no-store policy reduces avoidable persistence outside the authoritative Radicale/CardDAV store and the active browser application state.

## Scope boundary — access logs remain separate

This increment does **not** claim that production request logging is solved.

Some current API operations include CardDAV resource hrefs and ETags in query strings. A default web-server or reverse-proxy access log may record the full request target, including those query values. Resource hrefs and ETags are not authentication credentials, but they are application metadata and may reveal user/collection/resource identifiers that should not be retained unnecessarily.

The final production runtime must therefore explicitly validate its access-log behavior. The production logging decision must ensure that query strings and other contact-related request metadata are either:

- not logged;
- appropriately redacted; or
- retained only when a documented operational/security requirement justifies them and the resulting log is protected accordingly.

Because the final GoreeCloud Contacts server/reverse-proxy deployment has not yet been approved, this source increment deliberately does not invent a Uvicorn, Docker, Caddy, or other runtime logging configuration.

## Error-response boundary

The current CardDAV adapter already converts upstream failures into bounded application messages such as authentication failure, authorization denial, resource not found, precondition conflict, generic upstream status, or transport unavailability. The adapter does not return upstream response bodies, CardDAV passwords, or raw HTTP exception objects to the browser.

This increment preserves that behavior and ensures those error responses are also non-cacheable.

## Automated validation

Automated backend tests verify that:

- successful API responses receive the complete privacy-header set;
- authentication-state responses receive the same policy;
- authorization/error responses receive the same policy;
- early CSRF-origin rejection responses receive the same policy;
- the policy remains scoped to `/api/` and is not silently applied to unrelated non-API routes.

Frontend lint and production build validate the shared `cache: 'no-store'` Fetch configuration.

Exact-head GitHub Actions validation is required before this source increment is accepted.

## Remaining production privacy gates

Production approval still requires separate evidence for, as applicable:

- final access-log and application-log content/retention behavior;
- reverse-proxy/server logging and redaction configuration;
- production secret injection and recovery;
- production browser acceptance, including logout and browser-state behavior;
- private publication and TLS behavior;
- monitoring output privacy;
- backup/recovery handling of application configuration and any session state;
- production-family onboarding and access review.

Production remains unapproved until those target-environment controls are implemented and validated.
