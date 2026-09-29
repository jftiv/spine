# homelab-infra — overview

Infrastructure as code for `homelab`, a single Ubuntu box on the owner's LAN running k3s,
managed over Tailscale at `<tailnet-ip>` (also reachable on the home LAN at `<lan-ip>` until
the API listener is restricted). It hosts two virtual clusters — `dev` and
`prod` — and exposes prod to the internet through a Cloudflare Tunnel with **no inbound ports
open** on the residential connection.

It exists to unblock `secret-santa-v2`, which is its first and so far only tenant. See
`docs/secret-santa-v2/decisions.md` for why deploying elsewhere failed.

Lives at `~/source/homelab-infra`.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | none | |
| Backend | none | Platform only; workloads belong to tenant repos |
| Database | PostgreSQL 18.4 under CloudNativePG 1.30, one Cluster per app | Inside each vcluster; WAL + daily base backups to Cloudflare R2 via the Barman Cloud plugin |
| Infra / CI | Terraform on HCP Terraform free tier, executed by a **self-hosted agent** on homelab | k3s + loft-sh vcluster + Cloudflare Tunnel |

The agent is the load-bearing choice: HCP's hosted runners cannot reach an API server that
exists only on a tailnet, so remote execution would be impossible without it. Free tier includes
one agent, which means **one concurrent run** — applying two workspaces at once queues rather
than fails, and looks like a hang.

## Layout

```
bootstrap/agent.md          tfc-agent systemd unit, and why it runs outside k3s
docs/bootstrap.md           the one-time manual steps — the entry point
docs/runbook.md             rotate, restore, upgrade, the December checklist
terraform/00-cloudflare/    tunnel, ingress rules, DNS, R2 bucket  → homelab-cloudflare
terraform/10-host/          namespaces, vclusters, cloudflared     → homelab-host
terraform/15-databases/     CNPG + Barman plugin, Postgres per app → homelab-databases
terraform/20-tenants/       per-vcluster namespace, quota, RBAC    → homelab-tenants
```

Four separate states so a mistake in tenant-land cannot destroy the cluster or a database. Apply
in numeric order; each reads the layers below via `terraform_remote_state`.

## Running it

```bash
cd terraform/10-host
terraform init
terraform plan       # streams from the agent on homelab
```

Requires the Phase 0 steps in `docs/bootstrap.md` to have been done first — none of them are in
code, and most cannot be.

## External dependencies

| Service | Used for | When it is down |
|---|---|---|
| Tailscale | Management access from the workstation (kubectl, ssh) | kubectl from off the LAN stops. Terraform is unaffected, because the agent runs on homelab and polls HCP outbound. **Serving is unaffected**, because the tunnel is independent |
| Cloudflare | DNS, tunnel ingress, TLS termination | Prod is unreachable from the internet. Nothing in-cluster is affected |
| HCP Terraform | State, locking, run history and UI | No infrastructure changes. Running workloads unaffected |
| GHCR | Image pulls | Existing pods keep running; new rollouts fail |
| Cloudflare R2 | WAL archive and base backups | Databases keep serving. Postgres retains every unarchived WAL segment until archiving resumes, so a long outage slowly fills the 5Gi volume, which can't be expanded. Data already archived is unaffected |
| GitHub (HCP's VCS link) | HCP pulling Terraform config | No runs start. Seen 2026-09-27 when the OAuth token was revoked. See `troubleshooting.md` |
| Home ISP / power | Everything | The whole platform is offline |

## Status

**All four layers are applied:** `00-cloudflare`, `10-host`, `15-databases` and `20-tenants`.
The last two were applied on 2026-09-27, from PRs #3 and #4.

The public path is proven end to end: `https://api.secret-santa.net` returns a **404 from
Traefik**, reached through Cloudflare and the tunnel with no inbound ports open. A 404 is the
success signal here; a broken chain gives a Cloudflare error page instead. Both vclusters run
with their API servers on NodePorts <dev-api-port> and <prod-api-port>, and `secret-santa` is Active in each.

**Databases are live and backed up, as of 2026-09-27.** The `secret-santa` Cluster is healthy in
both dev and prod, and continuous WAL archiving to R2 is working in both. **The restore is
proven on dev:** a Cluster rebuilt from R2 alone contained rows written both before the base
backup and after it. Details, and the gotchas for doing it again, in `architecture.md`. dev has
one on-demand base backup; prod's first arrives with the 03:30 UTC schedule.

The database layer as built differs from the M6.5 plan in three places, each logged in
`decisions.md`. The operator runs inside each vcluster, not in `10-host`. Databases live in a
shared `data` namespace. Backups use the Barman Cloud plugin, not the deprecated in-tree object
store.

Still outstanding:
- **Prod restore drill and its runbook entry** (M6.5 Phase 5). Only dev has been restored.
- **Confirm the generated connection string reached `secret-santa-config`.** Terraform writes
  it, but the value hasn't been read back, because reading a prod Secret needs the owner.
- **The R2 key's scope.** `r2.tf` describes it as scoped to one bucket. `bootstrap.md` says to
  create it as *Admin Read & Write*, which in the R2 dashboard covers every bucket in the
  account. One of them is wrong; a bucket-scoped *Object Read & Write* token is what the design
  intends.
- Deployer tokens loaded into the app repo's GitHub secrets, and the GitHub-runner network path
  to the cluster, which is still undecided.
- Restricting the k3s API listener to `lo` and Tailscale. It currently answers on the LAN too.
