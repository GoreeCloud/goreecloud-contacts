# Milestone 3 — Authentication and Multi-User Isolation

## Goal

Milestone 3 replaces the single application-wide CardDAV identity with per-user Radicale authentication and enforces strict session-bound access to each user's discovered CardDAV address books.

Radicale remains the authoritative contact store. GoreeCloud Contacts does not create a second contacts database.

## Implemented Foundation

### Radicale-Backed Sign-In

The frontend provides a username/password sign-in flow. The backend validates those credentials by performing CardDAV discovery with the supplied identity.

Successful authentication creates an opaque server-side session. The browser receives only a random HTTP-only session token.

### Server-Side Sessions

The initial session store is process-local and in memory.

Each session records:

- the authenticated username;
- the CardDAV password required for server-side CardDAV requests;
- a cryptographically random opaque token;
- an expiration timestamp.

The password and token are excluded from the session record representation and are not returned by authentication API responses.

Session endpoints:

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

All CardDAV data routes require an authenticated session.

### Per-User CardDAV Clients

Every protected request constructs a CardDAV client from the authenticated session's credentials. The backend no longer uses `CARDDAV_USERNAME`, `CARDDAV_PASSWORD`, or a globally configured address-book home path for normal application access.

The protected environment supplies the CardDAV service endpoint rather than one shared CardDAV identity.

### Application-Level Collection Isolation

The CardDAV client discovers address books from the authenticated user's current principal and `addressbook-home-set`.

Before contact operations are performed, the application verifies that:

- a selected address book exactly matches a discovered address book for the current session;
- a contact path is a `.vcf` resource beneath one of those discovered address books;
- the target remains on the configured CardDAV server origin;
- normalized, percent-decoded paths remain inside the authorized collection boundary.

This application-level authorization supplements Radicale's own permissions.

### Existing Write Protections Preserved

Milestone 2 conditional writes remain unchanged in principle:

- create requires `If-None-Match: *`;
- update and delete require `If-Match` with the current ETag;
- stale writes remain conflict failures;
- `CARDDAV_WRITE_ENABLED` still defaults to `false`.

Authentication does not automatically enable writes.

## Automated Test Coverage Added

The branch adds tests for:

- opaque session creation;
- password/token exclusion from session representations;
- successful login, session retrieval, and logout;
- invalid CardDAV credential rejection;
- authentication requirements on CardDAV routes;
- rejection of an address book outside the authenticated user's discovered scope;
- rejection of a contact resource outside the authenticated user's discovered scope;
- preservation of existing conditional create/update/delete behavior.

The automated backend suite contains 15 passing tests. The existing Starlette TestClient deprecation warning remains non-blocking.

## Live Validation Harness

`backend/scripts/validate_milestone3_live.py` provides repeatable live API validation from the NetBird-connected development workstation. It prompts for CardDAV passwords with `getpass`; passwords are not accepted as command-line arguments, printed, or written by the script.

The core validation checks:

- backend health;
- CardDAV configuration;
- `CARDDAV_WRITE_ENABLED=false` safety state;
- unauthenticated rejection of protected CardDAV routes;
- live Radicale-backed login for `goreecloud-contacts-test`;
- HTTP-only and SameSite=Strict session-cookie attributes;
- absence of password/token fields in the authentication response;
- discovery of `GoreeCloud Contacts Test` at `/goreecloud-contacts-test/contacts-test/`;
- retrieval of the retained `Jordan Example` synthetic fixture and its expected UID;
- immediate logout invalidation;
- login for a second isolated Radicale principal named `goreecloud-contacts-isolation-test`;
- absence of the primary user's test address book from the second user's discovery results;
- HTTP 403 when the second user explicitly attempts to select the primary user's address book;
- logout invalidation for the second user.

The expiration validation is a separate mode so the normal development session lifetime does not need to be shortened for all tests.

## Live Validation Procedure

### 1. Preserve the Read-Only Test Boundary

The protected local `.env` must point to the approved CardDAV endpoint and keep writes disabled:

```dotenv
CARDDAV_BASE_URL=https://calendar.goreecloud.com
CARDDAV_WRITE_ENABLED=false
SESSION_TTL_SECONDS=28800
SESSION_COOKIE_SECURE=false
FRONTEND_ORIGIN=http://localhost:5173
```

`SESSION_COOKIE_SECURE=false` is for local HTTP development only. Production HTTPS deployment must use a Secure cookie.

The legacy `CARDDAV_USERNAME` and `CARDDAV_PASSWORD` values are no longer used by the Milestone 3 application path. User passwords are supplied interactively at sign-in and must remain outside source control and ordinary documentation.

### 2. Create the Second Isolated Radicale Test Principal

Use the preferred NetBird SSH path to `goreecloud-vps-01`. Back up the Radicale users file before changing it, then add the second test identity with the same bcrypt cost used for the existing Contacts test identity:

```bash
ssh goreecloud-vps-netbird
stamp=$(TZ=America/Chicago date +%Y%m%d-%H%M%S-%Z)
sudo cp -a /srv/docker/config/radicale/users "/srv/docker/config/radicale/users.bak.${stamp}"
sudo htpasswd -B -C 12 /srv/docker/config/radicale/users goreecloud-contacts-isolation-test
sudo stat -c '%U:%G %a %n' /srv/docker/config/radicale/users
sudo docker ps --filter name=radicale --format 'table {{.Names}}\t{{.Status}}'
```

The password must be entered interactively and kept outside the repository and conversation. The second principal does not need an address book for the negative isolation test.

Expected file state remains `debian:debian` mode `640`, and Radicale should remain healthy without requiring an account-addition restart.

### 3. Synchronize the Development Laptop

```bash
cd ~/goreecloud-contacts
git fetch origin
git switch feature/milestone-3-authentication-isolation 2>/dev/null || \
  git switch --track -c feature/milestone-3-authentication-isolation \
  origin/feature/milestone-3-authentication-isolation
git pull --ff-only
```

### 4. Start the Backend and Frontend

Backend terminal:

```bash
cd ~/goreecloud-contacts/backend
source .venv/bin/activate
fastapi dev
```

Frontend terminal:

```bash
cd ~/goreecloud-contacts/frontend
npm run dev
```

### 5. Run Core Live API Validation

From another backend virtual-environment terminal:

```bash
cd ~/goreecloud-contacts/backend
source .venv/bin/activate
python scripts/validate_milestone3_live.py --mode core
```

Enter the stored passwords for `goreecloud-contacts-test` and `goreecloud-contacts-isolation-test` only when the non-echoing prompts appear.

The run passes only if the write gate is disabled, the primary test fixture loads correctly, logout invalidates access, and the secondary principal receives HTTP 403 when it tries to select `/goreecloud-contacts-test/contacts-test/`.

### 6. Perform Browser Acceptance

Open `http://localhost:5173` and verify:

1. CardDAV address books are not visible before authentication.
2. Sign in as `goreecloud-contacts-test` using the stored test password.
3. The authenticated username is shown.
4. `GoreeCloud Contacts Test` loads.
5. `Jordan Example` appears with the expected synthetic contact information.
6. The application remains in read-only safety mode.
7. Sign out.
8. The contact data disappears and protected CardDAV data cannot be loaded without signing in again.

Do not use production-family credentials or collections during this validation.

### 7. Validate Session Expiration with a Temporary Short TTL

Stop the backend, temporarily change the protected local `.env` to:

```dotenv
SESSION_TTL_SECONDS=5
```

Restart the backend and run:

```bash
cd ~/goreecloud-contacts/backend
source .venv/bin/activate
python scripts/validate_milestone3_live.py --mode expiration
```

The script logs in with the primary test principal, waits only for the short configured lifetime, verifies `/api/auth/session` returns unauthenticated state, and confirms the protected address-book route returns HTTP 401.

After the expiration test, restore:

```dotenv
SESSION_TTL_SECONDS=28800
CARDDAV_WRITE_ENABLED=false
```

Restart the backend and re-check `/api/carddav/status` before treating live validation as complete.

## Live Validation Completed — August 12, 2026 at 5:04 PM CDT

Milestone 3 live validation was completed with isolated, non-production Radicale identities and synthetic contact data.

### Radicale Isolation Principal

- A backup of `/srv/docker/config/radicale/users` was created before the account change.
- `goreecloud-contacts-isolation-test` was added with bcrypt cost 12 through interactive `htpasswd` entry.
- No password was written to the repository, documentation, terminal command arguments, or conversation.
- `/srv/docker/config/radicale/users` remained owned by `debian:debian` with mode `640`.
- The Radicale container remained healthy after the account addition.

### Browser and Primary-Identity Acceptance

- The frontend and FastAPI backend ran locally on the approved development workstation.
- Browser sign-in succeeded for `goreecloud-contacts-test`.
- The authenticated username was displayed.
- `GoreeCloud Contacts Test` loaded through the signed-in user's live CardDAV principal path.
- The retained `Jordan Example` synthetic fixture loaded with its expected test contact information.
- The interface visibly remained in read-only safety mode while `CARDDAV_WRITE_ENABLED=false`.
- The frontend sign-out path clears the authenticated session state, address books, selected address book, contacts, editor state, and search query after requesting backend logout. Live core API validation independently proved immediate logout invalidation for both test identities.

### Session-Expiration Validation

The protected local `.env` was temporarily changed to `SESSION_TTL_SECONDS=5`. The expiration harness then passed the following live checks:

- backend health and CardDAV configuration;
- disabled CardDAV write gate;
- initial unauthenticated state;
- HTTP 401 for protected CardDAV access before login;
- live Radicale-backed login for `goreecloud-contacts-test`;
- authentication response contained no password/token fields;
- session cookie was HttpOnly and SameSite=Strict;
- the test session expired after the configured short lifetime;
- the expired session was removed;
- protected CardDAV access returned HTTP 401 after expiration.

The run ended with `Milestone 3 session-expiration validation PASSED.`

After the test, the protected local environment was restored to:

```dotenv
CARDDAV_BASE_URL=https://calendar.goreecloud.com
FRONTEND_ORIGIN=http://localhost:5173
CARDDAV_WRITE_ENABLED=false
SESSION_TTL_SECONDS=28800
```

### Core Two-User Isolation Validation

The core live harness passed against both isolated Radicale identities. It verified:

- backend health;
- configured CardDAV with writes disabled;
- fresh unauthenticated state;
- HTTP 401 for protected CardDAV access without a session;
- Radicale-backed login for `goreecloud-contacts-test`;
- no password/token fields in the authentication response;
- HttpOnly and SameSite=Strict cookie attributes;
- authenticated session metadata limited to identity and expiration information;
- discovery through the primary user's live Radicale/CardDAV principal path;
- retrieval of the retained `Jordan Example` synthetic fixture;
- immediate primary-session invalidation on logout;
- independent Radicale-backed login for `goreecloud-contacts-isolation-test`;
- no discovery of the primary user's address book by the secondary principal;
- application-level rejection of explicit cross-user address-book selection with HTTP 403;
- immediate secondary-session invalidation on logout.

The run ended with `Milestone 3 core live API validation PASSED.`

No production family contact data was used.

## Final Merge Gate

The authentication, expiration, read-only safety, and two-user live-isolation gates are complete. The remaining merge gate is successful GitHub Actions validation on the exact final branch head that contains this validation record.

## Current Limitation

The session store is process-local. Backend restarts invalidate all sessions, and multiple backend workers would not share session state. This is acceptable for the current development milestone but must be reviewed before production deployment.

Production deployment also requires a final decision on explicit CSRF-token protection versus additional Origin/Referer enforcement for the approved HTTPS deployment model.
