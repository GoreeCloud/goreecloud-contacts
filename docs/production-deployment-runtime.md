# GoreeCloud Contacts — Production Runtime and Private Publication Runbook

## Purpose

This runbook defines the initial stable production-runtime candidate for GoreeCloud Contacts and the controlled path for publishing it at `https://contacts.goreecloud.com`.

It does not declare production approval by itself. Source and CI evidence must be followed by target-host validation, private-publication validation, backup/recovery evidence, production-representative authentication/authorization checks, monitoring, and browser/client acceptance.

## Stable Initial Scope

The initial publication candidate preserves Radicale/CardDAV as the authoritative contact store and keeps the browser application same-origin behind Caddy.

The intended stable scope is:

- authenticated CardDAV discovery and per-user isolation;
- contact search, detail viewing, create, update, and delete with conditional ETag protection;
- expanded contact fields from Milestone 4 Phase 4A;
- raw VCF import/export from Phase 4B;
- Glaze UI responsive/accessibility behavior;
- encrypted shared production sessions;
- privacy-safe API caching/error/logging controls;
- production liveness/readiness signals.

Duplicate scan and preview remain read-only. Duplicate **merge** has a separate `DUPLICATE_MERGE_ENABLED` gate and must remain `false` for the initial stable publication until the Phase 4C isolated Radicale-backed live acceptance is completed, cleaned up, and documented.

## Runtime Architecture

```text
Approved NetBird browser
  |
  | private DNS + HTTPS
  v
Caddy at contacts.goreecloud.com
  |
  | Docker proxy network only
  v
goreecloud-contacts:8000
  |  \_ compiled Glaze UI static assets
  |  \_ FastAPI /api routes
  |
  | HTTPS CardDAV as the signed-in user
  v
Radicale/CardDAV
```

The production image serves the compiled frontend and FastAPI API from one origin. This avoids a separate frontend runtime and avoids cross-origin production API traffic.

## Container Security Contract

The production runtime is intentionally constrained:

- dedicated UID/GID `10001:10001`;
- non-root process;
- read-only container root filesystem;
- writable `/data` only for the encrypted SQLite session store;
- ephemeral `/tmp` through tmpfs;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- PID limit applied;
- no Docker socket or privileged mode;
- no host network mode;
- no application host port published by the production Compose definition;
- only the external `proxy` Docker network attached;
- an explicit target-approved `GOREECLOUD_CONTACTS_PROXY_IP` on that network;
- health checking through `/api/health/ready`.

The explicit proxy-network address provides a stable, least-privilege source identity for HTTPS CardDAV access through Caddy. It must be inspected and approved on each target host; do not grant the entire shared Docker subnet CardDAV access merely to avoid selecting a bounded service identity.

The image uses two Uvicorn workers. Shared SQLite sessions therefore provide worker-compatible authentication state instead of process-local sessions.

## Production Dependency Contract

The frontend uses the committed npm lock and `npm ci`.

The Python production image uses `backend/requirements.runtime.lock`, then installs the GoreeCloud Contacts package with `--no-deps` and runs `pip check`. Development-only FastAPI CLI/cloud tooling is intentionally excluded from the production dependency set.

The Node and Python base images are referenced by explicit release families plus immutable registry digests. Any digest refresh is a reviewed dependency/image update and must pass the complete CI/runtime gate before deployment.

## Persistent Data Boundary

GoreeCloud Contacts does **not** become an authoritative contact database.

The container's `/data` path contains application session state only. The browser token is stored as a digest and the CardDAV credential payload is encrypted using runtime-provided Fernet key material.

Loss of the Contacts session database should force sign-in again; it must not delete or replace CardDAV contacts.

The authoritative contact data and its recovery path remain with Radicale/CardDAV.

## Secret Boundary

Production session encryption keys are reusable secret material and use a file-based secret rather than living directly in the ordinary production `.env`.

The production application receives only this non-secret reference:

```text
SESSION_ENCRYPTION_KEYS_FILE=/run/secrets/session-encryption-keys
```

The Compose source is the protected host file referenced by:

```text
GOREECLOUD_CONTACTS_SESSION_SECRET_PATH=/srv/docker/secrets/goreecloud-contacts/session-encryption-keys
```

`SESSION_ENCRYPTION_KEYS` remains supported for local/test compatibility, but the application fails closed if both the direct-value and file-based mechanisms are configured simultaneously.

The active key value must never be committed, copied into this runbook, placed in the Docker image, or printed during troubleshooting.

## Target Host Preparation

Before first production startup, inspect the current target host, Docker networks, Caddy state, CardDAV service identity, backups, and filesystem ownership. Do not create paths or change shared services based only on this example.

The intended GoreeCloud paths are:

```text
/srv/docker/appdata/goreecloud-contacts/
/srv/docker/secrets/goreecloud-contacts/session-encryption-keys
```

When those paths are confirmed for the selected host:

1. Create the app-data directory for runtime UID/GID `10001:10001` with restrictive permissions.
2. Create the secret directory with restrictive administrative access.
3. Generate a Fernet key using an approved cryptographically secure method without placing the value into source control, documentation, or shell history when avoidable.
4. Store the secret file so runtime UID `10001` can read it and other ordinary host users cannot.
5. Protect the production `.env` with owner-only permissions.
6. Inspect the external `proxy` network and select a free, approved static address for `GOREECLOUD_CONTACTS_PROXY_IP`.
7. Reserve that exact address as the Contacts source identity in the CardDAV Caddy access matcher rather than authorizing the whole Docker subnet.

Because Docker Compose implements `file:` secrets using a bind mount, file-source `uid`, `gid`, and `mode` remapping is not available. The **host-side secret file ownership and mode are therefore authoritative for readability by the non-root container**.

A suitable intended state is:

```text
/srv/docker/appdata/goreecloud-contacts         10001:10001  700
/srv/docker/secrets/goreecloud-contacts         root:root    700
.../session-encryption-keys                     10001:10001  400 or 600
/srv/docker/stacks/goreecloud-contacts/.env     approved administrator 600
```

Use actual host inspection and the approved GoreeCloud ownership model before applying ownership. Do not use `chmod 777` or broad-readability troubleshooting.

Validate metadata after creation:

```bash
sudo stat -c '%A %a %U:%G %n' \
  /srv/docker/appdata/goreecloud-contacts \
  /srv/docker/secrets/goreecloud-contacts \
  /srv/docker/secrets/goreecloud-contacts/session-encryption-keys \
  /srv/docker/stacks/goreecloud-contacts/.env
```

## Required Production Configuration

The application fails closed in production unless required security configuration is present.

At minimum, review and provide non-secret runtime values equivalent to:

```text
APP_ENV=production
FRONTEND_ORIGIN=https://contacts.goreecloud.com
CARDDAV_BASE_URL=https://calendar.goreecloud.com
CARDDAV_WRITE_ENABLED=false
DUPLICATE_MERGE_ENABLED=false
SESSION_COOKIE_SECURE=true
CSRF_ORIGIN_CHECK_ENABLED=true
SESSION_STORE_BACKEND=sqlite
SESSION_DB_PATH=/data/sessions.sqlite3
SESSION_ENCRYPTION_KEYS_FILE=/run/secrets/session-encryption-keys
GOREECLOUD_CONTACTS_DATA_PATH=/srv/docker/appdata/goreecloud-contacts
GOREECLOUD_CONTACTS_SESSION_SECRET_PATH=/srv/docker/secrets/goreecloud-contacts/session-encryption-keys
GOREECLOUD_CONTACTS_PROXY_IP=<approved-free-proxy-network-address>
```

`https://calendar.goreecloud.com` is the current verified CardDAV service identity in the GoreeCloud Contacts records. A planned move to `dav.goreecloud.com` must not be assumed or embedded into production until that separate migration is completed and documented.

For target-specific values and evidence, use the applicable target record such as `docs/target-goreecloud-vps-01.md`.

## Build and Compose Validation

From an exact reviewed source revision:

```bash
docker build -f docker/Dockerfile -t goreecloud/contacts:<reviewed-tag> .
```

Before deployment, validate the Compose model from the documented stack/repository context:

```bash
docker compose -f docker/compose.production.yml config
```

Because rendered Compose output can expose environment-derived information, review it only in an approved administrative session and do not copy unredacted resolved configuration into ordinary documentation.

Confirm all of the following before startup:

- the `proxy` network exists and is the approved shared Caddy network;
- `GOREECLOUD_CONTACTS_PROXY_IP` is free and belongs to that network's configured subnet;
- the CardDAV Caddy matcher is prepared to authorize only that explicit Contacts source identity plus existing approved sources;
- the Contacts service has no `ports:` publication;
- the production `.env` exists with protected permissions;
- the `/data` bind path exists with runtime-compatible ownership;
- the session-encryption secret file exists and is readable by UID `10001` without broad host access;
- current backup/recovery evidence exists for authoritative Radicale contact data;
- the current CardDAV endpoint is reachable from the selected runtime without weakening private-access controls.

## CardDAV Dependency Reachability

Do not weaken Caddy, NetBird, DNS, or firewall restrictions merely to make the Contacts container reach Radicale.

Production requires an HTTPS `CARDDAV_BASE_URL`. When CardDAV is reached through a source-restricted Caddy route, assign Contacts a stable approved source identity on the shared Docker network and authorize only that address. Do not replace a bounded source list with the full Docker subnet as a convenience workaround.

If `CARDDAV_BASE_URL=https://calendar.goreecloud.com` is still not reachable from the production container, inspect the actual DNS resolution, Caddy source-address restriction, Docker networks, and current Radicale publication model. Choose and document an approved dependency path rather than bypassing security controls ad hoc.

The application must not be declared ready until `/api/health/ready` reports both the shared session store and CardDAV transport as available.

## First Startup

Start the application with ordinary writes and duplicate merge disabled:

```bash
docker compose -f docker/compose.production.yml up -d --build
```

Inspect the container and recent logs:

```bash
docker compose -f docker/compose.production.yml ps
docker logs --since 5m goreecloud-contacts
```

Do not continue if startup is unstable, production configuration fails closed, the container cannot reach CardDAV, the secret file is unreadable, secrets appear in logs, or the session database cannot be written safely.

## Private DNS Publication

The approved private-service pattern requires an AdGuard Home rewrite:

```text
contacts.goreecloud.com -> 100.71.27.119
```

This DNS rewrite identifies the current GoreeCloud VPS private endpoint. It is not authorization by itself. NetBird policies, Caddy source restrictions, the host firewall, and application authentication remain separate controls.

Do not create a public A or AAAA record for the private Contacts service merely to make the application reachable.

## Caddy Publication

Use the existing active Caddy deployment and back up the active Caddyfile before material modification. Validate the complete Caddyfile before reload/recreation.

The intended Contacts site pattern is:

```caddyfile
contacts.goreecloud.com {
    tls {
        dns porkbun {
            api_key {$PORKBUN_API_KEY}
            api_secret_key {$PORKBUN_API_SECRET_KEY}
        }
        propagation_delay 30s
        propagation_timeout 10m
        resolvers 1.1.1.1 8.8.8.8
    }

    @netbird_client remote_ip 100.64.0.0/10
    handle @netbird_client {
        reverse_proxy goreecloud-contacts:8000
    }

    respond "Forbidden" 403
}
```

The backend target is the Docker service on the shared `proxy` network. No Contacts host port is required.

The existing CardDAV site must separately authorize the exact Contacts proxy-network source identity required for application-to-CardDAV HTTPS requests. Keep that authorization narrow and target-specific.

Validate before applying:

```bash
sudo docker exec caddy caddy validate --config /etc/caddy/Caddyfile
```

Do not continue on a validation error.

## Publication Acceptance

From an approved NetBird client, validate:

```bash
dig +short contacts.goreecloud.com
curl -I https://contacts.goreecloud.com
```

Expected private DNS result:

```text
100.71.27.119
```

Validate the certificate directly against the private endpoint:

```bash
openssl s_client \
  -connect 100.71.27.119:443 \
  -servername contacts.goreecloud.com \
  </dev/null 2>/dev/null |
openssl x509 -noout -issuer -subject -ext subjectAltName -dates
```

Also validate:

- approved NetBird clients can reach the application;
- an unapproved/public source receives controlled denial and cannot reach the backend;
- `/api/health/live` is healthy;
- `/api/health/ready` is ready;
- `/docs`, `/redoc`, and `/openapi.json` are absent in production;
- the Glaze UI loads from the same origin;
- sign-in works with production-representative non-family test identities first;
- one authenticated user cannot discover another user's address books;
- session state survives worker selection and container restart as designed;
- the file-based encryption secret is readable by the application but is not present in ordinary container environment inspection;
- logs do not retain query strings, credentials, cookies, VCF bodies, contact contents, or encryption keys unnecessarily;
- Caddy reaches the backend only through the approved Docker network;
- the Contacts service has no unnecessary host-port publication.

## Enabling Ordinary Writes

Do not begin initial publication with writes enabled merely because source-level tests are green.

After production authentication/isolation validation, Radicale backup/restore evidence, rollback preparation, and controlled browser acceptance are complete, ordinary CardDAV writes may be enabled by setting:

```text
CARDDAV_WRITE_ENABLED=true
```

Recreate only the Contacts application as required and perform controlled synthetic create/update/stale-conflict/delete acceptance before onboarding family contact data.

Keep:

```text
DUPLICATE_MERGE_ENABLED=false
```

until the separate Phase 4C live merge gate is closed.

## Phase 4C Duplicate Merge Gate

Duplicate scan and preview are non-mutating. The merge endpoint is separately fail-closed through `DUPLICATE_MERGE_ENABLED=false`.

Only set it to `true` after the documented isolated sequence has been completed successfully:

```text
baseline -> seed -> review -> write -> final
```

If an interrupted write leaves disposable fixtures, use the bounded cleanup procedure from the Phase 4C live-acceptance runbook before restoring normal safety state.

## Monitoring

At minimum, production monitoring should distinguish:

- process liveness: `/api/health/live`;
- dependency readiness: `/api/health/ready`;
- end-user HTTPS reachability at `https://contacts.goreecloud.com`.

Alert routing must be validated rather than assumed. Monitor output must not expose contact data, CardDAV credentials, session tokens, encryption keys, or detailed internal paths unnecessarily.

## Backup and Recovery

Before production family data is approved:

1. verify the current Radicale backup includes the authoritative contact collections and required configuration;
2. perform or confirm a restoration test appropriate to the current Radicale architecture;
3. decide whether the Contacts session database is backed up or treated as disposable authentication state;
4. protect and recover session encryption key material independently from the session database;
5. record the authoritative secret location and recovery method without reproducing the active key;
6. document rollback to the previous reviewed Contacts image/source revision;
7. confirm that application rollback does not require contact-data rollback unless a separate CardDAV data event occurred.

## Rollback

The safest application rollback begins by disabling mutations:

```text
CARDDAV_WRITE_ENABLED=false
DUPLICATE_MERGE_ENABLED=false
```

Then restore the previous reviewed Contacts image/source revision and recreate the Contacts container. Validate liveness, readiness, authentication, and contact reads before considering normal operation restored.

A Contacts application rollback must not replace authoritative Radicale data automatically.

## Remaining Production Gates

This runtime definition closes the missing source-controlled deployment shape, but final publication still requires target-environment evidence for:

- CardDAV dependency reachability from the container;
- production-representative authentication and authorization;
- persistent session ownership/permissions and restart behavior;
- protected file-secret creation, injection, rotation, and recovery;
- Radicale backup and restore;
- Caddy/AdGuard Home/NetBird/firewall publication;
- production log redaction and retention across Caddy/container/host/monitoring layers;
- request/abuse controls at the selected runtime boundary;
- actual monitoring and alert delivery;
- production desktop/mobile/high-contrast browser acceptance;
- DAVx5 coexistence and conflict behavior;
- VCF export/portability acceptance;
- upgrade and rollback rehearsal;
- controlled production-family onboarding.

The application should remain in a proving/stabilization state until those target gates are evidenced. Stable source code is necessary, but stable GoreeCloud operation also requires validated access, recovery, monitoring, secret handling, and rollback.
