# Architecture

## Purpose

I use this document to define the initial application architecture for GoreeCloud Contacts.

## Governing Decision

Radicale remains the authoritative CardDAV service for contact data. GoreeCloud Contacts is a web application that reads and writes contacts through CardDAV rather than maintaining a second authoritative contact database.

## Logical Architecture

```text
Approved browser
    |
    v
Caddy HTTPS
    |
    v
GoreeCloud Contacts
    |
    +-- Frontend
    |     - contact list
    |     - contact details
    |     - editor
    |     - search and filters
    |
    +-- Backend
          - authentication/session handling
          - authorization
          - CardDAV client
          - vCard parsing and serialization
          - conflict handling
          - application API
    |
    v
Radicale
    |
    +-- user address books
    +-- vCard resources
    |
    v
DAVx5 / other standards-compliant CardDAV clients
```

## Data Authority

Ordinary contact fields belong in vCard resources stored by Radicale. This includes names, phone numbers, email addresses, organizations, postal addresses, birthdays, websites, notes, categories, photos, and other supported vCard properties.

The application may later maintain limited non-contact state such as UI preferences or session records, but application-specific storage must not become a competing source of truth for contact information.

## Multi-User Boundary

Each user must access only the CardDAV collections authorized to that user. The application must not depend on one broad service credential that can read every user's private contacts.

## Deployment Boundary

Development and testing are separate from production. Initial CardDAV work must use controlled test accounts, test address books, and test contacts whenever practical.

Production publication is blocked until authentication, authorization, backup, restoration, private-network access, Caddy routing, and rollback behavior are validated.
