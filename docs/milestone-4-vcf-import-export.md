# Milestone 4 Phase 4B — VCF Import and Export

## Status

**Implementation in progress. Automated and live validation are required before merge.**

Phase 4B adds portable VCF workflows to GoreeCloud Contacts without changing the authoritative-data model. Radicale/CardDAV remains authoritative; GoreeCloud Contacts does not introduce a second contacts database.

## Goals

Phase 4B provides:

- Single-contact VCF export.
- Full address-book VCF export.
- VCF import preview before any CardDAV mutation.
- Explicit destination address-book selection.
- User selection of previewed valid records.
- Conflict-safe creation with `If-None-Match: *`.
- Preservation of source vCard text and unknown properties during raw import/export where possible.
- UID generation only when an imported vCard has no UID.

Duplicate detection and merge remain Phase 4C work.

## Import boundaries

The initial Phase 4B importer:

- accepts vCard 3.0 and 4.0;
- limits submitted VCF text to 5,000,000 characters and the browser file picker to 5 MB;
- rejects malformed record boundaries, unsupported vCard versions, and records without a usable formatted name;
- previews missing UIDs as warnings and generates a UID only during import;
- warns about embedded `data:image/...` photos because the current Radicale/vobject path may not preserve them losslessly;
- does not silently overwrite an existing CardDAV resource.

Actual import remains blocked unless `CARDDAV_WRITE_ENABLED=true`. Preview and export remain available while the write safety gate is disabled.

## API surface

Phase 4B adds:

```text
GET  /api/carddav/contact/export?href=<authorized-vcf-resource>
GET  /api/carddav/address-book/export?address_book_href=<authorized-collection>
POST /api/carddav/import/preview
POST /api/carddav/import
```

All routes require the existing authenticated GoreeCloud Contacts session. Export routes reuse the existing per-user CardDAV resource authorization boundary. Import requires an explicitly authorized destination address book.

## Conflict-safe import

Imported contacts are written to newly generated `.vcf` resource paths beneath the selected authorized address book. Each create request uses:

```text
If-None-Match: *
```

This prevents an import from replacing an existing CardDAV resource at the generated path.

A batch is validated before the first write. If a later CardDAV failure occurs after earlier records were created, the importer makes a best-effort rollback of contacts created by that batch using their returned ETags.

## Portability behavior

Export returns raw CardDAV vCard data rather than rebuilding each contact from GoreeCloud's understood field model. Raw export avoids intentionally dropping unknown vendor-specific or extension properties.

Import also preserves the supplied record text wherever possible. The only intentional content addition is a generated UID when the source record has no UID.

This approach improves portability but does not claim perfect interoperability for every vCard extension. Radicale/vobject behavior and downstream clients remain part of live validation.

## Required automated validation

Before live import testing:

- VCF record splitting and malformed-boundary tests must pass.
- vCard 3.0 and 4.0 acceptance must be covered.
- unsupported-version rejection must be covered.
- UID generation must preserve unknown fields.
- address-book export must preserve raw unknown fields.
- import creation must prove `If-None-Match: *`.
- existing backend tests must remain green.
- frontend lint and production build must pass.

## Required live validation

Live validation must use only the isolated `goreecloud-contacts-test` account and synthetic contacts.

Read-only validation should prove:

- single-contact export;
- full test-address-book export;
- exported VCF parses as expected;
- import preview works while writes remain disabled;
- malformed/unsupported imports are rejected without writes.

Controlled write validation should temporarily enable the write gate and prove:

- previewed synthetic VCF import into the explicit test address book;
- generated resource does not replace the retained Jordan Example fixture;
- imported fields round-trip through Radicale;
- cleanup of imported synthetic contacts;
- restoration of `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800`.

Production family contacts remain outside Phase 4B development validation.
