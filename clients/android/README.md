# GoreeCloud Contacts Android Client

This directory is the dedicated native Android application line for GoreeCloud Contacts.

## Architecture authority

Radicale/CardDAV remains the sole authoritative contact store. The Android client must not create a competing application-only authoritative contact database. Any local persistence is a bounded offline/cache representation with explicit synchronization and conflict handling.

Android's Contacts Provider is an optional device-integration bridge, not the GoreeCloud source of truth. Provider read/write access must be separately permissioned, purpose-bound, user-controlled, and independently accepted before it is enabled.

## Current Development foundation

The current shell provides:

- Kotlin/Jetpack Compose application module targeting SDK 36 with minimum SDK 29 and Java 17.
- A launchable native Contacts surface.
- Explicit runtime capability state for GoreeCloud Identity, CardDAV read/write, offline cache, background synchronization, and the Android Contacts Provider bridge.
- Fail-closed Development behavior: every data capability is `NOT_IMPLEMENTED` and the manifest requests neither network nor Contacts Provider permissions.
- Android backup disabled.
- Unit coverage proving the shell does not advertise unavailable capability.
- Gradle caching, parallel execution, and incremental Kotlin compilation.

## Next milestones

Advance each capability independently and preserve truthful state:

1. Identity/session binding without reusable credentials in source control.
2. CardDAV discovery and read-only contact listing against non-production Development data.
3. ETag/precondition-aware create/edit/delete with explicit conflict surfaces.
4. Protected bounded offline cache and deterministic reconciliation.
5. WorkManager/background synchronization with power/network constraints.
6. Optional Android Contacts Provider bridge with explicit permission and user controls.
7. Glaze UI V1.3 application-level migration, accessibility, form-factor, and representative-device acceptance.
8. Independent Privacy Shield, Wardveil Security, Everkeep, Manager, Mesh, and Identity acceptance where applicable.
9. APK/AAB signing, SBOM/provenance, rollback/recovery evidence, Release Candidate, production, and Stable gates.

No source-local safeguard or successful CI run grants production, platform-system, or Stable acceptance by itself.
