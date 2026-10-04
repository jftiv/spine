# Landscape

The repos worked on from spine, and how they depend on each other. Read this before a session
that touches more than one of them.

## Repos

| Repo | Path | What it is | Its docs |
|---|---|---|---|
| `secret-santa-v2` | `~/source/secret-santa-v2` | Secret Santa web app: React SPA, .NET 10 API, PostgreSQL | `docs/README.md` in the repo |
| `homelab-infra` | `~/source/homelab-infra` | Terraform for `homelab`: a single k3s box with `dev`/`prod` vclusters, Cloudflare Tunnel, CloudNativePG | spine's `docs/homelab-infra/`, plus the repo's `docs/bootstrap.md` and `docs/runbook.md` |
| `secret-santa-web` | `~/source/secret-santa-web` | The 2018 app v2 replaces. Scheduled for deletion once v2 ships | none |

**homelab-infra is an extension of spine**, not an ordinary target repo. It is the owner's own
platform for spinning up and deploying apps, never shared, so its architecture and decisions
stay in spine's `docs/homelab-infra/` rather than being split into the repo. Only the
operational procedures (`bootstrap.md`, `runbook.md`) live in the repo, next to the Terraform
they operate.

## How they connect

```
                Cloudflare edge (TLS, DNS)
                         │ tunnel (outbound-only)
homelab-infra ───────────┼─────────────────────────────────────────────
  00-cloudflare  tunnel, `api` DNS record, Brevo sender-auth records (DKIM, DMARC)
  10-host        cloudflared → Traefik ← Ingress synced out of the prod vcluster
  15-databases   CNPG Cluster in `data` ns ──WAL + base backups──► R2
  20-tenants     `secret-santa` ns, quota, NetworkPolicy, deployer RBAC,
                 `secret-santa-config` Secret (incl. generated connection string)
                         ▲                            ▲
secret-santa-v2 ─────────┼────────────────────────────┼────────────────
  deploy/ + Deploy to k3s workflow        API pods read the Secret,
  (applies workloads into the ns;         reach Postgres on 5432 through
   never creates it)                      the cross-namespace NetworkPolicy
  client/dist ──► Hostinger static hosting (not on homelab)
  email outbox ──► Brevo API (IP check off for API keys; see the repo's decisions.md)
```

### The contract between them

- **The platform owns the namespace; the app owns its workloads.** `homelab-infra` creates the
  `secret-santa` namespace, its quota, NetworkPolicy, deployer credentials and the
  `secret-santa-config` Secret. `secret-santa-v2` only applies Deployments, Services, the
  Ingress and the migrate Job into it. The app's CI credential cannot create namespaces.
- **The database is a platform resource.** `15-databases` creates the Cluster and generates
  `ConnectionStrings__Default`; `20-tenants` merges it into `secret-santa-config`. The app never
  creates, alters or backs up the database. Schema is the app's (EF migrations via the migrate
  Job).
- **Secrets flow one way:** HCP Terraform workspace variables → Terraform state →
  `secret-santa-config`. None live in either repo. Setting and rotating them is in
  `homelab-infra/docs/runbook.md`.
- **CI reaches the cluster over Tailscale.** The vcluster API servers have no public endpoint;
  the deploy workflow joins the tailnet as an ephemeral `tag:ci` node.
- **Public traffic:** `api.secret-santa.net` → Cloudflare → tunnel → host Traefik → the prod
  vcluster's Ingress. dev has no public route.

### Changes that cross the boundary

A change on one side that the other side must know about:

| If you change… | …check |
|---|---|
| Secret keys the app requires | `prod_app_secrets` / dev equivalent on the `homelab-tenants` workspace |
| API replica count | `PostgresOptions.MaxPoolSize` × replicas against CNPG `max_connections` (100) |
| Tenant quota or NetworkPolicy | The app's resource requests; `/readyz` after deploy |
| Postgres major version | The app's Testcontainers image (`postgres:18.4`), which matches it on purpose |
| Hostnames or tunnel ingress rules | `Site__BaseUrl`, `Cors__AllowedOrigins__0`, the deploy workflow's smoke URL |
| The app's sender domain or email provider | Sender-authentication records in `00-cloudflare/mail.tf`. A domain without them gets mail accepted by the provider and never delivered |
| Brevo's authorised-IP setting (off for API keys since 2026-10-03) | If re-enabled, the homelab's public IP must be listed and kept current. An unlisted IP returns 401, and the app marks that mail `Failed` permanently |

## Cross-repo history

Why the app runs on a home cluster with an in-cluster database, instead of Fly and Hostinger
MySQL: `decisions.md`. The migration that moved it, and what is still owed (prod restore
drill, Hostinger decommission): `m6.5-postgres.md`.
