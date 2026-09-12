# Production Readiness — Environment Identity and API Documentation Surface

## Purpose

This record documents source-level safeguards that prevent an invalid application-environment label from silently bypassing production controls and that reduce unnecessary production API discovery surface.

GoreeCloud Contacts remains a private, self-hosted application whose authoritative contact data stays in Radicale/CardDAV. This change does not approve a production runtime, hostname, proxy topology, or production-family contact use.

## Environment identity is security-relevant

`APP_ENV` is not cosmetic. Production behavior depends on recognizing the application as production so the backend can enforce stronger security requirements.

The allowed application environments are now explicitly limited to:

- `development`
- `test`
- `production`

Values are normalized by trimming whitespace and case-folding before validation. For example, ` PRODUCTION ` is accepted and normalized to `production`.

Any other value fails configuration validation. Examples such as `prod`, `prodution`, `staging`, `local`, or an empty value are not silently treated as development.

This fail-closed behavior matters because a misspelled production environment must not bypass the existing production requirements for:

- Secure session cookies;
- Origin/Referer CSRF enforcement;
- HTTPS frontend origin;
- configured HTTPS CardDAV origin;
- shared SQLite session storage;
- protected session-encryption key material;
- an absolute session-database path.

A future environment name must be added deliberately to the validated application model together with an explicit decision about which security profile it should inherit.

## Central production classification

`Settings.is_production` is the single source-level production classification used by the configuration validator and production-only API-surface decision.

This avoids repeating free-form string comparisons in unrelated modules and reduces the chance that one production safeguard recognizes a different environment spelling than another.

## FastAPI documentation surface

FastAPI's interactive API documentation and machine-readable schema are useful development and test tools, but they are not required for the production Contacts user experience.

When `APP_ENV` is `development` or `test`, the backend retains:

- `/docs` — Swagger UI;
- `/redoc` — ReDoc;
- `/openapi.json` — OpenAPI schema.

When `APP_ENV=production`, all three routes are absent.

The production application does not add a runtime override that re-enables these routes. An administrator who needs API documentation can use the repository, a development/test environment, or an intentionally reviewed future administrative mechanism instead of expanding the ordinary production HTTP surface by default.

## What this change does not do

Disabling documentation routes is defense in depth. It does not replace:

- application authentication and authorization;
- private DNS and NetBird boundaries;
- Caddy/firewall controls;
- HTTPS;
- CSRF protection;
- CardDAV resource authorization;
- ETag conflict protection;
- logging/privacy controls;
- server/proxy request limits;
- runtime monitoring and recovery.

The API endpoints required by the Contacts frontend remain available according to their existing authentication and authorization rules.

## Glaze UI boundary

This increment does not modify frontend presentation or Glaze UI source.

The existing Glaze UI design language, accessibility behavior, responsive behavior, light/dark behavior, and source validation remain inherited unchanged. Production API documentation removal affects only FastAPI's backend development/documentation routes and does not change the GoreeCloud Contacts browser interface.

## Automated validation

`backend/tests/test_security.py` now validates that:

- supported environment names normalize predictably;
- unknown and misspelled environment names fail validation;
- secure production configuration remains accepted;
- insecure production configuration continues to fail closed;
- API documentation remains enabled for development and test;
- the development application still exposes `/docs`, `/redoc`, and `/openapi.json`;
- production documentation configuration removes all three routes.

The full repository CI remains responsible for backend regression tests, dependency auditing, Phase 4C helper syntax validation, frontend dependency auditing, Glaze UI validation, linting, and production frontend build validation.

## Production boundary

This source control closes only the environment-identity typo bypass and default FastAPI documentation exposure at the application layer.

Production approval still requires the independently documented live acceptance, runtime, proxy, logging, backup/recovery, monitoring, secret lifecycle, publication, browser, DAVx5 coexistence, portability, and controlled onboarding evidence.
