# Milestone 1 — CardDAV Proof of Concept

## Status

Completed and live-validated on August 12, 2026.

## Purpose

I use this milestone to prove that GoreeCloud Contacts can connect the browser interface to a FastAPI backend and retrieve address books and contact summaries from an approved CardDAV test account without adding any contact-writing capability.

## Implemented Scope

- React and TypeScript frontend scaffold.
- Vite development server and `/api` proxy.
- FastAPI backend scaffold.
- Backend health endpoint.
- CardDAV configuration-status endpoint.
- CardDAV principal and address-book-home discovery.
- Address-book discovery with `PROPFIND`.
- Read-only contact retrieval with WebDAV `PROPFIND` and CardDAV `addressbook-multiget`.
- ETag preservation in API results.
- Minimal vCard parsing for UID, formatted name, email addresses, and phone numbers.
- Basic responsive contact-list interface.
- Local contact search.
- Synthetic unit tests for the health endpoint, vCard parsing, CardDAV discovery, and contact retrieval.

## API

- `GET /api/health`
- `GET /api/carddav/status`
- `GET /api/carddav/address-books`
- `GET /api/carddav/contacts?address_book_href=<href>`

No create, update, or delete endpoint exists in this milestone.

## Live Validation

I completed live validation against the GoreeCloud Radicale service using a dedicated non-production account and synthetic data.

Validation results:

- Dedicated Radicale test account: `goreecloud-contacts-test`.
- Existing Radicale users file was backed up before the test account was added.
- Radicale remained healthy after the account change and did not require a restart.
- Authenticated WebDAV `PROPFIND` against the private CardDAV service returned HTTP `207`.
- Dedicated address book `GoreeCloud Contacts Test` was created at `/goreecloud-contacts-test/contacts-test/` with HTTP `201`.
- Synthetic vCard resource `jordan-example.vcf` was created with HTTP `201`.
- CardDAV discovery returned the dedicated address book as an address-book collection.
- Direct retrieval of the synthetic vCard succeeded.
- The local `.env` remained Git-ignored and was protected with mode `600`.
- Backend dependencies installed successfully in a project-local Python virtual environment.
- Backend automated tests passed: `4 passed`.
- Live API validation returned backend health `ok`, CardDAV `configured: true`, the dedicated address book, and the synthetic contact with its ETag.
- Frontend dependencies installed successfully with zero reported npm audit vulnerabilities at installation time.
- The TypeScript and Vite production build completed successfully.
- Browser validation at `http://localhost:5173` displayed the discovered address book and synthetic `Jordan Example` contact while preserving the read-only UI state.

The live validation used only the dedicated test account, dedicated test address book, and synthetic contact data. No production family contact collection was used as a development dataset.

## Local Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
pytest -q
fastapi dev
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Before testing CardDAV, copy `.env.example` to `.env` and replace the blank values with an approved test account. The `.env` file remains excluded from Git and should be protected with restrictive local permissions.

## CardDAV Compatibility

The implementation follows the CardDAV/WebDAV discovery and reporting model rather than using a GoreeCloud-specific contact protocol. The application preserves returned resource hrefs and ETags so later write support can implement conditional updates rather than blind overwrites.

## Current Limitations

- Read-only.
- Authentication is supplied through protected development environment variables rather than the future browser login flow.
- The vCard parser intentionally supports only the common fields needed for the proof of concept.
- No production CardDAV credentials or real family contact data are included.
- CardDAV write operations are intentionally blocked until conditional-request and ETag conflict handling are implemented and tested.

## Next Step

I will preserve this known-good read-only state with dependency lockfiles and automated continuous integration before introducing CardDAV write support. The next write milestone must use conditional requests and ETags for create, update, and delete operations so concurrent changes from DAVx5 or another CardDAV client are not silently overwritten.
