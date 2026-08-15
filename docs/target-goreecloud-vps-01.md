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

Caddy and Radicale are already attached to this network. Caddy is the only public HTTP/HTTPS gateway. Radicale has no host-published application port.

The production Caddyfile remains:

```text
/srv/docker/caddy/Caddyfile
```

The authoritative CardDAV service identity remains:

```text
https://calendar.goreecloud.com
```

## Contacts Proxy Identity

Production application validation requires `CARDDAV_BASE_URL` to use HTTPS. The existing Calendar Caddy route is deliberately source restricted and does not authorize the entire Docker proxy subnet.

To preserve least privilege without opening Calendar to all containers, GoreeCloud Contacts is assigned an explicit address on the existing `proxy` network:

```text
GOREECLOUD_CONTACTS_PROXY_IP=172.19.0.51
```

Target inspection on August 15, 2026 confirmed that `172.19.0.51` was unused before deployment.

The Calendar Caddy matcher should authorize only the established NetBird/client identities already required by Calendar plus the Contacts production identity:

```caddyfile
@netbird_client remote_ip 100.64.0.0/10 172.19.0.50 172.19.0.51
```

`172.19.0.50` is the existing Uptime Kuma source identity. `172.19.0.51` is reserved for GoreeCloud Contacts.

Do not replace this bounded list with `172.19.0.0/16` merely to make dependency checks pass.

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

The intended private DNS rewrite is:

```text
contacts.goreecloud.com -> 100.71.27.119
```

The Contacts application itself must have no host-published application port. Caddy reaches `goreecloud-contacts:8000` over the shared `proxy` network, while approved clients reach Caddy through the GoreeCloud private NetBird/DNS path.
