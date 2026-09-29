# homelab-infra — decisions

Append-only. Newest first. Only choices that had a real alternative.

### Barman plugin mTLS: pinned self-signed certificates, not a private CA — 2026-09-27
_Corrects the certificate design in "No cert-manager" (2026-09-06)._
**Context:** After `15-databases` first applied, neither Postgres cluster reconciled. The
operator could not handshake with the Barman Cloud plugin (`tls: certificate required`).
**Chose:** Both certificates self-signed, no CA. Each side trusts exactly the other's
certificate. Fixed in PR #4.
**Because:** That is the contract both ends actually implement, and neither reads `ca.crt`. The
plugin runs with `--client-cert=/client/tls.crt` and uses that one certificate as its client
trust pool. The operator builds `RootCAs` from the server secret's `tls.crt`
(`internal/controller/plugin_controller.go`, CNPG 1.30). With a CA-signed client leaf, the
plugin's CertificateRequest names only the leaf's own subject as an acceptable issuer. The
operator's certificate doesn't match it, so Go's TLS client sends no certificate at all. The
upstream chart uses a cert-manager `selfSigned` issuer for both certificates for this reason.
Reproduced locally in Go before shipping.
**Security effect:** Still mutual TLS. Trust narrows from anything the CA signs to one
certificate per side, and there is no signing key left in state. The cost is that the two
certificates must rotate together. They do, since one apply replaces both.
**Rejected:** Keeping the CA and overriding the chart's container args so the plugin trusts
`ca.crt`. That fights the chart to keep a CA that buys nothing with only two parties.

### PostgreSQL 18.4, pinned to a minor tag — 2026-09-06
**Context:** The M6.5 plan left the major version open.
**Chose:** `ghcr.io/cloudnative-pg/postgresql:18.4`, enforced by a `validation` block that
rejects `:latest` and untagged images.
**Because:** CNPG supports 14–18 and defaults to 18, and a new database with no data has no
reason to start on an older major. The minor tag is pinned so an upgrade is a deliberate choice.
**Note:** A major-version change is **not** a tag bump. It needs `pg_upgrade` or a dump and
restore.

### R2 bucket in Terraform, its S3 key made by hand — 2026-09-06
**Context:** The backup bucket needs credentials, and Terraform can mint Cloudflare tokens if its
own token holds `User > API Tokens > Edit`.
**Chose:** `00-cloudflare` creates the bucket. The S3 key is created by hand in the R2 dashboard
and set as sensitive variables on `homelab-databases`, the same way `ghcr_token` is handled.
**Because:** The permissions a minted token receives are declared in the Terraform config. A
token that can mint tokens therefore turns "can change the config", which covers anyone who can
open a PR or edit a workspace variable, into "can mint a Cloudflare token with any permission".
That widens the blast radius from one bucket to the whole account.
**Rejected:** A `cloudflare_api_token` resource. It's convenient but escalates privileges.

### Barman Cloud plugin, not the in-tree `barmanObjectStore` — 2026-09-06
**Context:** The M6.5 plan assumed CNPG's built-in `barmanObjectStore` for backups.
**Chose:** The Barman Cloud plugin (CNPG-I), pinned at chart 0.7.1 / plugin v0.14.0.
**Because:** The in-tree object store is deprecated and is removed in CNPG 1.31.0, one release
past the pinned 1.30.0. Building on it would force a migration of the backup subsystem within
months.
**Cost:** A second operator-side component, plus an mTLS channel between it and the operator.
That channel is what broke on first apply; see the 2026-09-27 entry.

### No cert-manager; plugin certificates minted by Terraform — 2026-09-06
**Context:** The plugin chart defaults to cert-manager for its operator↔plugin certificates.
**Chose:** Mint them with the `tls` provider in `modules/data-platform/pki.tf`.
**Because:** cert-manager would exist on this platform for exactly one pair of internal
certificates, and public TLS already terminates at Cloudflare. The chart puts all three
cert-manager resources behind conditionals, so opting out is clean. Long validity plus
`early_renewal_hours` makes `terraform plan` propose rotation well ahead of expiry.
**Rejected:** Installing cert-manager for this one purpose.
**Correction:** The first version built a private CA that signed both leaves. That didn't work.
See "pinned self-signed certificates" (2026-09-27).

### Databases in a shared `data` namespace, one Cluster per application — 2026-09-06
**Context:** Where a tenant's database lives inside each vcluster.
**Chose:** A generic `data` namespace per vcluster, holding one CNPG `Cluster` per application.
The app reaches it across namespaces, allowed by a NetworkPolicy scoped to that cluster's pods
(`cnpg.io/cluster=<name>`) from the app's namespace, on 5432 only.
**Because:** A second application then adds a database rather than a parallel namespace with
its own backup wiring. A destroy in tenant-land can't take a database with it. One Cluster per
app, not one shared, because point-in-time recovery works per Cluster. A shared cluster would
make every restore all-or-nothing across every tenant.
**Rejected:** The M6.5 plan's database in each app's own namespace, created by `20-tenants`.
Also a single shared Cluster, which is simpler but has the PITR problem above.

### CNPG operator inside each vcluster, in its own `15-databases` layer — 2026-09-06
**Context:** The M6.5 plan put the operator in `10-host`.
**Chose:** A new `15-databases` layer and `homelab-databases` workspace, installing the operator
and plugin **inside** each vcluster (`cnpg-system`).
**Because:** `10-host` targets the host k3s, and a CRD installed there isn't visible inside the
vclusters, where the application namespaces live. The plan's version couldn't have worked. A
separate layer keeps database lifecycle out of both the host layer and tenant-land.
**Rejected:** The operator in `10-host`, which doesn't work. Also adding it to `20-tenants`,
which would couple the database to the layer tenants are expected to churn.

### The connection string is generated, not typed — 2026-09-06
**Context:** `ConnectionStrings__Default` was a hand-entered sensitive variable on
`homelab-tenants`, pointing at Hostinger.
**Chose:** `15-databases` generates the app role's password and composes the connection string.
`20-tenants` reads it through remote state and merges it into `secret-santa-config` **last**, so
a stale workspace variable loses rather than silently overriding it.
**Because:** It keeps the single mechanism from the 2026-09-03 secrets decision: one place
creates application secrets, and nobody types a password into the HCP UI. Rotation means
changing it in `15` and re-applying `15` then `20`.
**Rejected:** Reading back the credentials CNPG would generate itself. The string couldn't then
be composed in Terraform without a second read path.

### Application secrets in Terraform state, not Sealed Secrets — 2026-09-03
_Supersedes "Sealed Secrets for app secrets, Terraform for infra tokens" (2026-08-30)._
**Context:** The owner found the Sealed Secrets workflow confusing and asked whether there was a
better way, before it had been applied.
**Chose:** All application secrets are Terraform-managed, from sensitive `dev_app_secrets` /
`prod_app_secrets` map variables on the `homelab-tenants` workspace, written to a
`secret-santa-config` Secret per vcluster. The sealed-secrets controllers were removed from the
plan before ever being applied.
**Because:** The original design defended the unrotatable `Tokens__ParticipantKey` from state by
introducing a **sealing key whose loss is equally unrecoverable** — trading one irreversible
failure for another, and charging a controller per vcluster plus the `kubeseal` CLI for it. For
a single operator running one application that is a bad deal. Four of the five secrets rotate
cheaply anyway; letting the fifth dictate the mechanism for all of them was the error.
**Cost, accepted knowingly:** these values live in HCP state including every historical version,
and anyone holding the HCP token can read them. That token can also apply arbitrary
infrastructure to this cluster, so it is not the weakest link — but it is now the thing to
protect, and an independent copy of the participant key belongs in a password manager.
**Rejected:** Keeping Sealed Secrets. Also considered and rejected: a split where only the
participant key was created by hand — simpler than sealing but still two mechanisms, and the
owner preferred one.

### Two vclusters rather than two namespaces — 2026-08-30
**Context:** One physical box, and a request for a dev cluster and a prod cluster.
**Chose:** loft-sh vcluster, one per environment, inside the single host k3s.
**Because:** Gives a separate API server, CRDs and RBAC per environment, so a cluster-scoped
mistake in prod cannot reach dev. The isolation is logical only — one box means one power
failure takes both — but availability isolation was never achievable on a single node, so the
real question was blast radius of configuration error, and vcluster answers it.
**Rejected:** Plain namespaces — simplest, but "two clusters" would have been true only by
convention, with one shared API server and shared CRDs. Two k3d clusters — genuinely separate,
but it would have discarded the k3s install already done and pushed ingress into per-cluster
host port juggling.

### HCP Terraform free tier with a self-hosted agent, over Cloudflare R2 — 2026-08-30
**Context:** Terraform state needed a home. The k3s API server is reachable only over Tailscale.
**Chose:** HCP Terraform free tier (500 managed resources, $0) with the one self-hosted agent
the free tier includes, running as a systemd unit on homelab.
**Because:** The owner specifically values HCP's plan/apply UI and run history. The agent polls
outbound and executes runs locally, so it reaches the k3s API without any inbound access.
**Rejected:** Cloudflare R2 via the S3 backend — no extra daemon, no resource cap, and no new
vendor since Cloudflare was already in the plan, but CLI-only: no run UI, no run history, no
drift detection.
**Correction worth recording:** R2 was initially recommended on the reasoning that HCP's remote
execution could not reach homelab. That was wrong — it applies only to HashiCorp's *hosted*
runners, and the free tier's self-hosted agent closes the gap. An intermediate claim that HCP
had no free tier at all was also wrong; the legacy free plan ended 2026-03-31 and those orgs
moved to the free tier of the pay-as-you-go structure. Both HCP and R2 require a card on file,
so that is not a differentiator either way.

### Cloudflare Tunnel for ingress; dev stays private — 2026-08-30
**Context:** Serving from a residential connection. Open questions recorded in
`docs/secret-santa-v2/decisions.md` were ISP blocking of inbound 80/443, and TLS.
**Chose:** cloudflared as an in-cluster Deployment, outbound-only. One tunnel, prod routes only.
Dev is reachable over Tailscale and has no public hostname.
**Because:** It removes both open questions rather than answering them — no inbound ports, so
ISP policy is irrelevant, and TLS terminates at the edge, so no certificate lifecycle. Dev being
private costs nothing, since Tailscale already reaches the box, and keeps half-built things off
the internet.
**Rejected:** Port-forwarding plus DDNS and cert-manager — more moving parts, exposes the home
address, and depends on ISP policy that could change without notice.

### The platform owns the namespace, not the app repo — 2026-08-30
**Context:** Where the `secret-santa` namespace object should be defined.
**Chose:** `homelab-infra` creates the namespace, quota, NetworkPolicy and the deployer RBAC.
The app repo deploys workloads into a namespace it does not create.
**Because:** The namespace carries policy, which is a platform concern; and the app's CI
credential must be scoped to a namespace that already exists, so defining the namespace in the
app repo makes the dependency circular.
**Rejected:** Namespace in the app repo alongside the manifests — the owner's initial instinct,
and reasonable, but it cannot resolve the bootstrapping order.

### Sealed Secrets for app secrets, Terraform for infra tokens — 2026-08-30
_Superseded by "Application secrets in Terraform state" on 2026-09-03._
**Context:** Anything Terraform creates as a `kubernetes_secret` is stored in state in plaintext.
**Chose:** A split. Infra tokens (Cloudflare, tunnel, GHCR) stay Terraform-managed. Application
secrets go through Sealed Secrets, with a controller inside each vcluster.
**Because:** `secret-santa-v2`'s `Tokens__ParticipantKey` cannot be rotated in normal operation
— participant links are HMAC-derived at send time, so rotation invalidates already-delivered
mail. A secret that cannot be rotated must not sit in a state file. Infra tokens rotate cheaply,
so the same reasoning does not apply to them.
**Rejected:** `kubernetes_secret` for everything — simplest and adds no component, but puts the
one irreplaceable secret in state. SOPS+age — the plaintext still reaches state at apply time,
so it solves the git problem and not the state problem.

### Kustomize over Helm for the app manifests — 2026-08-30
**Context:** Two environments differing in replica count, hostname, and a few config values.
**Chose:** Kustomize, with overlays per environment.
**Because:** That difference is overlay-shaped, not template-shaped, and `kubectl` already
embeds Kustomize, so it adds no tool. `preferences/stack.md` requires naming a capability the
slim option lacks before choosing the heavier one, and there is none here.
**Rejected:** A Helm chart — earns its place when something is redistributable or heavily
parameterised. This is neither.

### Plain ConfigMap rather than configMapGenerator — 2026-08-30
**Context:** The migrate Job and the Deployment must consume identical configuration, but live
in separate kustomizations so migration can be sequenced before rollout.
**Chose:** A plain ConfigMap in a shared `config/` base that both kustomizations include.
**Because:** A generator's name hash would only match across the two if the literals were
duplicated byte for byte, and duplicated configuration is precisely how the two drift.
**Rejected:** configMapGenerator with duplicated literals — the hash gives automatic rollout on
config change, but at the cost of two copies of the truth. The deploy workflow issues an
explicit `rollout restart` instead.
