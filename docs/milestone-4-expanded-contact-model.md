# Milestone 4 — Expanded Contact Model and Product Workflows

## Status

**In progress — Phase 4A expanded vCard model implemented; automated validation and live read/detail validation passed. Live write and browser mutation validation remain pending.**

Milestone 4 extends GoreeCloud Contacts beyond the Milestone 1–3 name/email/phone foundation while preserving Radicale as the authoritative CardDAV store, per-user isolation, conditional ETag writes, and the local write safety gate.

## Milestone goals

Milestone 4 is intentionally divided into smaller validation increments so a large contact-model change does not combine every product workflow into one unreviewable release.

### Phase 4A — Expanded contact model

Implementation scope:

- Structured vCard names (`N`) with family, given, additional, prefix, and suffix components.
- Organization (`ORG`).
- Job title (`TITLE`).
- Multiple postal addresses (`ADR`) with CardDAV/vCard type values.
- Birthday (`BDAY`).
- Multiple websites (`URL`).
- Notes (`NOTE`).
- Categories (`CATEGORIES`).
- GoreeCloud favorite metadata through `X-GOREECLOUD-FAVORITE`.
- Photo-reference awareness (`PHOTO`) with automatic browser rendering limited to embedded `data:image/...` values so ordinary remote photo URLs are not fetched without user action.
- A dedicated authenticated contact-detail API route.
- Expanded create/update serialization while preserving the existing UID and ETag protections.
- Favorites filtering and broader search over names, organizations, titles, categories, email addresses, and phone numbers.
- Read-only contact-detail viewing even while the CardDAV write gate is disabled.
- Expanded browser editor when writes are explicitly enabled.

### Phase 4B — Portable VCF workflows

Planned scope:

- VCF export for one contact.
- VCF export for an address book or selected contacts.
- VCF import preview.
- Validation of malformed or unsupported records before import.
- Explicit destination address-book selection.
- Conflict-safe resource creation without replacing existing CardDAV resources.

### Phase 4C — Duplicate detection and merge

Planned scope:

- Candidate detection using normalized names, email addresses, and phone numbers.
- User-reviewed duplicate groups rather than automatic destructive merges.
- Merge preview showing retained and discarded values.
- ETag-protected merge writes.
- Deletion of superseded resources only after the merged resource is confirmed written successfully.

### Phase 4D — Product and Glaze UI refinement

Planned scope:

- Continue responsive and dark-mode improvements.
- Align the Contacts experience with the GoreeCloud Glaze UI design language.
- Improve keyboard navigation, focus state, accessible labels, error presentation, and narrow-screen layouts.
- Evaluate richer photo workflows after privacy, payload-size, and CardDAV interoperability behavior are validated.

## Phase 4A implementation details

### Backend models

`backend/app/models.py` now distinguishes between a list-oriented contact summary and an expanded contact detail model.

The summary intentionally keeps large detail-only values such as notes, postal addresses, and photo data out of the normal address-book list response. It exposes organization, title, categories, favorite state, and photo presence because those values support list rendering, filtering, and search.

The detail model adds structured name components, addresses, birthday, websites, notes, and the optional photo value.

### vCard parser and serializer

`backend/app/vcard.py` now parses and serializes the Phase 4A fields while retaining UID, formatted-name, email, and telephone behavior.

The parser now handles escaped separators for structured names, addresses, and categories instead of splitting already-unescaped values. This is important for values such as a category containing a literal comma.

Favorites are stored as the GoreeCloud extension:

```text
X-GOREECLOUD-FAVORITE:TRUE
```

This extension is deliberately namespaced as a non-standard `X-` property. Other CardDAV clients may ignore it while still preserving it. Interoperability must be validated before treating favorites as portable across every client.

### Contact-detail API

Phase 4A adds:

```text
GET /api/carddav/contact?href=<authorized-vcf-resource>
```

The route requires an authenticated GoreeCloud Contacts session. The backend applies the same per-user CardDAV authorization boundary used by update and delete operations before reading the resource.

### Writes

The existing create and update routes now serialize the expanded Phase 4A write model.

Existing protections remain unchanged:

- Create uses `If-None-Match: *`.
- Update uses the currently supplied ETag through `If-Match`.
- The existing UID is retained during update.
- CardDAV HTTP 412 is translated to application HTTP 409.
- Writes remain impossible unless `CARDDAV_WRITE_ENABLED=true` is explicitly configured.

### Browser behavior

The frontend now provides:

- Contacts and Favorites views.
- Broader search coverage.
- A contact detail panel available in read-only mode.
- Organization/title context in the contact list.
- Expanded edit fields when writes are enabled.
- Multiple postal-address editing.
- Favorite-state editing.
- Embedded data-image display where present.
- Remote photo loading disabled by default to avoid silent third-party network requests from contact metadata.

## Security and privacy boundaries

Milestone 3 session and multi-user isolation rules remain mandatory and are not weakened by the expanded model.

The browser does not receive CardDAV credentials. Contact-detail requests use the authenticated backend session and the backend reconstructs the CardDAV client from the server-side session record.

The new detail endpoint must never be treated as an arbitrary CardDAV fetch endpoint. Its href remains subject to same-origin CardDAV URL validation, `.vcf` validation, and per-user address-book authorization.

Production family contact data remains outside Milestone 4 development validation until the production-readiness milestone is approved.

## Known compatibility limitations

Phase 4A does not claim lossless preservation of every possible vCard extension used by Apple, Google, Android vendors, or other CardDAV clients. The application still serializes the fields it understands when a contact is edited.

Particular follow-up areas include:

- Vendor-specific labels and relationship properties.
- Binary vCard 3.0 photo encodings versus vCard 4 URI-style photos.
- Custom ringtone or messaging metadata.
- Phonetic-name fields.
- Anniversary and relationship fields.
- Exact preservation of unknown `X-` properties.

These limitations must be considered before production-family contact editing is approved.

## Required automated validation

Before Phase 4A is considered complete:

- Backend vCard parsing tests must cover expanded fields and escaped delimiters.
- Expanded serialization must round-trip through the parser.
- Existing CardDAV authorization tests must remain green.
- Existing conditional-write tests must remain green.
- Existing authentication/session tests must remain green.
- Frontend lint must pass.
- Frontend production build must pass.

Exact-head GitHub Actions run #23 passed at `b49e876988519cbd762eb01963112f56dec224e5`, including backend tests, both live-helper syntax checks, frontend lint, and the production frontend build.

## Required live validation

Live validation must continue to use the isolated `goreecloud-contacts-test` principal and synthetic data.

### Read/detail validation — Passed

On August 12, 2026, `backend/scripts/validate_milestone4_live.py --mode read` passed with `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800`.

The live check confirmed:

- backend health
- CardDAV configured with the write gate safely disabled
- Radicale-backed login for `goreecloud-contacts-test`
- discovery of `GoreeCloud Contacts Test`
- retention of the existing `Jordan Example` synthetic fixture
- successful authenticated retrieval through the expanded contact-detail endpoint
- expanded model response shapes
- session invalidation after validation

Browser validation also confirmed that the Contacts and Favorites navigation rendered, Jordan Example remained visible, the read-only safety notice remained active, and the expanded Jordan Example detail panel opened successfully while mutations remained gated.

### Write validation — Pending

For approved write validation, enable the write gate only temporarily and create a new synthetic Phase 4 contact containing representative expanded fields. Validate create, detail read, update, stale-ETag rejection, and delete. After validation, restore:

```text
CARDDAV_WRITE_ENABLED=false
SESSION_TTL_SECONDS=28800
```

Do not use real family contacts as the Milestone 4 validation dataset.

## Completion gate

Phase 4A is complete only after automated CI and isolated live validation pass and the protected local write gate is restored to false.

The full Milestone 4 remains open until VCF portability, duplicate/merge workflows, and the planned product/UI refinement phases are completed or explicitly moved to a later milestone.
