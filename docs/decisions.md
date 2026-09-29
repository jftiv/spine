# Cross-repo decisions

Append-only. Newest first. Decisions whose reasoning involves more than one repo. A repo's own
`docs/decisions.md` records the local consequence; the argument lives here.

The platform-side decisions that shape tenants (the platform owns the namespace, Kustomize over
Helm, plain ConfigMap over generator) are in `homelab-infra/decisions.md`. homelab-infra is part
of spine, so its docs stay here (see `landscape.md`).

### Postgres in-cluster replaces Hostinger MySQL — 2026-09-04
**Context:** The 2026-08-30 decision put the API on `homelab` and kept the Hostinger MySQL
allowlist closed, at the cost of a new assumption: that the home WAN address is stable. Working
that assumption produced no good answer — the allowlist stores literal IPs, DDNS cannot help, a
static IP means an ISP plan, and every remaining option was monitoring or proxying the symptom
rather than fixing it. "How do I pin my external IP" has no satisfying answer, which was the
signal that it was the wrong question.

**Chose:** Run PostgreSQL in the cluster, on the same box as the API, managed by CloudNativePG,
with continuous WAL archiving and scheduled backups to Cloudflare R2. Drop the Hostinger MySQL
dependency entirely. Sequenced as **M6.5**, before the M7 deploy.

**Because:**
- **Availability was never being bought.** The API serves from `homelab` through the tunnel, so
  when the box is down the app is down regardless of where the database lives. Keeping the
  database off-box bought no uptime and added a network path that could fail on its own.
- It removes the dependency instead of monitoring it: no static IP, no allowlist, no WAN probe.
- **It ends the shared-host exposure.** Opening the allowlist was rejected on 2026-08-30 because
  that MySQL server also stores other applications' databases. Leaving the server removes that
  blast radius from this project rather than routing around it.
- **It unpins EF Core.** The project targets `net10.0` but is held at EF 9 because Pomelo ships no
  EF 10 provider. Npgsql does. The repo's `docs/ef-versions.md` stops being a problem the project carries.
- `preferences/stack.md`: PostgreSQL for new work, MySQL only where the system is already on it.
- **The cost is at its minimum right now.** M7 has not been crossed, so there is no production
  data — the migration is regenerated, not converted. Every week after deploy this gets more
  expensive, and December is the window that matters.

**The cost, measured rather than guessed:** 251 `HasColumnType` annotations across 6
configuration files, 3 stored computed columns using backtick-quoted MySQL, one raw
`ON DUPLICATE KEY UPDATE` upsert in `DailyQuota`, one `MySqlException` number check in
`EmailOutbox`, one migration to regenerate, and a Testcontainers swap touching ~10 test files.
Broad but mechanical. The part that is *not* find-and-replace: **Postgres has no `unsigned`**, so
every `tinyint/int/smallint unsigned` needs a per-column decision about width and whether the
range is worth a CHECK constraint.

One thing that could have been ugly and is not: MySQL's default collation is case-insensitive and
Postgres is case-sensitive, but the schema already does not lean on that — the three
`lower(trim(...))` stored columns exist so email uniqueness never depended on collation.

**What this newly puts at risk, and the answer:** today a disk failure on `homelab` loses no
data, because durability is Hostinger's problem. Afterwards it loses everything since the last
backup, on a single consumer SSD with no RAID, where `local-path` means the PVC *is* that disk.
Nightly `pg_dump` is therefore not sufficient — a 24-hour RPO in December means telling people to
re-run their exchange, the one failure this app cannot apologise its way out of. **Continuous WAL
archiving is load-bearing to this decision, not an enhancement attached to it.** And a backup that
has never been restored does not count, so the restore drill sits inside M6.5, not after it.

**Rejected:**
- **Self-hosting MySQL 8 in the cluster instead.** Captures the locality, the allowlist deletion
  and the shared-host win at *zero application code change* — honestly the cheaper option this
  week. Rejected because it pins the project to EF 9 permanently and contradicts the stack
  preference. **Kept as the explicit fallback if the calendar tightens**, because it buys most of
  the value for almost none of the work.
- **Buying a static IP from the ISP.** Treats the symptom. Leaves the shared-host exposure, the
  external network path and the EF 9 pin all standing, and costs monthly.
- **A VPS proxying MySQL on a fixed address.** Same symptom-only objection, plus a new always-on
  component to keep alive. (A proxy, not a Tailscale exit node — an exit node would push all
  homelab egress, including the tunnel and image pulls, through a $5 box.)
- **Opening the Hostinger allowlist.** Rejected 2026-08-30, still rejected, same reason.
- **A hand-rolled StatefulSet plus a backup CronJob.** More code and weaker guarantees than
  CloudNativePG, which does WAL archiving, PITR and restore as declarative resources.

**Unverified and load-bearing:** CloudNativePG's barman-cloud backup targets S3-compatible
storage and R2 is S3-compatible, but that pairing is unproven here and R2 has known quirks around
multipart uploads and checksums. It is the riskiest assumption in the plan, which is why Phase 0
exists to kill it before any application code changes.

### The API runs on self-hosted k3s at home; the allowlist stays closed — 2026-08-30
**Context:** Resolves the OPEN entry below, raised 2026-07-26 and unanswered for a month. The
owner has since stood up an Ubuntu box (`homelab`) with k3s and Tailscale.
**Chose:** Option 3. The API runs in a `prod` vcluster on `homelab`. Migrations run as a
Kubernetes Job on the same node.
**Because:** It does not work around the blocker, it removes it. The blocker was that Fly's
`release_command` machines egress from an unpredictable address, so the migrate step could not
pass an IP allowlist. On one box the app pod and the migrate Job share one egress address, so
**the Hostinger allowlist stays closed** — and that mattered more than cost, because that MySQL
server also holds other applications' databases.

The two open questions recorded against option 3 are answered rather than accepted:
*ingress and TLS from a residential connection*, and *whether the ISP blocks inbound 80/443*,
both dissolve under a Cloudflare Tunnel, which is outbound-only and terminates TLS at the edge.
The remaining two stand: **the machine is now the owner's to patch**, and **uptime across the
December window** rests on home power and ISP.

**A new dependency replaces the old one.** The allowlist stores literal IP addresses, so the
approach assumes the home WAN address is stable. **DDNS does not help** — it keeps a DNS name
current, which is no use to a rule that compares literal addresses. If the ISP rotates the
address the app loses its database. Unverified as of this entry; see `sessions/secret-santa-v2.md`.
_This paragraph is superseded by the 2026-09-04 entry above: the WAN-stability assumption is
retired along with the MySQL dependency itself. The rest of this entry — the API running on
k3s at home, migrations as a Job on the same node — still stands._

**Rejected:** Fly plus opening the allowlist — the fastest path, but it exposes every account on
that MySQL host to the internet, and new app-scoped credentials bound only the leak of *this*
app's credential, not the exposure of everyone else's. A DigitalOcean droplet — still the honest
fallback if the WAN address turns out to rotate, and the reason that option is not deleted here.
**Cost was never the deciding factor**, though this option is also the cheapest.

### RESOLVED — Where the API runs, and what happens to the MySQL allowlist — raised 2026-07-26
_Resolved 2026-08-30 in favour of option 3 (self-hosted k3s). See the entry above._
**Context:** Deploy artifacts are built and verified for Fly. The blocker is that the Hostinger
MySQL server has an IP allowlist, and Fly's `release_command` machines are not covered by
app-scoped static egress IPs.
**Unresolved.** Owner weighing (1) Fly + open allowlist + app-specific credentials, (2) a
DigitalOcean droplet, which has a static IP inherently and keeps the allowlist, or — added
2026-07-31 — (3) **self-hosting on k3s on a small PC at home**, which the owner is currently
leaning toward and needs hardware pieces for.

Option 3 notes, not yet researched in depth: it keeps the allowlist (home IP is static enough
with DDNS or a static-IP plan), costs nothing monthly, and the container already built runs
unchanged. The new questions it raises are ingress and TLS from a residential connection,
whether the ISP blocks inbound 80/443, uptime over the December window that actually matters,
and that the machine becomes the owner's to patch. **Deliberately not researched yet** — the
owner is still gathering hardware and has not committed.

**The fact that should carry the most weight:** *that MySQL server also stores other apps'
data.* The allowlist is not protecting this project — it is protecting every database on that
host. Scoping a new MySQL user to the `secret_santa` schema bounds what a leak of **this app's**
credential can reach, which is worth doing regardless. It does not bound what opening the host
rule exposes: every account on that server becomes reachable from the internet, and password
strength becomes the only remaining barrier for all of them. Those are different risks and only
the first is fixed by new credentials.

**Cost is close to a wash.** DO's lowest droplet is roughly Fly's egress-IP price, includes a
static IP, and has no cold start. Against that, a droplet is a machine the owner now patches,
certificates, and deploys to, versus a managed container.

**To verify before committing to Fly:** whether the owner's org is genuinely grandfathered onto
a free plan. That is an assumption, not a confirmed fact, and option 1's economics depend on it.

### Client and gift guides on Hostinger, API on Fly — 2026-07-25
_API half superseded by the self-hosted k3s decision on 2026-08-30. Fly config and workflow deleted 2026-09-27. The client half still stands._
**Context:** Hard constraint of no new cloud spend. Hostinger static hosting and one existing
Fly app are what exists.
**Chose:** Keep the current split. React SPA and prerendered gift guides static on Hostinger;
containerized .NET API on the existing Fly app. CORS and a base-URL constant are accepted costs.
**Because:** Owner's call, and it keeps free Hostinger bandwidth serving the gift guides — the
pages that actually earn — with no cold start on an email click-through.
**Rejected:** Single container serving the SPA from .NET (simpler, one origin, no CORS — but
puts revenue pages behind a scale-to-zero cold start). Container stays Fly-agnostic so a
droplet or k8s pod remains possible.

