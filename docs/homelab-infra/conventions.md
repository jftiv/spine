# homelab-infra — conventions

## Terraform

- **Numbered layers, applied in order.** `00-` before `10-` before `20-`. Cross-layer values
  move via `terraform_remote_state`, never by copy-paste.
- **Pin everything.** Chart versions and image digests are pinned. `cloudflared_image` has a
  variable `validation` block that rejects anything not `image@sha256:...` — enforcement, not
  discipline, because `preferences/stack.md` requires digest pinning for production containers
  and `agents/devops.md` forbids `latest` outright.
- **No defaults for things that must be a deliberate choice.** `cloudflared_image` has no
  default for this reason; a default would quietly violate the rule above.
- Run `terraform fmt -recursive` and `terraform validate` before considering anything done.
  `terraform init -backend=false` validates without touching HCP.
- Commit `.terraform.lock.hcl`. Never commit `.terraform/` — it is ~450 MB of provider binaries.

## Secrets

- One mechanism: every secret is Terraform-managed and lives in HCP state. Table of what goes
  where in `architecture.md`. (This reverses the pre-2026-09-03 rule that app secrets never
  touch Terraform. See `decisions.md`.)
- **Generate, don't type**, wherever Terraform can: database passwords and connection strings
  come from `15-databases`. Hand-typed sensitive variables are reserved for credentials that
  must come from outside: the GHCR PAT, the R2 key, and third-party API keys.
- **Never give Terraform's Cloudflare token `User > API Tokens > Edit`.** Tokens Terraform
  would need are made by hand. Reason in `decisions.md` (2026-09-06, R2 key).
- A generated value is merged **last** into any map that also takes variables, so a stale
  variable loses.

## Naming

- Host namespace for a virtual cluster: `vcluster-<env>`.
- Application namespace inside every vcluster: the same name in each, currently `secret-santa`.
  The environment is the cluster, not the namespace — that is the point of the split.
- HCP workspace: `homelab-<layer>`.

## Working with the clusters

**One kubectl context per API server**, named for the environment: `dev`, `prod`, and `homelab`
for the host underneath. `kubectx <name>` switches; `kubectl --context=<name>` runs one command
without switching. Full recipe, including how to rebuild the contexts on a new workstation, is
in the repo's `docs/runbook.md`.

The environment is the **cluster**, not the namespace. Both vclusters contain a namespace called
`secret-santa`; there is no `secret-santa-dev`. Anything that distinguishes environments by
namespace name is a sign something has drifted back toward the design we rejected.

Two details that are easy to get wrong:

- The kubeconfigs vcluster generates point at `127.0.0.1:3x443`, which is correct only for the
  Terraform agent running on homelab. From any other machine the server must be rewritten to the
  **hostname** `homelab`, never the Tailscale IP — `controlPlane.proxy.extraSANs` covers both,
  but the hostname is what k3s already signs for and keeps the two paths consistent.
- `kubectx` switches context **globally**, across every open terminal. The prompt must show the
  active context (starship's `kubernetes` module) or "I thought I was in dev" is a matter of
  time. Use `kubectl --context=prod` explicitly for anything destructive.

Operator contexts carry vcluster **admin** credentials. CI does not use them — it uses the
namespace-scoped `deployer` ServiceAccount from `20-tenants`.

## Tenant repos

- Tenants deploy into a namespace they do not create, with a namespace-scoped ServiceAccount
  token issued by `20-tenants`.
- A tenant's databases live in the shared `data` namespace, created by `15-databases`, never
  by the tenant. A tenant gets a connection string in its config Secret, not access to `data`.

## Databases

- **One CNPG Cluster per application**, named for the application, in `data`. Never a shared
  cluster: point-in-time recovery works per Cluster.
- Allow rules into `data` are keyed on `cnpg.io/cluster=<name>`, never on the namespace alone.
  The namespace is shared.
- **Any Cluster built from a backup must not declare the Barman plugin as its WAL archiver.** It
  would write into the source's R2 path. Use `externalClusters` only.
- Scratch clusters (drills, experiments) must fit the `data` quota alongside the live one, and
  must be deleted along with their PVC when done.
