# Future Client Packaging and Application Identity

## Status

Planned future product requirement. This document does not approve Android or Debian production distribution yet. The canonical application artwork source and web icon integration are now implemented in source control.

## Required Client Packages

GoreeCloud Contacts must eventually provide the following first-party client deliverables in addition to the browser application:

- an Android APK for supported Android devices;
- a Debian package (`.deb`) for supported Debian-family Linux systems.

Both clients must preserve the existing GoreeCloud Contacts architecture and product boundaries. Radicale/CardDAV remains authoritative, per-user authorization and portability remain required, and client packaging must not create a second authoritative contact store.

The exact Android and Linux client architecture, frameworks, signing model, permissions, desktop integration, update mechanism, release channels, CI/CD jobs, rollback model, and distribution process remain future implementation decisions that must be validated against current GoreeCloud standards before release.

## Canonical Application Icon

GoreeCloud Contacts has one canonical application icon and visual identity across every supported platform and distribution surface.

The authoritative master artwork is:

`artwork/contacts-icon.svg`

The browser-consumable source derivative is:

`frontend/public/contacts-icon.svg`

The icon uses a Glaze UI rounded application tile, a translucent address-book surface, visible address-book tabs, and a centered person silhouette. This visual vocabulary identifies the product as Contacts without relying on text inside the icon.

The same canonical Contacts artwork must drive:

- the web application icon and favicon surfaces;
- Android launcher and adaptive-icon assets;
- Debian/Linux application icons and desktop launcher metadata;
- package-manager and installer presentation where supported;
- GitHub repository and release artwork;
- documentation and other official GoreeCloud Contacts references;
- future supported client platforms.

Platform-specific icon files may be generated only when required by a platform's packaging or rendering rules. They must remain derivatives of the same canonical master artwork rather than independently designed replacements.

Android adaptive layers, raster sizes, Linux SVG/PNG derivatives, favicons, and other generated assets should be produced from `artwork/contacts-icon.svg` through a documented asset pipeline whenever practical. Generated artifacts must not become independent design authorities.

Client-specific alternate logos, unrelated artwork, unofficial colors, or visual identities are not permitted. GoreeCloud Contacts must remain immediately recognizable as the same application on the web, Android, Linux, GitHub, documentation, and future platforms.

## Web Integration

The current browser client references `/contacts-icon.svg` for its SVG favicon and application touch-icon metadata. This gives the web application the same source identity that future packaged clients must inherit.

Future raster or platform-native derivatives should be added only when the target platform requires them and should be validated visually against the canonical master before release.

## Design and Security Requirements

All client packages and icon assets must follow the current GoreeCloud Glaze UI, official application visual-identity, privacy, accessibility, security, source-control, and release-validation standards.

No Android APK or Debian package should be considered stable solely because it builds successfully. Each future client requires platform-specific functional, security, upgrade, rollback, packaging, signing, and visual-identity acceptance before distribution.
