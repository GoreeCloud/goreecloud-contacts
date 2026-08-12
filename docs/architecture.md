# Architecture

## Purpose

I use this document to define the application architecture for GoreeCloud Contacts.

## Governing Decision

Radicale remains the authoritative CardDAV service for contact data. GoreeCloud Contacts is a web application that reads and writes contacts through CardDAV rather than maintaining a second authoritative contact database.

## Logical Architecture

```text
Approved browser
    |
    | HTTPS / application session
    v
Caddy HTTPS
    |
    v
GoreeCloud Contacts
    |
    +-- Frontend
    |     - Radicale sign-in
    |     - contact list
    |     - contact editor
    |     - local search
    |     - address-book selection
    |
    +-- Backend
          - Radicale-backed authentication
          - opaque server-side sessions
          - per-user authorization
          - CardDAV client
          - vCard parsing and serialization
          - ETag conflict handling
          - application API
    |
    | CardDAV using the signed-in user's credentials
    v
Radicale
    |
    +-- per-user address-book homes
    +-- authorized address books
    +-- vCard resources
    |
    v
DAVx5 / other standards-compliant CardDAV clients
```

## Data Authority

Ordinary contact fields belong in vCard resources stored by Radicale. This includes names, phone numbers, email addresses, organizations, postal addresses, birthdays, websites, notes, categories, photos, and other supported vCard properties.

GoreeCloud Contacts may maintain application-specific state such as authenticated sessions or future UI preferences, but application-specific storage must not become a competing source of truth for contact information.

## Authentication Model

GoreeCloud Contacts does not use one broad CardDAV service credential for interactive user access.

Each user signs in with an approved Radicale/CardDAV username and password. The backend validates the credentials through CardDAV principal and address-book discovery. A successful login creates a random opaque application session token.

The browser receives only the opaque token in an HTTP-only cookie. The CardDAV password remains in backend process memory for the lifetime of the session because the backend must authenticate subsequent CardDAV requests as that user.

The current session store is process-local. A backend restart invalidates all sessions, and multiple backend workers do not share session state. This limitation must be reviewed before production deployment.

## Multi-User Authorization Boundary

Every protected CardDAV request is executed with the authenticated session user's credentials.

The backend independently verifies application-level scope in addition to Radicale permissions:

- requested address books must exactly match collections discovered for the authenticated user's CardDAV principal;
- requested contact resources must be `.vcf` files beneath one of those discovered address books;
- CardDAV targets must remain on the configured CardDAV server origin;
- decoded and normalized resource paths are checked before authorization decisions.

The browser therefore cannot use GoreeCloud Contacts to select an arbitrary same-origin CardDAV collection simply by changing an href parameter.

## Write Integrity Boundary

Create, update, and delete operations remain protected by the Milestone 2 conditional-write model.

- Create uses `If-None-Match: *`.
- Update and delete use `If-Match` with the current ETag.
- CardDAV HTTP 412 becomes application HTTP 409.
- `CARDDAV_WRITE_ENABLED` remains disabled by default.

Per-user authentication does not bypass these controls.

## Deployment Boundary

Development and testing remain separate from production. CardDAV validation must use controlled test accounts, test address books, and synthetic contacts whenever practical.

Production publication is blocked until authentication, authorization, multi-user isolation, session protection, backup, restoration, private-network access, Caddy routing, monitoring, and rollback behavior are validated.
