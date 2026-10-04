# homelab-infra — architecture

## The shape

```
homelab (Ubuntu, k3s, LAN <lan-ip> wired, Tailscale <tailnet-ip>)
├─ systemd: tfc-agent ──── outbound ──▶ HCP Terraform   (plans/applies execute here)
├─ ns kube-system     Traefik (k3s default)
├─ ns cloudflared     cloudflared ──── outbound ──▶ Cloudflare edge
├─ ns vcluster-dev    dev API server,  NodePort <dev-api-port> ─┐ each contains:
└─ ns vcluster-prod   prod API server, NodePort <prod-api-port> ─┘   ns secret-santa   the app
                                                            ns cnpg-system    CNPG operator + Barman plugin
                                                            ns data           Postgres Cluster `secret-santa`

Public:  api.secret-santa.net ─▶ Cloudflare ─▶ tunnel ─▶ Traefik ─▶ prod vcluster
Private: dev                  ─▶ Tailscale ─▶ NodePort <dev-app-port>
In-cluster: secret-santa ns ─▶ data ns :5432  (NetworkPolicy-allowed, nothing else)
Egress:  Postgres pod (Barman sidecar) ─▶ R2  s3://homelab-postgres-backups/<env>/<db>
```

Hostinger MySQL is being retired (M6.5 of `secret-santa-v2`). Since 2026-09-27, `20-tenants`
writes the generated in-cluster Postgres connection string into `secret-santa-config`. The
value itself hasn't been read back to confirm it. Hostinger and its allowlist entry stay until
Phase 6 of that plan.

## Addressing

| Address | What it is | How it is held |
|---|---|---|
| `<lan-ip>` | homelab's LAN address, on **`enp2s0` (wired)** | DHCP **reservation on the Netgear** for MAC `<enp2s0-mac>`, and `node-ip` in `/etc/rancher/k3s/config.yaml` |
| `<tailnet-ip>` | homelab on the tailnet | Assigned by Tailscale; all management access uses this or the MagicDNS name `homelab` |
| `<wan-ip>` | home WAN address | **ISP DHCP — not static.** Only the Hostinger MySQL allowlist depends on it, and that goes away in M6.5 Phase 6. Nothing on the Postgres path uses it |

Topology: cable modem → Netgear. The Netgear feeds a wired run to homelab **and** the Google
router, which serves wifi to everything else. homelab sits on the Netgear's subnet, one NAT
above the wifi clients — the isolation the double-NAT exists to provide.

`k3s` records the node `InternalIP` from `node-ip`, not from the default route, so the two must
be changed together. `/etc/rancher/k3s/config.yaml` must be **appended to** — it also carries
`debug`, `write-kubeconfig-group` and `write-kubeconfig-mode`.

homelab's NICs. The two ethernet MACs differ by one character and reserving the wrong one is the
obvious trap:

| Interface | MAC | Role |
|---|---|---|
| `enp1s0` | `<enp1s0-mac>` | `NO-CARRIER` — nothing plugged in |
| `enp2s0` | `<enp2s0-mac>` | **the live wired link** to the Netgear |
| `wlp3s0` | `<wlp3s0-mac>` | wifi, kept only as fallback and to be retired |

`cni0`, `flannel.1` and every `veth*` are k3s's pod network and are never DHCP clients.

The LAN address pins the *inside* address only. It does nothing for the Hostinger allowlist,
which sees the WAN address. Those are different layers, and conflating them is the easy
mistake. The WAN problem is being **removed rather than solved**: once the database is
in-cluster, nothing depends on the WAN address at all.

**The k3s API server also listens on the LAN.** `<lan-ip>:6443`, `:<dev-api-port>` and `:<prod-api-port>`
answer from the wifi subnet without Tailscale. Credentials are still required, so it isn't
open. But "management is Tailscale-only" is currently true by convention, not enforced.
Restricting the listener to `lo` and the Tailscale interface is noted in the repo runbook and
not done yet.

## Why two vclusters rather than two namespaces

The isolation is **logical, not physical** — one box, so a hardware or power failure takes both
environments. What vcluster buys is a separate API server, separate CRDs, and separate RBAC per
environment, so a cluster-scoped mistake in prod cannot reach dev. Namespaces would have given
none of that, and "two clusters" would have been true only by convention.

The cost is one more component to run and upgrade, and vcluster moves quickly enough that the
chart version is pinned deliberately.

## The three sharp edges of vcluster here

**Ingress objects created inside a vcluster are invisible to the host's Traefik** unless synced
out. `sync.toHost.ingresses.enabled` pushes them to the host; `sync.fromHost.ingressClasses`
lets `ingressClassName: traefik` resolve inside the virtual cluster instead of dangling. Without
both, an Ingress applies cleanly and routes nothing.

**NetworkPolicies inside a vcluster are decorative** unless `sync.toHost.networkPolicies` is on,
because the CNI that enforces them lives on the host. Verified 2026-08-30: this k3s was **not**
started with `--disable-network-policy`, and the NetworkPolicy API is served, so the host side
is in place. (Enforcement was confirmed by the absence of the disable flag, not by a traffic
test — worth an actual test the first time a policy is load-bearing.)

**The Terraform agent runs on the host, outside the cluster**, so it cannot resolve `*.svc`
addresses. Each vcluster's API server is therefore published on a **fixed** NodePort, and
`controlPlane.proxy.extraSANs` must carry `127.0.0.1` or the agent fails certificate
verification. `exportKubeConfig.server` makes the generated kubeconfig name that endpoint, so
the tenant layer can consume the `vc-<name>` secret verbatim rather than patching it.

The port has to be fixed rather than dynamically allocated precisely because the generated
kubeconfig has to name it.

## Terraform layering

| Layer | Manages | Depends on |
|---|---|---|
| `00-cloudflare` | Tunnel, tunnel ingress rules, DNS (including the Brevo sender-authentication records in `mail.tf`), R2 backup bucket | nothing |
| `10-host` | Namespaces, cloudflared, 2× vcluster | `00` (tunnel token) |
| `15-databases` | Per vcluster: CNPG operator, Barman plugin + its mTLS certs, `data` namespace, one Postgres Cluster per app, app role credentials, connection strings | `00` (R2 bucket, endpoint), `10` (vcluster kubeconfigs) |
| `20-tenants` | Per-vcluster namespace, quota, NetworkPolicy, deploy SA, pull secret, `secret-santa-config` | `10` (vcluster kubeconfigs), `15` (connection strings) |

**A speculative plan reads the applied state of the layers below it.** A PR that adds a new
output in one layer and consumes it in another fails its speculative plans until the producer is
applied. PR #3 did exactly this. The failures are about ordering, not bugs. The fix is to apply
layer by layer after merging: `00` → `15` → `20`, each started by hand once the one below
finishes. The single agent runs one job at a time anyway.

`00` genuinely depends on nothing because the tunnel's ingress rule targets a stable in-cluster
address (`http://traefik.kube-system.svc.cluster.local:80`) rather than anything Terraform
creates. That is what lets the tunnel be configured before the cluster is populated.

**Providers cannot be created with `for_each`**, so `20-tenants` declares one provider pair per
environment by hand. Adding a third environment means editing that file. The friction is
accepted at this size and is a reason not to grow the environment list casually.

## Secrets: one mechanism, Terraform state

Every secret on the platform is Terraform-managed and lives in HCP state. Sealed Secrets was
designed and then dropped before it was ever applied (2026-09-03, `decisions.md`).

| Secret | Created by | How it gets there |
|---|---|---|
| Cloudflare API token, tunnel token | `00` | Workspace variable / resource output |
| GHCR PAT | `20` | Sensitive workspace variable, typed by hand |
| R2 S3 key | `15` | Sensitive workspace variable, **made by hand on purpose** (see `decisions.md`) |
| Postgres app role password, connection string | `15` | `random_password`, composed in Terraform |
| Barman plugin mTLS keys | `15` | `tls` provider |
| App secrets (`Tokens__ParticipantKey`, API keys, salt) | `20` | Sensitive map variables `dev_app_secrets` / `prod_app_secrets` |

`secret-santa-config` is `var.<env>_app_secrets` merged with the generated connection string,
with the generated value applied **last** so a stale variable can't override it.

**HCP state and the HCP token are what's worth protecting.** Most other controls inside the
cluster depend on who can read Secrets and who can read state.

`Tokens__ParticipantKey` is still the one secret that can't be rotated in normal operation.
Rotating it invalidates links in mail already delivered. It lives in state knowingly, and an
independent copy belongs in a password manager.

## Databases (`15-databases`)

Each vcluster runs its own CloudNativePG operator (1.30.0, chart 0.29.0) and Barman Cloud plugin
(v0.14.0, chart 0.7.1) in `cnpg-system`. They have to be inside the vcluster. A CRD installed on
the host k3s isn't visible in the virtual clusters.

**One Postgres `Cluster` per application, in a shared `data` namespace.** Currently one
database, `secret-santa`, in each of dev and prod. Single instance, PostgreSQL 18.4, 5Gi
`local-path` volume, database `secretsanta` owned by role `secretsanta`, superuser access
disabled.

- **`local-path` can't expand a volume** (`ALLOWVOLUMEEXPANSION=false`). Growing one means a
  dump, a new volume and a restore. That's why the size was chosen generously for a dataset
  measured in megabytes.
- **The `data` namespace has a quota: 2 CPU, 2Gi memory limits.** A live cluster uses 1280Mi of
  the memory limit: 1Gi for Postgres plus 256Mi for the Barman sidecar. A second full-size
  cluster, such as a restore, doesn't fit next to it. See the restore section below.
- **NetworkPolicy:** default-deny ingress, then two allows. The operator namespace may reach
  everything. The app's namespace may reach only its own cluster's pods, on 5432. Allows are
  keyed on `cnpg.io/cluster=<name>`, not the namespace, because the namespace is shared.
  Verified 2026-09-27 that the policies sync to the host (`sync.toHost.networkPolicies`). On the
  host every vcluster pod shares one namespace, so vcluster rewrites the namespace selector into a
  pod label (`vcluster.loft.sh/ns-label-<env>-x-<hash>: secret-santa`), and the rewritten form
  is correct. **Still not traffic-tested.** The app's first connection will be that test, and
  a refusal there should be read as this policy first.

### Backups

- **Continuous WAL archiving** to `s3://homelab-postgres-backups/<env>/<db>`, done by a Barman
  sidecar the plugin injects into each Postgres pod. `archive_timeout` is 5 minutes, so an idle
  database still ships a segment at least that often. This, not the base backup, bounds how
  much data can be lost.
- **Base backups** daily at 03:30 UTC (`ScheduledBackup` `secret-santa-daily`), gzip, 14-day
  retention. The base backup only bounds how much WAL a restore has to replay.
- One bucket for the whole platform, in R2 `enam`, keyed by environment and database.

### The operator ↔ plugin channel

The operator drives the plugin over gRPC ("archive this", "back up now", "restore from
there"). It isn't the path to R2, and it isn't the path from the app to Postgres. **But the
operator won't reconcile a Cluster whose declared plugin it can't reach,** so a broken channel
means no database pods at all, not just no backups.

The channel is mutual TLS with **pinned, self-signed** certificates: each side trusts exactly the
other's `tls.crt`, and `ca.crt` is ignored. Its purpose is authentication: nothing on the pod
network except the operator can drive the plugin. Encryption comes along with it.
`cnpg-system` has no NetworkPolicy, so mTLS is the only thing gating it. Anyone who can read the
client Secret in `cnpg-system`, or take over the operator pod, already holds the operator's much
larger powers. So this protects against *other* workloads, not a compromised operator.

### Restoring

Proven on dev on 2026-09-27. A new Cluster built from R2 alone contained a row written before
the base backup **and** a row written after it that existed only in archived WAL. Recovery took
53 seconds end to end on an empty database. The shape of the restore Cluster:

- `bootstrap.recovery.source: origin`, with an `externalClusters` entry `origin` using plugin
  `barman-cloud.cloudnative-pg.io` and parameters `barmanObjectName: secret-santa-backups` and
  `serverName: secret-santa`.
- **No `plugins:` block with `isWALArchiver`.** A restored cluster that archives would write a
  new timeline into the *source's* R2 path. Without the block the pod gets no Barman sidecar and
  no R2 credentials, so it physically can't upload.
- Reduced resources (384Mi limit), or it won't fit in the `data` quota next to the live cluster.

A restored cluster reports **"Continuous archiving is working"** even with no archiver. With
nothing configured, the archive command does nothing and reports success. Don't read that
status as "it's archiving somewhere".

The prod drill (M6.5 Phase 5) and a 2am-grade runbook entry are still owed. The steps above are
the raw material for it.

## Why there is no cert-manager

TLS terminates at the Cloudflare edge and the tunnel-to-Traefik hop is inside the cluster. The
only internal certificates are the operator↔plugin pair above, and Terraform mints those. A
certificate controller would be a component to run for two certificates that are replaced
together on one apply.

## Why there is no GitOps controller

Terraform plus a deploy workflow covers a one-app, one-node cluster. Flux or Argo would be a
reconciliation loop to run, upgrade, and debug for benefits that begin at a scale this is not at.
