# homelab-infra — troubleshooting

## Diagnosed

**A CNPG Cluster sits at "Cluster cannot proceed to reconciliation due to an error while
interacting with plugins", with no pods.** Read `.status.phaseReason`. If it says
`tls: certificate required`, the operator↔Barman-plugin mTLS handshake is failing and the
operator won't build the database until it works. On 2026-09-27 the cause was CA-signed
certificates, when both ends pin the peer's exact `tls.crt`. Fixed in `pki.tf` (PR #4). Check
with `openssl x509 -noout -subject -issuer` on both secrets in `cnpg-system`: each certificate's
issuer must equal its own subject. After a certificate change the operator picks up new secrets
by itself. If it doesn't within a minute or two, restart `deploy/plugin-barman-cloud`.

**HCP runs fail with `SIC-001 … Failed on ls-remote … Invalid username or token`, while the
workspace's VCS settings show green.** The org's GitHub OAuth token (`ot-…`, one per org, shared
by all four workspaces) has been revoked or has expired on GitHub's side. The green indicator
only means the workspace is *bound* to a token. It never tests the token. Webhooks still
arrive, so a merge still triggers an attempt, and every clone fails. Fix at the **org** level:
Settings → Version Control → Providers → GitHub.com → reconnect. Runs triggered while the token
was dead are not replayed and must be started by hand. Seen 2026-09-27; the token had worked on
2026-09-06, and what revoked it is unknown.

**It keeps recurring, and the cause is still unknown.** As of 2026-10-03 the owner reconnects
roughly daily. What is known:
- HCP's VCS event log (`GET /api/v2/organizations/<org>/vcs-events`) shows `There was an error
  fetching data from repository` on 09-27 and twice on 09-29. This log is the quickest way to
  confirm the token is the problem.
- The `ot-…` token has had the same ID since it was created on 2026-09-03. Reconnecting
  repairs it in place, so something on GitHub's side keeps invalidating the authorization.
- On 2026-10-03, PR #6 got no speculative run and no logged error, even though GitHub shows the
  webhook delivered with `200`.
- **Switching to HCP's GitHub App connection did not work.** "GitHub App" is not offered in
  workspace VCS settings for this org. Installing the app by hand (it is still listed on GitHub
  as "Terraform Cloud") ended on an HCP 404 page.

Next step: check GitHub → Settings → Applications → Authorized OAuth Apps for duplicate
authorizations of the app behind HCP's "GitHub.com" provider. GitHub keeps at most ten tokens per
user and OAuth app, and authorizing an eleventh revokes the oldest.

**To plan a branch while the connection is down, or at any time,** run `terraform init &&
terraform plan` in the layer's directory on that branch. It runs remotely on the agent with the
workspace's variables. Applies still have to come from `main`.

**The workspace's VCS settings page looks empty after "Change source".** That page is the
provider picker for a *new* connection. Leaving it without saving keeps the existing connection;
the workspace API still shows the repo, branch and working directory.

**A PR's speculative plans fail with "Unsupported attribute" or "Unable to find remote state".**
Not a bug when the PR adds an output in one layer and consumes it in another. Speculative plans
read the *applied* state below them, which doesn't have the output yet. Merge, then apply layer
by layer. See `architecture.md`, Terraform layering.

**Tailscale won't start from the Mac's menu bar; `homelab` doesn't resolve.** Seen 2026-09-27:
logged in, macOS showing the VPN as Connected, but `tailscale status --json` reported
`BackendState: Stopped`, and `tailscale debug prefs` showed `WantRunning: false`. No MDM, other
VPN or exit node involved. `/Applications/Tailscale.app/Contents/MacOS/Tailscale up` fixed it
immediately. Why the toggle failed wasn't found; the macOS logs that would say need sudo.
While it's down, `kubectl --server https://<lan-ip>:<port> --tls-server-name homelab` works
from the home LAN (6443 host, <dev-api-port> dev, <prod-api-port> prod).

**HCP's runs API hides plan-only runs by default.** `GET /workspaces/<id>/runs` returns an empty
list even when speculative and CLI plan-only runs exist; they only appear with
`filter[operation]=plan_only`. Do not conclude from an empty list that nothing has run — that
mistake led to telling the owner their PR did not exist when it did.

**A pull request produced no speculative plan.** GitHub events were arriving (config versions
with `source=github` existed) but every one had `speculative=false`. Everything settable through
the API was already correct. The gate is **Automatic speculative plans**, a per-workspace VCS
setting in the UI that appears to default off when VCS is attached via the API.

**`ssh` under a non-interactive shell silently fails password auth.** Running the kubeconfig
fetch through a harness without a TTY gives ssh no way to prompt, so it consumes empty input and
fails — *after* the shell has already created the redirect target, leaving a zero-byte
`~/.kube/config` and a misleading `localhost:8080` connection error. Write to a temp file and
`test -s` it before installing.

**Running the kubeconfig fetch on the box instead of the workstation looks like failure.** It
writes a valid kubeconfig into homelab's own home directory, but the on-box `k3s kubectl` still
reads `/etc/rancher/k3s/k3s.yaml` and fails on permissions. The fetch is a workstation command.

## Anticipated


**`kubectl` fails TLS verification against `<tailnet-ip>`.** k3s issues the API server
certificate for a fixed set of names. If the Tailscale address is not among them, add it via
`tls-san` in `/etc/rancher/k3s/config.yaml`, delete
`/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.{crt,key}` and restart k3s. Using
`config.yaml` rather than the systemd unit means a k3s upgrade preserves it.

**~~The Terraform agent fails to read the kubeconfig after a k3s restart.~~** Resolved
2026-09-03: `write-kubeconfig-group: k3s-readers` and `write-kubeconfig-mode: "0640"` are set in
`/etc/rancher/k3s/config.yaml`, and a restart was confirmed to reissue the file as
`root:k3s-readers 0640`. Before that it was set by hand and would not have survived.

**An Ingress applies cleanly inside a vcluster and routes nothing.** Almost certainly
`sync.toHost.ingresses` or `sync.fromHost.ingressClasses` is off. The object exists in the
virtual cluster and never reaches the host Traefik, so there is no error to find — only silence.

**A migrate Job fails and it looks like a database problem.** `--migrate` runs the app's full
startup validation before it reaches the migrate branch, so a missing `Email__ApiKey` or
`Captcha__SecretKey` fails the Job. Read the exception before assuming the database.

**`/readyz` returns 503 while `/healthz` is 200.** That is a real and meaningful state, not a
broken deploy: the app is up and the database is unreachable. With in-cluster Postgres, check
in order: the Cluster's status in `data`, then the `allow-secret-santa-to-secret-santa`
NetworkPolicy (not yet traffic-tested), then the connection string host. The old first check,
the WAN address against the Hostinger allowlist, applies only until M6.5 Phase 6.

**A restored or scratch Cluster never schedules.** Check the `data` namespace quota before
anything else. The live cluster uses 1280Mi of the 2Gi memory limit, and a second full-size
cluster doesn't fit. Not yet observed here. Expect the Cluster to just sit in "Setting up
primary", with the actual `exceeded quota` message only in the events of the recovery Job or
instance (`kubectl -n data get events`), not in the Cluster's status.

**Terraform appears to hang.** The free tier includes one agent, so one concurrent run. A second
apply queues rather than failing.
