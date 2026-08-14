# GoreeCloud Contacts

GoreeCloud Contacts is my private, self-hosted personal and family contact-management web application. I am building it as a GoreeCloud-native web interface for contacts stored through CardDAV.

## Project Status

**Status:** Active development — Milestone 4 Phase 4C duplicate detection and user-reviewed merge implementation; isolated live validation pending

Milestones 1 and 2 provide Radicale address-book discovery, contact listing and search, and guarded create, update, and delete operations with ETag-based conflict protection.

Milestone 3 adds per-user Radicale authentication, opaque server-side sessions, strict application-level address-book isolation, logout/session-expiration behavior, and live negative two-user authorization validation.

Milestone 4 Phase 4A expands the contact model with structured names, organization/title, addresses, birthdays, websites, notes, categories, favorites, HTTP(S) photo-reference awareness, full contact-detail retrieval, and expanded browser workflows. Phase 4B adds raw VCF import/export and validated portability through Radicale. Both phases are merged to `main`. Phase 4C is implementing read-only duplicate suggestions plus an explicit, ETag-protected, user-reviewed merge workflow. Development and validation continue to use isolated non-production identities and synthetic contact data; production family contact data is not yet approved for use.

## Role

I will use GoreeCloud Contacts to provide a modern browser-based interface for managing personal and family contacts while preserving CardDAV as the portable synchronization standard.

## Architecture

The application model is:

```text
Approved browser
  |
  | HTTPS / opaque application session
  v
GoreeCloud Contacts
  |
  | CardDAV using the signed-in user's credentials
  v
Radicale
  |
  | CardDAV
  v
DAVx5
  |
  v
Android Contacts Provider
```

Radicale remains the authoritative CardDAV service. GoreeCloud Contacts does not create a competing contact database for ordinary contact data.

Each user authenticates with an approved Radicale/CardDAV identity. The backend performs CardDAV operations as that user and independently restricts requested address books and contact resources to collections discovered for the authenticated session.

## Technology Direction

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Contact protocol: CardDAV
- Contact format: vCard
- Authoritative contact service: Radicale
- Android synchronization: DAVx5
- Application authentication: Radicale-backed per-user sign-in
- Application sessions: opaque server-side sessions
- Deployment: Docker and Docker Compose
- Reverse proxy: Caddy
- Development platform: GitHub

Technology selections remain subject to implementation and production-readiness validation.

## Repository Structure

```text
goreecloud-contacts/
├── frontend/
├── backend/
├── docker/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── carddav.md
│   ├── development.md
│   ├── security.md
│   ├── milestone-1-carddav-poc.md
│   ├── milestone-2-carddav-writes.md
│   ├── milestone-3-authentication-isolation.md
│   ├── milestone-4-expanded-contact-model.md
│   ├── milestone-4-vcf-import-export.md
│   └── milestone-4-duplicate-detection-merge.md
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Development Milestones

### Milestone 1 — Read-Only CardDAV Proof of Concept — Complete

- Implemented the React/TypeScript frontend and FastAPI backend foundation.
- Authenticated to an isolated Radicale test account through protected local configuration.
- Discovered CardDAV principals, address-book homes, and address books.
- Retrieved synthetic contacts and preserved resource hrefs and ETags.
- Parsed common vCard fields.
- Rendered a responsive browser contact list with local search.
- Added dependency locking and GitHub Actions continuous integration.
- Validated the complete browser-to-Radicale read path without production family contact data.

### Milestone 2 — Conditional CardDAV Writes — Complete

- Added controlled contact creation using `If-None-Match: *`.
- Added ETag-protected contact updates and deletes using `If-Match`.
- Converted stale CardDAV precondition failures into application conflicts instead of blind overwrites.
- Added guarded browser create, edit, and delete controls.
- Preserved contact UIDs during updates.
- Added vCard serialization for formatted name, multiple email addresses, and multiple phone numbers.
- Validated create, update, stale-ETag conflict, and delete behavior with isolated synthetic data.
- Restored `CARDDAV_WRITE_ENABLED=false` after validation.

### Milestone 3 — Authentication and Multi-User Isolation — Complete

- Replaced the single application-wide CardDAV identity with per-user Radicale sign-in.
- Validated user credentials through CardDAV discovery.
- Added opaque HTTP-only server-side sessions.
- Kept CardDAV passwords out of browser-readable storage and source control.
- Required authentication for CardDAV application routes.
- Constructed CardDAV clients from the authenticated session user's credentials.
- Restricted address-book access to collections discovered for the signed-in user.
- Restricted contact-resource access to `.vcf` resources beneath those authorized collections.
- Preserved the Milestone 2 write gate and ETag protections.
- Added explicit logout and session-expiration handling.
- Added credential-safe live validation for authenticated CardDAV behavior.
- Validated a retained synthetic primary fixture through `goreecloud-contacts-test`.
- Validated negative two-user isolation with `goreecloud-contacts-isolation-test`; the second user cannot discover the primary test address book and receives HTTP 403 when explicitly selecting it.
- Validated session expiration with a temporary five-second TTL and restored the normal 28,800-second development TTL afterward.
- Confirmed `CARDDAV_WRITE_ENABLED=false` remained the live safety state throughout authentication validation.

### Milestone 4 — Expanded Contact Model and Product Workflows — In Progress

#### Phase 4A — Expanded Contact Model — Complete

- Added structured names, organizations, titles, postal addresses, birthdays, websites, notes, categories, favorites, and HTTP(S) photo-reference awareness where supported.
- Added a full authenticated contact-detail endpoint while preserving per-user CardDAV authorization.
- Expanded create/update serialization while retaining UID and ETag protections.
- Added Contacts and Favorites views, broader search, read-only detail viewing, and expanded write-enabled editor workflows.
- Added expanded parser/serializer tests and credential-safe live read/write validation tooling.
- Passed isolated live read/detail validation using `goreecloud-contacts-test` with `CARDDAV_WRITE_ENABLED=false`.
- Passed controlled synthetic live create/detail/update/stale-ETag/delete validation with an HTTP(S) photo reference.
- Passed browser create, Favorites filtering, expanded edit, unfavorite, and delete validation using a disposable synthetic contact while preserving the retained Jordan Example fixture.
- Restored `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800` after live mutation validation.
- Corrected structured API validation-error presentation after browser validation exposed `[object Object]` for FastAPI/Pydantic detail arrays.
- Final exact-head CI passed and Phase 4A was squash-merged to `main` as `1e2675390e06e9485bf664b53b0552c2e4575cd4`.

#### Phase 4B — VCF Import and Export — Complete

- Implemented single-contact and full address-book VCF export using raw CardDAV vCard data.
- Implemented VCF 3.0/4.0 import preview and validation before any mutation.
- Required explicit destination address-book selection and selected preview records.
- Preserved unknown source properties where possible and generated a UID only when missing.
- Kept actual import behind `CARDDAV_WRITE_ENABLED` and created new resources with `If-None-Match: *`.
- Passed 27 backend tests, frontend lint, frontend production build, implementation-head CI, isolated live acceptance, and final exact-head CI.
- Passed isolated read-only export/preview, unsupported-version rejection, malformed-input rejection, controlled synthetic import, raw VCF round-trip preservation, and cleanup validation.
- Confirmed the tested unknown `X-GOREECLOUD-TEST` property and source UID survived import through Radicale and subsequent raw export.
- Restored `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800` after controlled validation and confirmed Jordan Example remained the only retained test contact.
- Phase 4B was squash-merged to `main` as `eead31afb86894fcf5ed44c32ba7cbd8c5fa30a0`.

#### Phase 4C — Duplicate Detection and Merge — In Progress

- Added read-only duplicate-candidate detection using exact UID plus normalized names, emails, and telephone numbers, with organization/title as supporting signals.
- Added confidence/score presentation as a review aid without automatic identity decisions or automatic merges.
- Added user-reviewed merge previews, survivor selection, primary/duplicate value choices for scalar conflicts, and multi-value field unions.
- Added raw passthrough-property preservation from both source vCards where possible while retaining the chosen survivor UID.
- Added write-gated, dual-ETag validation before mutation, conditional survivor update, and conditional duplicate deletion only after the survivor is confirmed written.
- Added partial-failure handling that prefers duplicate retention over possible information loss when duplicate deletion cannot be confirmed.
- Added the responsive Phase 4C browser review panel without automatically loading external photo URLs.
- Backend automated validation currently passes 34 tests with the two existing nonblocking warnings; frontend lint and production build pass.
- Isolated read-only and controlled synthetic live acceptance remain required before Phase 4C can be completed or merged.

#### Phase 4D — Product and Glaze UI Refinement

- Continue responsive, dark-mode, keyboard, accessibility, and error-state refinement.
- Align GoreeCloud Contacts with the GoreeCloud Glaze UI design language.
- Refine category, favorite, and photo workflows after interoperability/privacy validation.
- Normalize editor helper text and placeholders to the final supported photo-reference model.

### Milestone 5 — Production Readiness and Deployment

- Complete authentication, authorization, session, and security review.
- Decide and validate the production session-storage model.
- Validate CSRF protections for the final deployment architecture.
- Build and validate the Docker deployment.
- Validate backup and restoration requirements.
- Publish through the approved private Caddy/DNS/NetBird service model.
- Add monitoring and operational validation.
- Document rollback and recovery procedures.
- Do not use production family contacts until the required production gates are complete.

## Security Rules

I will not commit passwords, active CardDAV credentials, tokens, private keys, session values, or other reusable credentials to this repository.

The browser must never receive a user's CardDAV password after sign-in. The current Milestone 3 session model keeps the password only in backend process memory while the browser holds a random opaque HTTP-only session token.

Authentication does not grant unrestricted CardDAV access. Every address-book and contact request must remain within the collections authorized for the signed-in user.

Development and validation must use isolated test accounts, test address books, and synthetic contact data whenever practical. Production family contact data must not be used as a convenient development dataset.

## License

GoreeCloud Contacts is licensed under the MIT License. See `LICENSE`.
