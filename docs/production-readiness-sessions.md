# Production Readiness — Shared Encrypted Sessions

## Status

This increment replaces the process-local-only production session assumption with an optional shared encrypted SQLite session backend while preserving the existing in-memory backend for local development and isolated testing.

It addresses the source-level production-readiness requirement that authenticated sessions behave consistently across backend workers and ordinary process restarts. It does **not** by itself approve GoreeCloud Contacts for production deployment.

## Current and production session models

### Development default — memory

`SESSION_STORE_BACKEND=memory` preserves the existing lightweight development behavior:

- sessions exist only inside one backend process;
- backend restart invalidates all sessions;
- multiple workers do not share sessions;
- CardDAV credentials are not persisted to disk.

This remains appropriate for local development and isolated synthetic validation.

### Production-required backend — SQLite

When `APP_ENV=production`, configuration now fails closed unless:

- `SESSION_STORE_BACKEND=sqlite`;
- `SESSION_DB_PATH` is an absolute path;
- `SESSION_ENCRYPTION_KEYS` contains at least one valid Fernet key;
- the previously established production Secure-cookie, CSRF-origin, HTTPS frontend, and HTTPS CardDAV requirements are also satisfied.

Multiple backend workers configured with the same SQLite database and encryption-key set can read and revoke the same sessions. A backend process can restart and recover active sessions from the shared database while their expiration time remains valid.

## Persisted session data

The SQLite session table stores only:

- a SHA-256 digest of the opaque browser session token;
- one encrypted credential payload containing the CardDAV username and password;
- the UTC session-expiration timestamp.

The raw browser token is never persisted. The CardDAV username and password are not stored as plaintext columns.

The database remains sensitive even though the credential payload is encrypted. It must therefore live on a protected persistent application-data mount with approved ownership, permissions, backup treatment, and recovery handling.

## Encryption-key separation and rotation

`SESSION_ENCRYPTION_KEYS` is a runtime secret and must not be committed to source control or copied into ordinary documentation.

The setting accepts a comma-separated key list:

1. The first key encrypts newly created sessions.
2. Following keys may decrypt sessions created under older approved keys.

This supports controlled key rotation by deploying the new key first while retaining the old key temporarily for decryption. After sessions encrypted with the old key are no longer required, the old key may be removed through a separately controlled secret-rotation procedure.

Losing all valid encryption keys makes existing encrypted sessions unreadable. That failure logs users out; it does not alter Radicale contact data. The session database is not an authoritative contact store.

## Worker and restart behavior

The SQLite backend uses:

- WAL journaling;
- SQLite busy timeout;
- transactional session creation;
- shared token-digest lookups;
- shared revocation;
- expiration pruning;
- owner-only `0600` permissions on the database and SQLite WAL/shared-memory files when present.

Automated validation creates multiple independent store instances against the same database to prove that one instance can read and revoke sessions created by another. Recreating a store instance against the same database and key set also proves source-level restart persistence.

These tests establish the application behavior but are not a substitute for target-environment validation with the final worker count, filesystem, persistent mount, user/group IDs, runtime secret injection, and service restart model.

## Failure and recovery model

The shared session database contains only application authentication state.

If the database is lost, corrupted, intentionally cleared, or becomes unreadable because its encryption key is unavailable:

- existing GoreeCloud Contacts sessions become invalid;
- users must authenticate to Radicale again;
- authoritative CardDAV contact collections remain unchanged;
- no application-side contact reconstruction is required.

Whether the production session database itself should be backed up or treated as intentionally disposable must be decided during target-environment backup/recovery validation. Any backup containing the encrypted session database remains sensitive and must be protected according to the approved secret/data-protection model.

## Automated validation

The shared-session test coverage verifies:

- a session survives store recreation using the same database and key;
- independent store instances see the same active session;
- revocation by one instance is immediately visible to another;
- raw browser tokens are not stored in the database;
- CardDAV usernames and passwords are absent from plaintext database fields;
- encrypted credentials can be recovered only with an approved key;
- a new primary key with an older fallback key supports controlled rotation;
- sessions created under the new key are not decryptable by the retired old key alone;
- SQLite database, WAL, and shared-memory files use owner-only permissions when present;
- the memory backend remains available for development;
- production configuration fails closed when shared-session requirements are missing.

Exact-head GitHub Actions validation is required before this increment is accepted.

## Production-readiness gates still open

This increment does not satisfy the following separate requirements:

- Phase 4C isolated live acceptance, cleanup, and write-gate restoration;
- target-environment validation of the final worker count and restart behavior;
- final persistent data-path ownership, UID/GID, mount, and filesystem evidence;
- protected runtime secret injection, rotation, and recovery evidence;
- Radicale and application configuration backup/restore validation;
- recovery and rollback procedures;
- approved private DNS/Caddy/NetBird/firewall publication;
- monitoring and health visibility;
- upgrade and rollback validation;
- production-representative browser acceptance;
- DAVx5 and other approved client coexistence/conflict validation;
- final export/portability acceptance;
- production-family contact onboarding.

Production approval remains fail-closed until the applicable target-environment and operational gates have separate evidence.
