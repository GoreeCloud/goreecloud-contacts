# Public Profiles

## Status

**Development status:** Implemented on the `agent/contact-public-profiles` development branch and subject to pull-request review and validation. This document does not imply that the capability is merged to `main`, production-approved, or available to production family contact data.

## Purpose

GoreeCloud Contacts supports repeatable public-profile links for contacts without creating a second contact database or depending on remote profile discovery. The capability is for links that a user intentionally enters for a contact, such as a public GitHub, Instagram, Bluesky, Mastodon, YouTube, or other profile.

GoreeCloud Contacts does not scrape, discover, infer, verify, or continuously monitor a contact's social accounts as part of this feature.

## Data Model

A public profile contains:

- `platform` — a normalized lowercase platform slug containing letters, numbers, and hyphens.
- `url` — an explicit HTTP or HTTPS public-profile URL.

The browser and backend accept multiple profiles per contact. Arbitrary platform slugs are supported so the data model does not depend on a fixed vendor list.

## CardDAV and vCard Representation

Radicale/CardDAV remains authoritative for ordinary contact data. Public profiles are stored inside the contact's vCard as standard `URL` properties with a GoreeCloud parameter identifying the platform:

```text
URL;TYPE=profile;X-GOREECLOUD-PLATFORM=github:https://github.com/example
```

This representation intentionally keeps the public URL visible to generic vCard/CardDAV consumers that do not understand the GoreeCloud parameter. GoreeCloud-aware clients can reconstruct the platform association.

A URL with missing, invalid, or unsupported GoreeCloud profile metadata is treated as an ordinary website rather than hidden or discarded. Unknown raw vCard properties continue to follow the existing preservation rules used by VCF import/export and duplicate merging.

## Security and Privacy Boundary

- Profile URLs must use HTTP or HTTPS.
- JavaScript, data, file, and other non-web URL schemes are rejected for public profiles.
- The application does not fetch public-profile content merely to render a stored profile entry.
- Browser profile links open only after an explicit user action.
- Public-profile links remain subject to the same signed-in-user address-book authorization and ETag-protected CardDAV write paths as other editable contact data.
- Adding a public profile does not establish a GoreeCloud Identity relationship and does not verify ownership of the external account.
- Profile entries are ordinary contact data and remain subject to Privacy Shield requirements for collection, disclosure, export, deletion, and retention.

## Presentation and Glaze UI Boundary

The feature uses durable, readable contact-detail and editor surfaces, with restrained interaction styling. It includes visible keyboard focus, responsive layouts, practical touch targets, increased-contrast handling, Forced Colors handling, and Reduced Motion-safe behavior.

This branch-level feature work is designed against current Glaze UI principles. It is not an application-wide Glaze UI conformance claim. GoreeCloud Contacts must still satisfy its separate exact-revision, platform, accessibility, and production acceptance requirements before any broader conformance claim is made.

## Platform Marks

Known platforms may use locally bundled or locally encoded identifying marks. Unknown platforms use a generic link symbol. No remote icon library, font, stylesheet, script, or image is required at runtime.

The current development implementation includes local marks derived from the Simple Icons project for selected services. Simple Icons publishes its project artwork under CC0 1.0; its license explicitly states that trademark rights are not waived. Platform names and marks remain trademarks or service marks of their respective owners where applicable. Their use in GoreeCloud Contacts is solely to identify user-entered destinations and does not imply sponsorship, affiliation, endorsement, account verification, or partnership.

The current locally represented known-platform set includes Bluesky, Discord, Facebook, GitHub, GitLab, Instagram, Mastodon, Reddit, Threads, TikTok, Twitch, X, and YouTube. LinkedIn currently uses a local textual `in` mark rather than a copied third-party SVG asset. Custom platforms remain supported through the generic link presentation.

## Portability and Recovery

Because profile records live inside vCards as URL properties, they participate in the existing raw VCF export/import and CardDAV backup/recovery model. Everkeep-specific recovery claims require the same separate backup, restore, and recovery verification as the rest of GoreeCloud Contacts; this feature does not independently establish those guarantees.
