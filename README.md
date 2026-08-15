# GoreeCloud Contacts

GoreeCloud Contacts is the native GoreeCloud CardDAV-backed contact-management application. Radicale/CardDAV remains the authoritative contact store; GoreeCloud Contacts provides the GoreeCloud-controlled web experience, authentication/session boundary, contact workflows, portability support, and production safety controls around that store.

## Status

GoreeCloud Contacts is in stabilization for controlled private publication. The current release candidate includes the production Docker runtime, encrypted shared sessions, same-origin Glaze UI delivery, production API/privacy controls, explicit write gates, and target-host deployment documentation.

Initial publication must keep ordinary CardDAV writes disabled and must keep duplicate merge independently disabled until their respective production/live-acceptance gates are completed.

## Architecture

```text
Approved private client
        |
        v
NetBird + private DNS
        |
        v
Caddy HTTPS
        |
        v
GoreeCloud Contacts
        |
        v
Radicale / CardDAV
```

Radicale remains authoritative for contact data. The Contacts runtime persists application session state only; it does not replace the CardDAV data store.

## Repository Layout

```text
backend/     FastAPI backend, CardDAV integration, tests, live-validation helpers
frontend/    Glaze UI React/Vite frontend
docker/      Production image and Compose definition
docs/        Deployment, acceptance, and target-environment documentation
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
fastapi dev
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The development frontend normally uses `http://localhost:5173`. The development FastAPI backend normally uses `http://127.0.0.1:8000`.

## Configuration

Copy `.env.example` to `.env` for local development and review each value before use. Never commit active reusable secrets.

Important controls include:

```text
APP_ENV
FRONTEND_ORIGIN
CARDDAV_BASE_URL
CARDDAV_WRITE_ENABLED
DUPLICATE_MERGE_ENABLED
SESSION_STORE_BACKEND
SESSION_ENCRYPTION_KEYS_FILE
CSRF_ORIGIN_CHECK_ENABLED
```

Production requires HTTPS browser and CardDAV origins, secure cookies, origin checking, SQLite shared sessions, and encryption key material.

## Write Safety

Ordinary CardDAV mutation is independently controlled by:

```text
CARDDAV_WRITE_ENABLED=false
```

Duplicate merge is controlled by a separate gate:

```text
DUPLICATE_MERGE_ENABLED=false
```

Duplicate scan/preview can remain read-only while merge remains disabled.

## Production Runtime

The production container:

- runs as UID/GID `10001:10001`;
- uses a read-only root filesystem;
- persists only bounded session state under `/data`;
- uses `/tmp` tmpfs;
- drops Linux capabilities;
- enables `no-new-privileges`;
- has a PID limit;
- receives session-encryption key material through a protected file secret;
- publishes no application host port;
- attaches only to the approved external Caddy `proxy` network;
- serves the compiled Glaze UI and FastAPI API from the same origin.

The production Compose model also requires an explicit `GOREECLOUD_CONTACTS_PROXY_IP`. This provides a stable, least-privilege source identity when the Contacts container reaches the HTTPS CardDAV service through Caddy. The selected address must be verified free on the target Docker network before deployment.

For the currently validated `goreecloud-vps-01` target, the candidate address is documented as `172.19.0.51` on the existing `172.19.0.0/16` proxy network. See `docs/target-goreecloud-vps-01.md` for target-specific evidence and Caddy implications.

## Validation

Backend tests:

```bash
cd backend
pytest -q
```

Frontend validation:

```bash
cd frontend
npm ci
npm audit
npm run validate:ui
npm run lint
npm run build
```

Production Compose validation:

```bash
docker compose -f docker/compose.production.yml config
```

Production deployment and acceptance requirements are defined in:

- `docs/production-deployment-runtime.md`
- `docs/target-goreecloud-vps-01.md`
- milestone/live-acceptance documentation under `docs/`

## Production Boundary

A green source build or CI run is not by itself production approval. Production publication requires target-environment evidence for CardDAV reachability, authentication/isolation, protected sessions and secrets, authoritative Radicale backup/restore, private DNS and Caddy routing, monitoring, log privacy, browser/client acceptance, rollback, and controlled activation of writes.

## License

MIT. See `LICENSE`.
