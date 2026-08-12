# GoreeCloud Contacts

GoreeCloud Contacts is my private, self-hosted personal and family contact-management web application. I am building it as a GoreeCloud-native web interface for contacts stored through CardDAV.

## Project Status

**Status:** Initial development

The current development objective is to prove the complete CardDAV data path before adding the full contact-management interface.

## Role

I will use GoreeCloud Contacts to provide a modern browser-based interface for managing personal and family contacts while preserving CardDAV as the portable synchronization standard.

## Architecture

The planned application model is:

```text
Browser
  |
  v
GoreeCloud Contacts
  |
  | CardDAV
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

Radicale remains the authoritative CardDAV service. GoreeCloud Contacts will not create a competing contact database for ordinary contact data.

## Initial Technology Direction

- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Contact protocol: CardDAV
- Contact format: vCard
- Authoritative contact service: Radicale
- Android synchronization: DAVx5
- Deployment: Docker and Docker Compose
- Reverse proxy: Caddy
- Development platform: GitHub

Technology selections remain subject to implementation validation before the first production release.

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
│   └── security.md
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Development Milestones

### Milestone 1 — CardDAV Proof of Concept

- Authenticate to an approved Radicale test account.
- Discover address books through CardDAV.
- Retrieve contacts without modifying production data.
- Parse vCard contact records.
- Render a basic contact list.
- Verify that changes made through a controlled test path remain compatible with DAVx5.

### Milestone 2 — Core Contact Management

- Create contacts.
- Edit contacts.
- Delete contacts.
- Search and filter contacts.
- Support multiple address books.
- Support common vCard fields and contact photos.

### Milestone 3 — GoreeCloud Product Interface

- Responsive GoreeCloud user interface.
- Favorites and categories.
- VCF import and export.
- Duplicate detection and merge workflows.
- Multi-user access boundaries.
- Dark mode and accessibility improvements.

### Milestone 4 — Production Readiness

- Automated tests.
- Container build and runtime validation.
- Authentication and authorization testing.
- Backup and restoration validation.
- Caddy and private-service publication validation.
- Monitoring integration.
- Security review.
- Documented rollback procedure.

## Security Rules

I will not commit passwords, active CardDAV credentials, tokens, private keys, session secrets, or other reusable credentials to this repository. Example configuration uses placeholders only.

Development must use test accounts, test address books, and non-production contact data whenever practical.

## License

GoreeCloud Contacts is licensed under the MIT License. See `LICENSE`.
