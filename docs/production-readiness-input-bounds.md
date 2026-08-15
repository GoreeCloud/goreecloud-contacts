# Production Readiness — Input and Import Bounds

## Status

This increment adds explicit application-level bounds to user-controlled GoreeCloud Contacts payloads and resource identifiers that previously relied on only list-count limits or broader request limits.

The goal is to make accepted production input deliberate and predictable without changing ordinary contact-management behavior or the authoritative Radicale/CardDAV data model.

## Shared CardDAV resource limits

Resource identifier limits are now defined once in the shared application model layer and reused by the primary CardDAV routes, raw VCF export routes, and duplicate-review/merge models:

- address-book and contact-resource hrefs: 4,096 characters;
- reviewed/write ETags: 1,024 characters.

These limits are intentionally far above normal CardDAV identifiers while preventing unbounded query-string or JSON values from reaching authorization, URL resolution, export, conflict-checking, and conditional-write code.

The primary CardDAV routes now apply the href bound to:

- contact listing;
- contact detail retrieval;
- contact creation destination selection;
- contact update and delete resource selection;
- single-contact VCF export;
- full-address-book VCF export.

Contact update and delete query parameters also apply the shared ETag bound. This closes the earlier inconsistency where duplicate-workflow identifiers were bounded but the primary CardDAV and VCF-export query identifiers were not.

## Contact write limits

`ContactWriteRequest` limits both the number of repeated fields and the maximum length of each individual value.

Current write-side limits are:

- formatted name: 512 characters;
- email address: 320 characters each, up to 50 values;
- telephone number: 128 characters each, up to 50 values;
- organization: 1,024 characters;
- title: 1,024 characters;
- postal addresses: up to 20 structured addresses with the existing bounded address components;
- birthday: 64 characters;
- website: 2,048 characters each, up to 50 values;
- note: 10,000 characters;
- category: 256 characters each, up to 100 values;
- photo reference: 4,096 characters and still restricted to HTTP(S) URI references.

These constraints apply to application write requests, including reviewed duplicate merges because duplicate merge writes use the same `ContactWriteRequest` model.

They do not retroactively reject longer unknown/raw properties merely because a source vCard contains them. Raw VCF export remains the portability path for information outside the structured write model.

## Duplicate-workflow identifier limits

Duplicate review and merge requests use the same shared CardDAV resource limits:

- address-book hrefs to 4,096 characters;
- contact-resource hrefs to 4,096 characters;
- reviewed ETags to 1,024 characters.

## VCF import limits

The existing VCF text limit remains 5,000,000 characters.

This increment additionally establishes a maximum of 5,000 vCard records per VCF import/preview operation. The same constant also limits the selected-index list used for controlled import.

The record-count check occurs while splitting the VCF file, so a file containing many tiny records cannot bypass the intended operation-count bound merely because the total text remains below the character limit.

## Scope boundary — transport request size

These FastAPI/Pydantic/parser limits are application-level validation controls. They are not a substitute for a final production request-body or request-target limit at the selected web server or reverse proxy.

A framework must receive enough of a request to parse and validate it before model-level limits can reject oversized content. The final production runtime must therefore separately establish and validate, where supported:

- maximum accepted HTTP request-body size;
- maximum request-target/header size;
- reverse-proxy buffering behavior;
- timeout behavior for slow or oversized uploads;
- access-log behavior for rejected requests.

The final GoreeCloud Contacts server/reverse-proxy topology is not yet approved, so this source increment does not invent those runtime values or configurations.

## Automated validation

Tests verify:

- each bounded contact multi-value field accepts its documented maximum;
- values one character over the maximum fail validation;
- HTTP(S) photo references are bounded to 4,096 characters;
- duplicate-review resource identifiers reject over-limit values;
- duplicate-merge ETags reject over-limit values;
- the generated API schema exposes the shared href limit on every primary CardDAV and VCF-export query parameter;
- the generated API schema exposes the shared ETag limit on contact update and delete;
- VCF selected-index lists reject more than the allowed record count;
- VCF splitting rejects content that exceeds the record-count limit.

Exact-head GitHub Actions validation is required before this source increment is accepted.

## Remaining production abuse-control gates

Production approval still requires target-environment decisions and evidence for, as applicable:

- server/reverse-proxy request-body, request-target, and header limits;
- authentication abuse/rate-limit strategy appropriate to the final private-access topology;
- request and application timeout behavior;
- production access-log redaction/retention;
- resource monitoring under intentionally malformed or oversized requests;
- normal browser/VCF workflows under the final limits.

Production remains unapproved until the applicable runtime controls are implemented and validated.
