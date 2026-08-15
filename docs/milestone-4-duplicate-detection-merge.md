# Milestone 4 Phase 4C — Duplicate Detection and User-Reviewed Merge

**Implementation in progress. Automated and isolated live validation are required before merge.**

## Goal

Phase 4C adds duplicate-contact discovery and an explicit review-and-merge workflow without changing the GoreeCloud Contacts data authority. Radicale/CardDAV remains the single authoritative contact store, and no second contact database or hidden canonical-contact table is introduced.

The feature must suggest possible duplicates without automatically deciding that two people are the same person. Every actual merge remains a user-reviewed, write-gated CardDAV operation.

## Scope and safety boundaries

- Duplicate scanning is restricted to one address book selected and authorized for the current authenticated session.
- Scanning and merge preview are read-only and remain available when `CARDDAV_WRITE_ENABLED=false`.
- The actual merge endpoint remains blocked unless `CARDDAV_WRITE_ENABLED=true`.
- Production family contacts are not approved for Phase 4C development or acceptance testing.
- Live acceptance must use only the isolated `goreecloud-contacts-test` identity, the `GoreeCloud Contacts Test` address book, the retained Jordan Example fixture, and disposable synthetic duplicate contacts.
- The normal development state must be restored to `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800` after any controlled write validation.

## Duplicate candidate detection

Phase 4C evaluates contact pairs only within the selected authorized address book. Candidate signals currently include:

- Exact UID match.
- Normalized email-address match.
- Normalized telephone-number match.
- Normalized exact formatted-name match.
- Matching organization as supporting evidence when the name also matches.
- Matching title as supporting evidence when the name also matches.

Email matching is case-insensitive after Unicode normalization. Telephone matching removes formatting characters and requires at least seven digits before it is used as a duplicate signal. Name, organization, and title matching use case-insensitive Unicode-normalized text with punctuation and whitespace normalized.

The backend returns a score and a `high`, `medium`, or `low` confidence label for prioritization. These values are review aids, not automatic identity decisions. A candidate is never merged merely because its score is high.

## User-reviewed merge proposal

The user chooses which contact resource will survive. The other contact remains untouched until the final merge action succeeds.

The initial merge proposal follows these rules:

- The selected primary contact is the survivor and retains its resource path and UID.
- Blank primary scalar fields may be filled from the duplicate.
- When both contacts contain different nonblank scalar values, the preview reports an explicit conflict instead of silently replacing the primary value.
- The browser lets the user choose the primary or duplicate value for each reported scalar conflict.
- Emails, telephone numbers, websites, categories, and postal addresses are combined and deduplicated.
- Favorite state is retained if either reviewed contact is a favorite.
- The proposed result is shown before mutation.

The user may swap which contact is primary and regenerate the proposal before merging.

## Raw vCard portability behavior

A normal structured contact update rebuilds the vCard from fields understood by GoreeCloud Contacts. Phase 4C therefore uses a dedicated raw-merge path to reduce avoidable loss of properties that are not part of the structured model.

The merged survivor is rebuilt from the reviewed structured payload while:

- Retaining the primary contact UID.
- Retaining the primary contact vCard version.
- Carrying forward unsupported raw property lines from both reviewed source vCards where possible.
- Deduplicating identical passthrough lines.

This is a best-effort interoperability boundary, not a claim that every possible vCard construct is losslessly mergeable. Grouped properties, parameters on modeled properties, and companion metadata can have relationships that are not fully represented by the current structured parser. Phase 4C must not claim complete lossless preservation of arbitrary grouped or vendor-specific metadata.

Embedded `data:image/...` PHOTO content remains outside the current lossless structured-write boundary. A duplicate pair containing embedded photo data must not be merged through Phase 4C unless that limitation is explicitly handled; HTTP(S) photo references remain the supported structured photo-write model.

Raw VCF export remains the preferred portability path for retaining source data outside the understood application field model.

## Conflict-safe CardDAV mutation

A merge is deliberately more defensive than an ordinary single-contact edit because it mutates two resources.

Before any mutation, the backend:

1. Re-authorizes both contact resources against the selected address book and authenticated session.
2. Retrieves the raw current primary and duplicate vCards.
3. Requires both current CardDAV ETags to exactly match the ETags from the reviewed preview.
4. Aborts with a conflict if either contact changed after review.

If both ETags still match, the backend:

1. Writes the reviewed merged vCard to the primary resource using `If-Match` with the reviewed primary ETag.
2. Re-reads the primary resource to confirm the merged survivor and obtain its new ETag.
3. Deletes the superseded duplicate resource using `If-Match` with the reviewed duplicate ETag.

The duplicate is therefore never deleted before the merged survivor is confirmed written.

If the duplicate changes before deletion, the survivor remains safely merged and the duplicate is left in place for a fresh review. If a transport or server failure makes the DELETE outcome ambiguous, Phase 4C deliberately does not roll the survivor backward: a rollback could discard merged information if the server actually completed the deletion but the success response was lost. Instead, the operation returns an explicit partial-state error and requires the address book to be refreshed and both resources inspected before any retry.

This failure model prefers duplicated information over possible information loss.

## API surface

Phase 4C introduces:

- `GET /api/carddav/duplicates?address_book_href=...` — read-only candidate scan.
- `POST /api/carddav/duplicates/preview` — read-only user-review proposal for two selected resources.
- `POST /api/carddav/duplicates/merge` — write-gated, ETag-protected reviewed merge.

All endpoints require an authenticated GoreeCloud Contacts session. Address-book and contact-resource authorization continues to use the existing per-user CardDAV discovery boundary.

## Browser workflow

The Phase 4C panel allows the signed-in user to:

- Run a read-only duplicate scan for the currently selected address book.
- Review why each candidate pair was suggested.
- Choose which contact should survive.
- Review the proposed merged contact.
- Resolve conflicting scalar values explicitly.
- Swap the primary/survivor before mutation.
- Keep the final merge control disabled while the CardDAV write safety gate is active.
- Refresh contacts and duplicate candidates after a successful merge.

No external photo URI is automatically loaded merely because a duplicate candidate or merge preview contains a photo reference.

## Required automated validation

Before Phase 4C can be considered complete, automated validation must prove at minimum:

- Normalized email and telephone matching identify strong duplicate candidates.
- Name-only matches remain lower-confidence suggestions rather than automatic merges.
- Multi-value fields are unioned and deduplicated predictably.
- Conflicting scalar fields are surfaced for review.
- The survivor UID remains unchanged.
- Raw passthrough properties from both source vCards are preserved where supported by the Phase 4C raw merge strategy.
- Duplicate merge writes use current ETags and stale review state is rejected before mutation.
- The duplicate resource is deleted only after the survivor update succeeds.
- An ambiguous duplicate-delete failure does not roll the merged survivor backward or silently claim completion.
- Backend test suite, frontend lint, and frontend production build pass on the exact final pull-request head.

## Required isolated live acceptance

The acceptance requirements below are grouped into read-only and controlled-write categories. Operational execution is intentionally divided into the safer `baseline` → `seed` → `review` → `write` → `final` helper stages, with a fixture-scoped `cleanup` recovery stage available after an interrupted synthetic write. The exact procedure is documented in `docs/milestone-4-phase4c-live-acceptance-runbook.md`.

The live helper defaults to a loopback API target, requires an explicit override for an approved isolated non-loopback backend, refuses backends reporting `prod` or `production`, never accepts credentials in the API URL, and limits recovery cleanup to the retained Jordan UID plus the two fixed disposable Phase 4C fixture UIDs. Final validation also checks that a newly issued application session reflects the restored `SESSION_TTL_SECONDS=28800` value.

### Read-only acceptance

With `CARDDAV_WRITE_ENABLED=false`:

- Sign in only as `goreecloud-contacts-test`.
- Confirm the selected address book is `GoreeCloud Contacts Test`.
- Confirm the retained Jordan Example fixture remains present.
- Run duplicate scan and merge preview without any CardDAV mutation.
- Confirm the browser clearly distinguishes suggestion confidence from user approval.
- Confirm merge remains disabled while the write gate is false.

### Controlled synthetic write acceptance

Only after read-only acceptance passes:

- Create two disposable synthetic contacts designed to produce a deterministic duplicate match.
- Include complementary fields so the proposed union can be verified.
- Include at least one deliberate scalar conflict so user-reviewed selection can be verified.
- Include a harmless synthetic unknown vCard extension where practical so raw passthrough preservation can be checked by export after merge.
- Verify a stale ETag on either reviewed resource rejects the merge before mutation.
- Refresh and repeat review with current ETags.
- Perform exactly one approved merge and confirm the chosen primary UID survives.
- Confirm combined fields match the reviewed proposal and the superseded resource is gone.
- Raw-export the survivor and verify the expected tested passthrough extension remains where supported.
- Remove all disposable Phase 4C contacts after validation, leaving Jordan Example as the only retained fixture.
- Restore `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800`.
- Restart/re-authenticate as needed and confirm the final browser state is read-only safety mode.

## Completion gate

Phase 4C must remain a draft development increment until automated validation, exact-head CI, isolated live acceptance, cleanup, safety-state restoration, documentation reconciliation, and final review are complete.

Production-family contact use, production deployment, shared/durable session storage, final CSRF protection, private-service publication, backup/recovery validation, monitoring, and broader production-readiness work remain separate gates.
