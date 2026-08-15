# GoreeCloud Contacts

GoreeCloud Contacts is my private, self-hosted personal and family contact-management web application. I am building it as a GoreeCloud-native browser interface over standards-based CardDAV while keeping Radicale authoritative.

## Project Status

**Status:** Active development — Milestone 4 Phase 4C duplicate detection and user-reviewed merge is source-complete with isolated live acceptance pending; Phase 4D Glaze UI/readiness refinement is in stacked draft review; production deployment remains unapproved.

Milestones 1–3 established CardDAV discovery, ETag-protected writes, Radicale-backed per-user authentication, opaque server-side sessions, and verified multi-user address-book isolation.

Milestone 4 Phase 4A expanded the structured contact model and browser workflows. Phase 4B added raw VCF import/export and validated portability. Phase 4C adds read-only duplicate suggestions and conflict-safe user-reviewed merge. Phase 4D begins the dedicated Glaze UI, accessibility, and responsive-resilience pass.

Production-readiness work is intentionally separate from product feature completion. Current stacked source increments add fail-closed production HTTPS/Secure-cookie/CSRF requirements, encrypted shared SQLite sessions, liveness/readiness probes, API no-store privacy controls, bounded contact/VCF inputs, dependency vulnerability auditing, and Glaze UI validation. These source controls do not replace target-environment acceptance.

No production family contact data is approved for development or acceptance testing yet.

## Role

I use GoreeCloud Contacts to provide a modern browser-based interface for managing personal and family contacts while preserving CardDAV as the portable synchronization standard.

## Architecture

```text
Approved browser
  |
  | HTTPS / opaque application session
  v
GoreeCloud Contacts frontend + backend
  |
  | CardDAV using the signed-in user's authorized credentials
  v
Radicale
  |
  | CardDAV
  v
DAVx5 and other approved CardDAV clients
```

Radicale remains the authoritative contact store. GoreeCloud Contacts does not create a competing contacts database.

Each user authenticates with an approved Radicale/CardDAV identity. The backend performs CardDAV operations as that user and independently restricts requested address books and contact resources to collections discovered for the authenticated session.

## Technology Direction

- Frontend: React + TypeScript + Vite
- Design language: GoreeCloud Glaze UI
- Backend: Python + FastAPI
- Contact protocol: CardDAV
- Contact format: vCard
- Authoritative contact service: Radicale
- Android synchronization: DAVx5
- Application authentication: Radicale-backed per-user sign-in
- Browser session: opaque HttpOnly cookie; Secure required in production
- Development session backend: in-memory
- Production session backend: shared SQLite with hashed browser-token lookup and encrypted CardDAV credential payload
- Deployment direction: Docker and Docker Compose; final production placement not yet approved
- Private HTTPS gateway: Caddy, subject to final private-publication acceptance
- Development platform: GitHub

Technology selections remain subject to implementation and production-readiness validation.

## Repository Structure

```text
goreecloud-contacts/
├── backend/
│   ├── app/
│   ├── scripts/
│   └── tests/
├── frontend/
│   ├── scripts/
│   └── src/
├── docker/
├── docs/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

Important current records include the Milestone 4 Phase 4A–4D documents and the production-readiness security, session, monitoring, API-privacy, input-bound, and dependency-audit records under `docs/`.

## Development Milestones

### Milestone 1 — Read-Only CardDAV Proof of Concept — Complete

- Implemented the React/TypeScript frontend and FastAPI backend foundation.
- Discovered CardDAV principals, address-book homes, address books, contacts, resource hrefs, and ETags.
- Rendered a responsive browser contact list with search.
- Added dependency locking and GitHub Actions CI.
- Validated the browser-to-Radicale read path with isolated synthetic data.

### Milestone 2 — Conditional CardDAV Writes — Complete

- Added contact creation using `If-None-Match: *`.
- Added ETag-protected updates and deletes using `If-Match`.
- Converted stale CardDAV precondition failures into application conflicts rather than blind overwrites.
- Preserved UIDs during updates.
- Kept mutations behind `CARDDAV_WRITE_ENABLED`.
- Validated controlled synthetic create/update/conflict/delete behavior and restored read-only safety mode afterward.

### Milestone 3 — Authentication and Multi-User Isolation — Complete

- Replaced the application-wide CardDAV identity with per-user Radicale sign-in.
- Added opaque server-side sessions, logout, and expiration handling.
- Kept CardDAV passwords out of browser-readable storage.
- Restricted address-book and contact access to resources authorized for the signed-in user.
- Validated negative two-user isolation with separate synthetic Radicale identities.
- Preserved the write gate and ETag protections.

### Milestone 4 — Expanded Contact Model and Product Workflows — In Progress

#### Phase 4A — Expanded Contact Model — Complete

- Added structured names, organizations, titles, postal addresses, birthdays, websites, notes, categories, favorites, and supported photo-reference awareness.
- Added authenticated full-detail retrieval and expanded create/update serialization.
- Added Contacts/Favorites views, broader search, detail viewing, and expanded editor workflows.
- Passed isolated API/browser validation and merged Phase 4A to `main`.

#### Phase 4B — VCF Import and Export — Complete

- Added raw single-contact and full-address-book VCF export.
- Added VCF 3.0/4.0 preview/import with explicit destination and record selection.
- Preserved unknown raw source properties where practical and generated UIDs only when missing.
- Kept import behind the write gate and conflict-safe create semantics.
- Validated raw VCF round-trip portability through Radicale and merged Phase 4B to `main`.

#### Phase 4C — Duplicate Detection and User-Reviewed Merge — Source Complete; Live Acceptance Pending

- Scans only the selected address book authorized for the signed-in user.
- Suggests duplicate candidates using exact UID and normalized name/email/phone signals with supporting organization/title evidence.
- Never performs an automatic merge or identity decision.
- Lets the user select the survivor and explicitly resolve scalar conflicts.
- Unions/deduplicates multi-value fields and preserves the chosen survivor UID.
- Re-reads both raw resources and verifies both reviewed ETags before mutation.
- Updates the survivor conditionally before conditionally deleting the superseded resource.
- Keeps information rather than attempting unsafe rollback when a post-write delete result is ambiguous.
- Preserves unsupported raw vCard properties from both records where practical.
- Has automated stale-ETag and partial-failure regression coverage.
- Still requires controlled isolated live acceptance, cleanup, and safety-state restoration before Phase 4C can close.

#### Phase 4D — Glaze UI and Product Readiness — In Progress

- Added a dedicated `frontend/src/glaze.css` token and presentation layer.
- Added layered/selectively translucent surfaces, rounded geometry, restrained shadows, semantic colors, and ambient gradients without introducing third-party browser assets.
- Unified VCF and duplicate-management feature surfaces through shared Glaze compatibility tokens.
- Added explicit keyboard `:focus-visible` treatment.
- Added coarse-pointer touch-target improvements.
- Added reduced-motion and reduced-transparency behavior.
- Corrected the mobile breakpoint so Create contact, Contacts/Favorites navigation, address-book selection, and the write-safety indicator remain available instead of disappearing with the desktop sidebar.
- Added a dependency-free Glaze UI source validator and made it a CI gate.
- Added light/dark browser theme-color metadata while retaining operating-system color-scheme behavior.
- Production-representative visual/browser acceptance remains a separate gate.

### Milestone 5 — Production Readiness and Deployment — In Progress; Deployment Not Approved

Source-level controls currently include:

- fail-closed production HTTPS configuration;
- Secure session-cookie requirement;
- centralized Origin/Referer CSRF enforcement for unsafe requests;
- encrypted shared SQLite production sessions with hashed token lookup and key rotation support;
- liveness and dependency-readiness endpoints;
- API/browser no-store privacy behavior;
- bounded contact, duplicate-workflow, and VCF inputs;
- Python and npm dependency vulnerability auditing;
- a narrowly documented temporary `cryptography` advisory exception guarded against use of the affected PKCS#7 decrypt API surface;
- Glaze UI/accessibility/responsive source validation.

The following still require separate evidence before production approval:

- Phase 4C isolated live acceptance and cleanup;
- production-representative authentication/authorization validation;
- final worker/process/session persistence validation on the selected runtime;
- secret injection, ownership, permissions, rotation, and recovery;
- application configuration and authoritative Radicale backup/restore;
- recovery and rollback rehearsal;
- private DNS/Caddy/NetBird/firewall publication validation;
- actual monitoring and alert delivery;
- production logging/redaction and server-level request controls;
- authentication abuse controls appropriate to the final runtime;
- container/operating-system security scanning when a final deployment image/runtime exists;
- production-representative desktop and mobile-browser acceptance;
- DAVx5 coexistence/conflict testing;
- export/portability acceptance;
- controlled production-family onboarding.

## Security and Privacy Rules

I do not commit passwords, active CardDAV credentials, tokens, private keys, session values, or other reusable credentials to this repository.

The browser never receives a user's CardDAV password after sign-in. It holds only a random opaque HttpOnly session token. Production additionally requires a Secure cookie and HTTPS frontend/CardDAV origins.

Development may use the process-local in-memory session backend. Production is required to use the shared SQLite session backend, which stores a SHA-256 digest of the opaque browser token and encrypts the CardDAV username/password payload using protected Fernet key material kept outside the database and source control.

Authentication never grants unrestricted CardDAV access. Every address-book and contact-resource request remains constrained to collections authorized for the signed-in user.

API responses are explicitly marked non-cacheable, and the frontend requests API resources with `cache: 'no-store'`. Contact and credential information must remain minimized in logs, errors, browser state, diagnostics, and monitoring output.

Development and validation use isolated test accounts, test address books, and synthetic contact data whenever practical. Production family contact data is not a development dataset.

## Glaze UI Boundary

Glaze UI is the shared visual and interaction language for GoreeCloud Contacts. Contacts keeps its Google Contacts-inspired product ergonomics without copying proprietary branding.

The Glaze implementation is self-hosted and privacy-conscious. It does not add analytics, advertising, external fonts, remote CSS, or third-party browser scripts. Visual effects remain subordinate to readability, accessibility, performance, and clear interaction states.

## License

GoreeCloud Contacts is licensed under the MIT License. See `LICENSE`.
