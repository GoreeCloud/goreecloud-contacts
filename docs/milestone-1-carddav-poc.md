# Milestone 1 — CardDAV Proof of Concept

## Status

Initial read-only implementation.

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
- Synthetic unit tests for the health endpoint and vCard parser.

## API

- `GET /api/health`
- `GET /api/carddav/status`
- `GET /api/carddav/address-books`
- `GET /api/carddav/contacts?address_book_href=<href>`

No create, update, or delete endpoint exists in this milestone.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
fastapi dev
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Before testing CardDAV, copy `.env.example` to `.env` and replace the example values with an approved test account. The `.env` file remains excluded from Git.

## CardDAV Compatibility

The implementation follows the CardDAV/WebDAV discovery and reporting model rather than using a GoreeCloud-specific contact protocol. The application preserves returned resource hrefs and ETags so later write support can implement conditional updates rather than blind overwrites.

## Current Limitations

- Read-only.
- Authentication is supplied through protected development environment variables rather than the future browser login flow.
- The vCard parser intentionally supports only the common fields needed for the proof of concept.
- No production CardDAV credentials or real family contact data are included.
- Dependency lockfiles are not yet committed; they should be generated and reviewed from the development workstation before production-oriented build automation is introduced.
