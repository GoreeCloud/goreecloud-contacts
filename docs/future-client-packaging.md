# Future Client Packaging and Application Identity

## Status

Planned future product requirement. This document does not approve implementation or production distribution yet.

## Required Client Packages

GoreeCloud Contacts must eventually provide the following first-party client deliverables in addition to the browser application:

- an Android APK for supported Android devices;
- a Debian package (`.deb`) for supported Debian-family Linux systems.

Both clients must preserve the existing GoreeCloud Contacts architecture and product boundaries. Radicale/CardDAV remains authoritative, per-user authorization and portability remain required, and client packaging must not create a second authoritative contact store.

The exact Android and Linux client architecture, frameworks, signing model, permissions, desktop integration, update mechanism, release channels, CI/CD jobs, rollback model, and distribution process remain future implementation decisions that must be validated against current GoreeCloud standards before release.

## Canonical Application Icon

GoreeCloud Contacts must have one canonical application icon and visual identity across every supported platform and distribution surface.

The same canonical Contacts artwork must drive:

- the web application icon and favicon surfaces;
- Android launcher and adaptive-icon assets;
- Debian/Linux application icons and desktop launcher metadata;
- package-manager and installer presentation where supported;
- GitHub repository and release artwork;
- documentation and other official GoreeCloud Contacts references;
- future supported client platforms.

Platform-specific icon files may be generated only when required by a platform's packaging or rendering rules. They must remain derivatives of the same canonical master artwork rather than independently designed replacements.

The canonical source should be retained in source control as reusable vector/master artwork. Android adaptive layers, raster sizes, Linux SVG/PNG derivatives, favicons, and other generated assets should be produced from the canonical source through a documented asset pipeline whenever practical.

Client-specific alternate logos, unrelated artwork, unofficial colors, or visual identities are not permitted. GoreeCloud Contacts must remain immediately recognizable as the same application on the web, Android, and Linux.

## Design and Security Requirements

All client packages and icon assets must follow the current GoreeCloud Glaze UI, official application visual-identity, privacy, accessibility, security, source-control, and release-validation standards.

No Android APK or Debian package should be considered stable solely because it builds successfully. Each future client requires platform-specific functional, security, upgrade, rollback, packaging, signing, and visual-identity acceptance before distribution.
