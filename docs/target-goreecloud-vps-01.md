# GoreeCloud Contacts — goreecloud-vps-01 Target Record

## Purpose

This record captures target-specific production-publication evidence for GoreeCloud Contacts on `goreecloud-vps-01`. It supplements the generic production runtime and private-publication runbook and must be updated when the target network, Caddy model, CardDAV service identity, or deployment placement changes.

## Validated Target State — August 15, 2026

The target host is `goreecloud-vps-01` running Debian 13 with Docker 29.6.2 and Docker Compose v5.3.1.

The shared external Docker network is:

```text
proxy
subnet: 172.19.0.0/16
gateway: 172.19.0.1
```

Caddy and Radicale are already attached to this network. Caddy is the only HTTP/HTTPS gateway. Radicale has no host-published application port.

The production Caddyfile remains:

```text
/srv/docker/caddy/Caddyfile
```

## Service Identity Separation

The stable GoreeCloud service identities are intentionally separate:

```text
GoreeCloud Contacts: https://contacts.goreecloud.com
Radicale / CardDAV:  https://dav.goreecloud.com
GoreeCloud Calendar: https://calendar.goreecloud.com
```

`calendar.goreecloud.com` is reserved for the GoreeCloud Calendar application and must not remain the long-term Radicale/CardDAV identity.

GoreeCloud Contacts must use:

```text
FRONTEND_ORIGIN=https://contacts.goreecloud.com
CARDDAV_BASE_URL=https://dav.goreecloud.com
GOREECLOUD_CONTACTS_CARDDAV_HOST=dav.goreecloud.com
```

Do not publish Contacts at the CardDAV hostname and do not point Contacts at the Calendar application hostname.

The Contacts production redeployment remains blocked until `dav.goreecloud.com` is live on Caddy, presents the correct HTTPS certificate, reaches Radicale, and is source-restricted according to the GoreeCloud private-service model.

## Contacts Proxy Identity

Production application validation requires `CARDDAV_BASE_URL` to use HTTPS. The Radicale Caddy route is deliberately source restricted and must not authorize the entire Docker proxy subnet.

GoreeCloud Contacts is assigned an explicit address on the existing `proxy` network:

```text
GOREECLOUD_CONTACTS_PROXY_IP=172.19.0.51
```

Target inspection on August 15, 2026 confirmed that `172.19.0.51` was unused before deployment.

After the Radicale hostname migration, the `dav.goreecloud.com` Caddy matcher should authorize only the established approved sources plus the Contacts production identity. The intended bounded source list for the existing Radicale access pattern is:

```caddyfile
@netbird_client remote_ip 100.64.0.0/10 172.19.0.50 172.19.0.51
```

`172.19.0.50` is the existing Uptime Kuma source identity. `172.19.0.51` is reserved for GoreeCloud Contacts.

Do not replace this bounded list with `172.19.0.0/16` merely to make dependency checks pass.

## Private Caddy Dependency Address

Live target inspection on August 15, 2026 confirmed Caddy's current address on the shared `proxy` network:

```text
172.19.0.2
```

The production Compose model therefore requires the target-specific deployment value:

```text
GOREECLOUD_CONTACTS_CADDY_IP=172.19.0.2
```

The production container preserves the HTTPS CardDAV hostname while routing only that hostname to the approved private Caddy address through Compose `extra_hosts`. This keeps TLS hostname validation intact, avoids routing the dependency through public DNS, and preserves the Contacts source identity `172.19.0.51` seen by Caddy.

The Caddy address is target state, not an application constant. Re-inspect it before a future deployment if the Caddy container or proxy-network addressing changes.

## First Startup Dependency Finding — August 15, 2026

The first production-shaped startup of reviewed release candidate `f7a4e3740de852932b08d4c9baa6efb20ea8e1a0` validated the container's runtime hardening but correctly failed readiness because CardDAV transport was unavailable.

Observed state:

```text
/api/health/live  -> 200
session_store     -> ok
carddav           -> unavailable
/api/health/ready -> 503
```

At that time the deployment still used `https://calendar.goreecloud.com` as the CardDAV endpoint. Inside the Contacts container, default Docker DNS resolved that hostname to public addresses `207.207.210.36` and `207.207.210.50`. An unauthenticated HTTPS `PROPFIND` reached an `openresty` endpoint and returned HTTP `404`, so the application correctly treated CardDAV as unavailable.

This exposed two deployment-model issues that are now being corrected together:

1. CardDAV dependency traffic must route privately through Caddy instead of public DNS.
2. Radicale's stable service identity is `dav.goreecloud.com`, while `calendar.goreecloud.com` is reserved for GoreeCloud Calendar.

The unready Contacts container was removed before continuing. The release candidate was amended to make the CardDAV hostname target-configurable and to require the private Caddy mapping. It must pass CI again and `dav.goreecloud.com` must be live before target redeployment.

## Temporary Calendar Matcher Cleanup

During the first readiness investigation, the live `calendar.goreecloud.com` Caddy matcher was temporarily expanded from:

```caddyfile
@netbird_client remote_ip 100.64.0.0/10 172.19.0.50
```

to:

```caddyfile
@netbird_client remote_ip 100.64.0.0/10 172.19.0.50 172.19.0.51
```

This change was narrow and validated, but it belongs to the Radicale dependency path, not the future GoreeCloud Calendar application. When Radicale is moved to `dav.goreecloud.com`, transfer the required Contacts source authorization to the `dav.goreecloud.com` block and remove `172.19.0.51` from the Calendar block unless the future Calendar application independently requires it.

Do not remove the temporary Calendar authorization before the Radicale/Caddy migration sequence is reviewed; avoid creating an unnecessary intermediate outage for any still-active dependency path.

## Backup Evidence Before First Deployment

The active `goreecloud-kopia-backup.service` completed successfully on August 15, 2026 from 12:02:15 AM CDT through 12:02:31 AM CDT.

The run produced Kopia snapshot ID:

```text
d8b92b68a6f2b5bb1ad66149620d483e
```

The active Kopia stack references the current Radicale application-data/configuration paths. Radicale remains the authoritative contact store; the Contacts application session database is not authoritative contact data.

A production-family approval still requires restore evidence appropriate to the current Radicale architecture. A successful snapshot alone does not close the restore-validation gate.

## Initial Safety State

First publication must use:

```text
CARDDAV_WRITE_ENABLED=false
DUPLICATE_MERGE_ENABLED=false
```

Ordinary writes may be considered only after production authentication/isolation, CardDAV dependency reachability, backup/restore, browser acceptance, and controlled CRUD acceptance are complete.

Duplicate merge remains independently disabled until the Phase 4C live-acceptance gate is closed.

## Private Publication Target

The intended private DNS rewrite for the Contacts application is:

```text
contacts.goreecloud.com -> 100.71.27.119
```

The Contacts application itself must have no host-published application port. Caddy reaches `goreecloud-contacts:8000` over the shared `proxy` network, while approved clients reach Caddy through the GoreeCloud private NetBird/DNS path.
