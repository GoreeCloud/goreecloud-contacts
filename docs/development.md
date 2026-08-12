# Development

## Purpose

I use this document to define the initial development workflow for GoreeCloud Contacts.

## Branch Model

`main` represents stable GoreeCloud code. Development work should normally use short-lived branches such as:

- `feature/*`
- `fix/*`
- `security/*`
- `docs/*`

A permanent `develop` branch is not required unless project complexity later justifies one.

## Initial Development Sequence

1. Establish the repository structure and security boundaries.
2. Select and pin the initial frontend and backend dependencies after current-version verification.
3. Implement a read-only CardDAV proof of concept.
4. Add synthetic contact fixtures and automated tests.
5. Implement controlled create, update, and delete operations.
6. Build the responsive GoreeCloud Contacts interface.
7. Add Docker development and production deployment definitions.
8. Validate backup, restoration, monitoring, security, and rollback before production publication.

## Quality Requirements

Code must remain understandable, testable, maintainable, secure, and documented. Working behavior alone is not sufficient.

Changes should include appropriate validation for the affected area, including unit tests, API tests, CardDAV integration tests, UI tests, import/export tests, authentication tests, authorization tests, and container-build tests when applicable.

## Secrets

Do not commit `.env`, production endpoint credentials, real contact exports, private keys, session secrets, or other reusable credentials.

## Test Data

Use synthetic contact records by default. Test data should be clearly fictional and safe to publish with the source code.
