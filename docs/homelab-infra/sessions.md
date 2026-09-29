# homelab-infra — session log

Newest first.

## 2026-09-27 — Databases layer applied, mTLS defect fixed, restore proven on dev

**Changed:**
- PR #3 (`15-databases`) merged and applied layer by layer: `00` (+1, the R2 bucket), `15` (+44),
  `20` (~2, the generated connection string merged into `secret-santa-config`).
- **PR #4:** `pki.tf` switched from a private CA to pinned self-signed certificates. On first
  apply, neither Postgres cluster started because the operator couldn't handshake with the
  Barman plugin. Plan +4 / ~4 / −12, only certificates and secrets.
- Both `secret-santa` Clusters are healthy, and WAL archiving to R2 works in both.
- **Restore test on dev (M6.5 Phase 0 gate): passed.** Row A written, on-demand base backup
  `20260927T043001` taken (8s), row B written and its WAL segment forced to R2. A new Cluster
  bootstrapped from R2 alone contained **both** rows, so base backup and WAL replay both
  work. 53s to healthy. The throwaway schema, the restored Cluster and its PVC were all removed.
  The Backup object was kept as dev's first base backup.

**Decisions:** Pinned self-signed certificates for the operator↔plugin channel, correcting the
09-06 CA design. Logged in `decisions.md`, along with the 09-06 decisions that hadn't been
recorded yet.

**How the mTLS defect was found** (worth not re-deriving): Cluster `phaseReason` said
`tls: certificate required`. The plugin runs with `--client-cert=/client/tls.crt`, and the
operator's `plugin_controller.go` builds `RootCAs` from the server secret's `tls.crt`. Both pin
the exact certificate, and neither reads `ca.crt`. Reproduced locally in Go with the same
`tls.Config` shapes before the fix shipped: CA-signed failed with the production error, pinned
succeeded, and an impostor certificate with the same CN was rejected.

**Other things hit along the way:**
- The org's GitHub OAuth token had been revoked since 09-06. The PR #3 merge webhook fired,
  but the clone failed with `SIC-001`, while workspace settings still showed green. The owner
  reconnected the provider at org level. In `troubleshooting.md`.
- Tailscale on the Mac was stuck at `WantRunning: false`, and the menu-bar toggle didn't clear
  it. `tailscale up` from the CLI did.
- The k3s API answers on the LAN (`<lan-ip>`) without Tailscale. Used as a fallback today,
  and noted as a gap.

**Open:**
- **Prod restore drill and runbook entry**, M6.5 Phase 5. The raw steps are in
  `architecture.md` → Restoring.
- **Connection string not read back.** Reading `secret-santa-config` was declined as a
  production-secret read. The owner can check it with the host masked. Until the app does its
  Phase 2 provider swap, the current MySQL build **can't** run against the Postgres string now
  in the secret, so nothing should be deployed from the pre-M6.5 app build.
- R2 key scope: `bootstrap.md` says *Admin Read & Write*, which is account-wide. The design says
  bucket-scoped.
- What revoked the GitHub OAuth token is unknown. Consider HCP's GitHub App integration instead,
  which isn't tied to a personal token. Switching means re-pointing all four workspaces.
- `docs/runbook.md` in the repo has uncommitted local edits (Host networking section, from
  2026-09-04). They were left untouched.

## 2026-09-06 — `15-databases` written: CNPG per vcluster, Barman plugin, R2 bucket

_Backfilled 2026-09-27 from commit `6b0a88d`. No spine docs were written in that session._

**Changed:**
- New layer `terraform/15-databases` and workspace `homelab-databases`: the CNPG operator and
  Barman Cloud plugin via Helm inside each vcluster, a `data` namespace with quota and
  default-deny, one Postgres Cluster per app via a local chart, an ObjectStore, a daily
  ScheduledBackup, the app role password, and the connection strings as outputs.
- `00-cloudflare`: R2 bucket `homelab-postgres-backups` (`enam`), with endpoint and name as
  outputs.
- `20-tenants`: reads connection strings from `15` and merges them into `secret-santa-config`.
  `ConnectionStrings__Default` is no longer a workspace variable.
- `bootstrap.md`: the fourth workspace, explicit remote-state sharing, and the hand-made R2 key.

**Decisions:** Seven, all in `decisions.md` dated 2026-09-06. Three depart from the M6.5 plan:
the operator inside each vcluster, not `10-host`; a shared `data` namespace; and the plugin
instead of the in-tree object store.

**Open (as of that session):** PR #3 opened, with its speculative plans failing on unapplied
upstream outputs. **Phase 0 was skipped:** the real layer was built without first proving a
restore. The CA-based `pki.tf` shipped in this commit and was broken, but that only showed up
on apply.

## 2026-09-04 — homelab moved off wifi onto the wired LAN; node IP repinned

**The finding:** homelab was running the entire platform over **wifi**, on the Google router's
subnet (`<old-wifi-ip>`), one NAT *below* the boundary the double-NAT exists to create. The
wired run to the Netgear was plugged in and had carrier the whole time — it had simply never been
configured. `subiquity` wrote `enp2s0: accept-ra: true` with **no `dhcp4`**, so the interface came
up, gained IPv6LL, and never sent a DHCP request. The journal shows no DISCOVER at all, which is
what distinguished a client-side omission from the Netgear refusing to lease.

The isolation the topology was built for had therefore never been in effect.

**Changed:**
- netplan: `dhcp4: true` plus `dhcp4-overrides.route-metric: 100` on `enp2s0` (wifi was 600, so
  ethernet wins the default route without turning anything off); `optional: true` on `enp1s0`,
  the empty port; the whole `wifis:` block removed once wired was proven.
- Netgear DHCP reservation for MAC `<enp2s0-mac>` → **`<lan-ip>`**.
- `node-ip: <lan-ip>` appended to `/etc/rancher/k3s/config.yaml`. k3s restarted and the node
  object picked up the new `InternalIP` with no node deletion and no flannel intervention.
- `jtaulman` added to `k3s-readers`.

**Verified after two reboots:** `enp2s0` leases unassisted, single default route, `wlp3s0` down
with no address, k3s `active`, node `Ready` at `<lan-ip>`, cloudflared 2/2, both vclusters
answering through their NodePorts, and `https://api.secret-santa.net` returning its 404. The
vcluster kubeconfigs were unaffected, as the `127.0.0.1` + fixed-NodePort design predicted.

**Correction to the 2026-09-03 entry:** "the kubeconfig group grant now survives a k3s restart"
was half true. `/etc/rancher/k3s/k3s.yaml` is `root:k3s-readers 0640` and that ownership does
persist — but the operator account had never been *added* to `k3s-readers`, so unprivileged
on-box `kubectl` had never worked. Fixed this session.

**Also worth remembering:**
- The two ethernet MACs differ by one character — `<enp1s0-mac>` is `enp1s0` with no cable, `<enp2s0-mac>` is
  the live link. The first reservation attempt went to the empty port.
- The starship prompt's `☸ homelab(host)` shows the **kubectl context**, not the host you are
  logged into. It reads identically on the Mac and on the box. `hostname` is the reliable check.
- `Required For Online: yes` on an interface that never leases adds a ~2 minute
  `systemd-networkd-wait-online` delay at boot. That, not a failure, was why the first reboot
  looked like it never came back.
- A reboot picked up kernel `7.0.0-29` → `7.0.0-30` with no intervention.

**Rollback available:** `~/netplan-prewifi-removal-2026-09-04.yaml`, mode 600, still contains the
wifi PSK. Delete it once wired has run clean for a week. The wifi radio was deliberately left
functional rather than `rfkill`-blocked, so restoring that file is a complete recovery path if
the cable or the Netgear port fails. With `NetworkManager` inactive and no netplan wifi stanza,
`wlp3s0` cannot re-associate on its own.

**Open:**
- **Item 1 is not resolved by any of this.** The Hostinger allowlist keys off the **WAN**
  address, which is still ISP DHCP and still the single reading `<wan-ip>`. LAN and WAN are
  different layers; pinning the LAN address changes nothing there.
- ~~`20-tenants` status discrepancy~~ — resolved: the owner confirmed all three workspaces show
  as applied in `app.terraform.io`. The docs were stale, not the cluster. `overview.md` corrected.
- The wifi PSK was exposed in a session transcript. The owner has accepted this knowingly — it
  is an isolated guest SSID — and will rotate it later.


## 2026-09-03 — Platform stood up: tunnel, vclusters, VCS-driven runs

**Changed:**
- Applied `00-cloudflare` and `10-host`. Tunnel live, `api.secret-santa.net` resolving,
  cloudflared 2/2, both vclusters running. `20-tenants` plans clean (20 resources) but is not
  applied.
- Repo pushed to `github.com/jftiv/homelab-infra`; all three workspaces created via API and
  connected to VCS with per-layer working directories and trigger prefixes, `auto-apply` off,
  explicit (not global) state sharing.
- Three kubectl contexts — `dev`, `prod`, `homelab` — built on the Mac, plus `kubectx`/`kubens`
  and a starship prompt indicator. Recipe in the repo's `docs/runbook.md`.

**Decisions:** cloudflared pinned by **version tag, not digest** — owner's call, and
`preferences/stack.md` was rewritten to match: third-party images take a version tag and
upstream bug-fix releases, while the project's own CI-built artifacts stay digest-pinned because
that is artifact identity rather than version selection. vcluster bumped 0.34.0 → 0.36.1.

**Two corrections worth remembering:**
- I told the owner to set workspace execution mode to **Remote**. It must be **Agent** — Remote
  runs on HashiCorp's infrastructure and cannot reach a tailnet-only cluster. Caught before it
  cost anything.
- I concluded a PR did not exist because the runs API returned nothing. The API hides plan-only
  runs unless asked for them. Trusting an incomplete query over what the owner said.

**Verified rather than assumed:** vcluster 0.36.1 accepts the `sync.toHost` /
`controlPlane.proxy.extraSANs` / `exportKubeConfig` keys; cross-layer state sharing carries the
tunnel token into the cluster; the agent reaches k3s from inside a run; the certificate SANs
cover `homelab` so kubectl works from the Mac without `--insecure`; the kubeconfig group grant
now survives a k3s restart.

**Open:**
- `20-tenants` not applied. Sealing keys must be backed up **before** the first SealedSecret —
  `Tokens__ParticipantKey` cannot be regenerated without invalidating delivered mail.
- **Automatic speculative plans** is off; PRs produce no plan until it is enabled in the UI.
- PR #1 is unmerged, so `main` does not reflect what is applied.
- The WAN address (`<wan-ip>`) is still a single reading, and the closed MySQL allowlist
  depends on it being stable.
- vcluster API NodePorts bind on every interface; no firewall rule restricting them yet.
- GitHub-hosted runners still have no network path to the cluster for the app deploy.

## 2026-08-30 — Repo created; platform defined in Terraform, nothing applied

**Changed:**
- Created `~/source/homelab-infra` from nothing, on branch `bootstrap-platform`. Three Terraform
  layers — `00-cloudflare` (tunnel, ingress rules, DNS), `10-host` (namespaces, two vclusters,
  cloudflared), `20-tenants` (per-vcluster namespace, quota, NetworkPolicy, deployer RBAC, GHCR
  pull secret) — plus `docs/bootstrap.md`, `docs/runbook.md` and `bootstrap/agent.md`.
- All three layers pass `terraform fmt` and `terraform validate` against real provider schemas
  (cloudflare 5.24.0, kubernetes 2.38.0, helm 2.17.0). Terraform 1.16.0 was installed from the
  `hashicorp/tap` — it is no longer in homebrew core.

**Decisions:** Seven logged. The load-bearing ones: vclusters over namespaces, HCP free tier
with a self-hosted agent over R2, Cloudflare Tunnel with dev kept private, the platform owning
the namespace object, and the two-class secret split driven by `Tokens__ParticipantKey` being
unrotatable.

**Verified against the real box** (Ubuntu 26.04, kernel 7.0.0-29, 16 cores, 27 GB RAM, 80 GB
free, k3s v1.36.2 active, no Docker):
- The API server certificate carries `DNS:homelab` but **not** `<tailnet-ip>`. Pointing the
  kubeconfig at the hostname therefore needs no `tls-san` change and no certificate reissue —
  Tailscale MagicDNS resolves the name, and a TLS handshake from the Mac was confirmed. The
  bootstrap doc originally prescribed reissuing the certificate; that was unnecessary and has
  been corrected.
- `/etc/rancher/k3s/config.yaml` exists and contains only `debug: true`, so any k3s config must
  be appended, not written over. That `debug: true` is also why every on-box `k3s kubectl` call
  prints `DEBU` lines — noise, not a fault.
- Default add-ons are all present and are what the design assumes: Traefik (Deployment + a
  `traefik` LoadBalancer Service in `kube-system`, and the **default** IngressClass), CoreDNS,
  metrics-server, local-path storage. The tunnel's target
  `http://traefik.kube-system.svc.cluster.local:80` resolves to a real Service.
- k3s was **not** started with `--disable-network-policy`, so NetworkPolicy is enforced.
- Traefik's ServiceLB holds two NodePorts of its own. The ports the design picks — <dev-app-port> (dev
  app), <dev-api-port> (dev API), <prod-api-port> (prod API) — do not collide.
- Cluster access from the Mac now works via `https://homelab:6443`, with no k3s change.

**Working agreement established:** the operator runs anything requiring `sudo` on homelab; the
assistant does unprivileged work directly. Scripting `sudo` over SSH with a password is blocked
by the harness and should not be worked around.

**Open:**
- **Nothing has been applied.** No HCP organization, no agent installed, no `terraform apply`.
  All of Phase 0 in `docs/bootstrap.md` is outstanding and most of it cannot be automated.
- **Whether the home WAN address is stable is unverified**, and it is the assumption the whole
  approach rests on. DDNS does not help: the Hostinger allowlist stores literal addresses.
  Baseline reading `<wan-ip>`; needs re-checking after a router reboot and after a few days.
- **sudo on homelab needs a password and is not NOPASSWD.** The tfc-agent install is a run of
  sudo commands and should be done interactively.
- The vcluster API NodePorts bind on every interface, so anything on the home LAN can reach
  them. Client-certificate auth is required, so this is not an open door, but a firewall rule
  restricting them to `lo` and the Tailscale interface has not been written.
- `cloudflared_image` has no default and must be set to a digest before the first apply.
