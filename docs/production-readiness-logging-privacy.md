# Production Readiness — Logging and Browser-Error Privacy

## Purpose

This document records the source-level logging and error-disclosure protections currently implemented for GoreeCloud Contacts. It is intentionally limited to behavior controlled by the application repository.

GoreeCloud Contacts processes private contact data and CardDAV resource metadata. The project specification requires minimizing exposure of contact data and credentials in logs, errors, browser state, diagnostics, and monitoring output. The GoreeCloud Privacy by Default standard also requires the lowest useful normal logging level and rejects unnecessary request-body, response-body, credential, token, cookie, and detailed activity logging.

## Current source-level protections

### API response privacy

All `/api/` responses continue to receive:

- `Cache-Control: no-store, max-age=0`
- `Pragma: no-cache`
- `Expires: 0`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`

These controls reduce browser caching and referrer leakage. They do not replace private-network or application authorization controls.

### Uvicorn access-log query minimization

The application installs `QueryStringRedactionFilter` from `backend/app/logging_privacy.py` on the `uvicorn.access` logger when the application module is loaded and reapplies the same idempotent installation during FastAPI lifespan startup.

The two installation points cover both normal CLI startup, where Uvicorn configures logging before loading the application, and programmatic startup patterns that may import the application before server logging is reconfigured.

The filter removes the query component from Uvicorn's normal access-log request target before the record is formatted.

For example, an incoming request target conceptually shaped like:

`/api/carddav/contact?href=<resource>&etag=<etag>`

is represented in the normal Uvicorn access log as:

`/api/carddav/contact`

The actual ASGI request is not changed. Route validation, CardDAV authorization, ETag checks, and application behavior continue to receive the original request.

The filter is deliberately narrow:

- it only modifies Uvicorn access-log formatting arguments;
- it preserves the HTTP method, route path, protocol version, client address already included by Uvicorn, and response status;
- it does not log replacement values;
- it does not inspect or retain removed query data;
- configuration is idempotent so repeated application imports or startup hooks do not stack duplicate filters.

This protects the existing Phase 4C local acceptance helper as well as normal development requests from routine Uvicorn query-string logging.

## Browser-facing CardDAV errors

CardDAV exception translation is now centralized in `backend/app/carddav_errors.py`.

Controlled failure classes retain the minimum useful user-facing semantics:

- authentication failure → HTTP 401;
- authorization failure → HTTP 403;
- stale-write or precondition conflict → HTTP 409;
- missing resource → HTTP 404.

Unexpected `CardDavError` failures are returned as HTTP 502 with the generic browser message:

`CardDAV request could not be completed.`

The generic fallback deliberately does not reflect the raw exception text into the browser. This reduces the chance that an upstream URL, implementation detail, parser detail, internal resource identifier, or future transport diagnostic is exposed by a new CardDAV failure path.

The shared translator is used by the primary contact routes, VCF routes, duplicate routes, and the generic login failure path where applicable. Centralization reduces the chance that one feature later develops a weaker error-disclosure policy than the others.

## What this does not control

Application-side Uvicorn filtering is not a substitute for target-runtime logging policy.

Before production approval, the selected deployment must separately validate every logging layer that can observe the request, including as applicable:

- Caddy;
- container runtime logs;
- systemd or another service supervisor;
- host logging/journaling;
- monitoring and log shipping;
- intrusion-detection or security tooling;
- any future load balancer or reverse proxy.

The production path must not assume that because Uvicorn removes a query string, another proxy or monitoring layer does the same.

## Production logging requirements

The final runtime should use the lowest useful normal level and must not enable routine logging of:

- request bodies;
- response bodies;
- passwords;
- authentication payloads;
- `Cookie` or `Set-Cookie` values;
- session tokens;
- CardDAV Basic Authentication values;
- private encryption keys;
- full VCF/contact content;
- unnecessary search terms;
- detailed per-contact activity beyond an approved operational requirement.

If access logging is enabled at Caddy or another proxy, its format must be reviewed against the actual Contacts routes. Query strings, sensitive headers, and cookies must not be retained merely because the logging platform supports them.

Temporary diagnostic logging requires a defined purpose, restricted access, a start and end point, and a review/removal decision after troubleshooting.

## Retention boundary

This repository does not select a production log-retention period because the final Contacts runtime and logging destination are not yet approved.

A production retention value must be chosen only after the target host, operational monitoring requirements, storage location, backup behavior, and privacy impact are known. Indefinite retention is not an acceptable default.

## Automated validation

`backend/tests/test_logging_privacy.py` validates that:

- a query-bearing Uvicorn access-log record loses the complete query component;
- representative CardDAV href and ETag values are absent after formatting;
- a queryless request path remains unchanged;
- application import installs the filter;
- application lifespan startup reapplies the filter after simulated logger reconfiguration;
- repeated installation is idempotent.

`backend/tests/test_carddav_errors.py` validates that:

- controlled CardDAV failure classes keep their expected HTTP semantics;
- unexpected CardDAV exception text is not reflected to the browser.

These tests validate source behavior only. They do not prove Caddy, Docker, host, monitoring, or production log-retention behavior.

## Remaining production gate

Before GoreeCloud Contacts can be approved for production, logging acceptance still requires target-environment evidence that:

1. the active Caddy/reverse-proxy access-log format is known;
2. query strings are omitted or redacted where they could contain CardDAV resource metadata;
3. cookies, authorization values, request bodies, response bodies, and contact content are not logged by default;
4. application/server log levels are appropriate for normal production use;
5. monitoring does not ingest unnecessary personal contact data;
6. retention and deletion behavior are defined;
7. diagnostic logging can be enabled and removed deliberately without exposing reusable secrets;
8. negative validation confirms representative resource identifiers and reusable secrets do not appear in retained logs.

Until that target-runtime evidence exists, this increment improves source-level privacy and structure but does not close the production logging gate.
