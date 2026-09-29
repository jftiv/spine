# secret-santa-v2 — session log

Entries before 2026-09-28 refer to `architecture.md`, `decisions.md` etc. in spine. Those files
now live in the repo's own `docs/`; cross-repo decisions are in spine's `docs/decisions.md`.

Newest first.

## 2026-09-28 — Docs moved into the repo; comments trimmed

**Changed:**
- PR #1 (M6.5 Npgsql swap + k3s deploy path) merged.
- PR #2: architecture, decisions, conventions, troubleshooting and design notes moved from spine
  into `docs/`, with `docs/README.md` as the entry point. `deploy.md` gained manifest layout,
  ingress/TLS, CI image and workflow sections. PR #1's comments trimmed to match (156 lines out,
  37 in). Build clean, 405 tests green, rendered manifests identical to `main`.

**Decisions:** Two-tier docs (repo `docs/` for the repo, spine for cross-repo) and the comment
rule, both in spine's `preferences/conventions.md` and the `doc-sync` playbook. The four
hosting/database decisions moved to spine's `docs/decisions.md`; the repo keeps two short
local-consequence entries.

**Open:**
- `deploy/migrate/job.yaml` claimed the Job name carries the git SHA via `nameSuffix`. It does
  not; the workflow deletes the old Job instead. Comment removed. Decide whether a SHA suffix is
  actually wanted (it would keep failed Jobs inspectable across deploys).
- The "delete the old repo" decision's leaked passwords were left out of the repo copy.
  They are still in the pre-split spine file, which has never been committed.

## 2026-09-27 — M6.5 Phase 2+3: Pomelo → Npgsql, tests green on Postgres

**Changed:**
- Branch `m6.5-npgsql` in `secret-santa-v2` (**uncommitted**). EF 10.0.12 + Npgsql 10.0.3. There's
  one `UseSecretSantaPostgres` for the API, design-time and tests. Types converted, the MySQL
  collation removed, the migration regenerated. `DailyQuota` uses `ON CONFLICT … RETURNING`, and
  the `EmailOutbox` catch is narrowed to `ux_msg_dedupe`.
- Tests: the fixture is `postgres:18.4`. `ApiFactory` now uses Program's own DB registration.
  The constraint tests assert constraint names. 11 new tests in `DatabaseConnectionTests`:
  migrations vs model, UTC round-trip, session zone and pool, bad connection string at startup,
  `/readyz` 200 and 503, and outbox dedupe vs other violations. A mutation check confirmed they
  fail without the fixes.
- Testcontainers bumped to 4.15.0, forced by an `SSH.NET` advisory (see troubleshooting). Deleted
  `docs/ef-versions.md`, updated `README.md` and `docs/schema.md`.

**Decisions:** `timestamptz(3)` for instants, drop `unsigned`, pool cap of 20, and the outbox
catch matched by name. All are in `decisions.md`. `DailyQuota` stays raw SQL, because EF has no
upsert. The owner agreed.

**Open:**
- **Committed and pushed at the end of the session as PR #1**
  (https://github.com/jftiv/secret-santa-v2/pull/1): `99c6e1f` is the deploy work, `3fcca64`
  the Npgsql swap. It's awaiting owner review. The repo was then **switched from public to private** at the owner's request, so the deploy
  details can be reviewed before they're exposed. The branch had been public for a few minutes.
  It had no forks, stars or watchers. History, for context: the branch was cut from a dirty `main`, so the older untracked deploy
  work (`deploy/`, `Dockerfile`, workflows, `docs/deploy.md`, `fly.toml`) and the modified
  `ci.yml` came along. This session **edited some of those untracked files**: both configmaps
  (removed `Database__ServerVersion`), the `deploy-k8s.yml` smoke-check text,
  `deploy/base/deployment.yaml` (a comment) and `docs/deploy.md`. Separating the two sets of
  changes into commits is the next step.
- Phase 4 gate (migrate Job on dev, `/readyz`, an end-to-end game) not run. Phases 5–6 untouched.
- ~~Comments elsewhere still mention Fly.~~ Cleaned up later the same day (next bullet).
- **Later the same day, at the owner's request: Fly removed.** Deleted `fly.toml` and
  `.github/workflows/deploy-api.yml` (both untracked, so they're gone for good), and removed
  `fly.toml` from `.dockerignore`. `docs/deploy.md` was rewritten around the current setup: a
  "The database" section replaces the allowlist section, which is kept as a short history
  paragraph. The first-deploy order was fixed, and `VITE_API_BASE_URL` now points at
  `api.secret-santa.net`. Fly-era comments were reworded in `Dockerfile`, `deploy/migrate/job.yaml`,
  `README.md`, `TokensOptions`, `EmailOutbox`, `EmailOutboxWorker`, `EmailMessage`, `IpThrottle`,
  `client/.env.example` and `client/src/api/client.ts`. The early "keep Fly until the first k3s
  deploy succeeds" plan was dropped, because the Npgsql build can't reach the in-cluster
  database from Fly anyway. **Not touched:** the suspended `secret-santa-be` Fly app and any
  `FLY_API_TOKEN` GitHub secret. Delete those by hand if wanted.
- Prettier isn't configured for `client/`. `--check` fails on unmodified files over quote style,
  so don't treat it as a gate.
- The app's `EmailNormalizer` uses .NET `Trim()`, which trims all Unicode whitespace, but the
  stored columns use SQL `trim()`, which trims spaces only. This predates M6.5 and matters only
  if validation ever lets other whitespace through.
- `Suppression` has no writer in the app yet. Whoever adds one must normalize the address,
  because collation no longer makes the match case-insensitive.

## 2026-09-27 — M6.5 platform half done: Postgres live, restore proven on dev

**Changed:** No code in this repo. All the work landed in `homelab-infra` (PRs #3 and #4, all
four layers applied). See `docs/homelab-infra/sessions.md`. Here, `m6.5-postgres.md` gained a
status table and as-built corrections to Phase 1, and `overview.md` gained the M6.5 status.

**Where M6.5 stands:** Phases 0 and 1 are done. Postgres 18.4 is healthy in dev and prod under
CloudNativePG, and WAL archiving to R2 works. The Phase 0 gate was run late, against the real dev
Cluster, and passed: a Cluster rebuilt from R2 alone had a row from before the base backup and
one that existed only in archived WAL.

**Decisions:** None in this repo. The platform decisions, three of which depart from the M6.5
plan, are in `docs/homelab-infra/decisions.md`.

**Open:**
- **Phase 2 is next and unblocked.** It still needs two decisions first: `timestamptz` vs
  `timestamp`, and whether to widen `unsigned` columns or keep their ranges with CHECKs.
- **The app can't be deployed until Phase 2 lands.** `secret-santa-config` now holds a Postgres
  connection string, which the MySQL build can't use.
- **Still unread:** the actual value of `ConnectionStrings__Default` in the cluster. Terraform
  writes it; reading it back was declined as a production-secret read.
- Deploy work from 07-26 and 08-30 (`deploy/`, `Dockerfile`, both workflows, `docs/deploy.md`)
  is **still uncommitted**. Phase 2 touches nearby files, so commit that work first.
- Unchanged from before: the Brevo 401/403 retry classification, and `GamesPerIpPerHour` set
  above `GamesPerIpPerDay`.

## 2026-09-04 — M6.5 planned: Postgres in-cluster replaces Hostinger MySQL

**Changed:** No code. Planning and documentation only — `decisions.md` (new entry, plus the
2026-08-30 WAN-stability paragraph marked superseded), `overview.md` (stack row, EF-pin note,
roadmap, and a stale "the cluster is still unbuilt" claim corrected), and a new working plan at
`m6.5-postgres.md`.

**Decisions:** Run PostgreSQL in the cluster under CloudNativePG with WAL archiving to R2, and
drop Hostinger MySQL entirely, as **M6.5 before the M7 deploy**. Full reasoning in `decisions.md`.
The short version: the API already serves from `homelab`, so keeping the database off-box bought
no availability while adding an independent failure path, a shared-host exposure that blocked
opening the allowlist, and an EF 9 pin. Self-hosted MySQL was rejected but **kept as the explicit
fallback** — it is zero application code change and captures most of the value if the calendar
tightens.

**How the cost was sized** (worth not re-deriving): 251 `HasColumnType` annotations across 6
configuration files, 3 stored computed columns, one raw `ON DUPLICATE KEY UPDATE` in `DailyQuota`,
one `MySqlException` number check in `EmailOutbox`, one migration to regenerate, ~10 test files on
the Testcontainers fixture. The only non-mechanical part is that Postgres has no `unsigned`.

**Why now rather than after deploy:** M7 has not been crossed, so no environment holds data. The
migration is regenerated, not converted. This is the cheapest the change will ever be.

**Open:**
- Phase 0 gates the whole plan: CNPG backing up to R2 and **restoring from it** is unproven, and
  R2 has known quirks with multipart uploads and checksums. Fallbacks are listed in the plan.
- Three decisions deferred into the phases: Postgres major version, `timestamptz` vs `timestamp`,
  and whether `unsigned` ranges get widened or preserved with CHECK constraints.
- The WAN static-IP thread (item 1 of the homelab list) is **obsoleted rather than solved** by
  this decision, but stays open until Phase 6 actually removes the allowlist entry. Second WAN
  reading taken today: `<wan-ip>`, unchanged from the earlier one.
- Monitoring narrows: the WAN probe becomes pointless, but Cloudflare Tunnel health notifications
  and a dead-man's-switch ping are still worth having. The alerting path must not run through
  Brevo — its 90-day key expiry is one of the things you want alerted about.

## 2026-09-03 — Secrets moved to Terraform; Brevo key-expiry defect found

**Changed:**
- Application secrets are now a Terraform-managed `secret-santa-config` Secret, replacing the
  Sealed Secrets design. `deploy/` overlays and `docs/deploy.md` updated; no secret material in
  this repo either way.
- Documented the **Brevo 90-day inactivity expiry** and its interaction with retry
  classification in `architecture.md` and `troubleshooting.md`.

**Decisions:** Sealed Secrets dropped — it protected the unrotatable participant key from state
by introducing a sealing key whose loss is equally unrecoverable, at the cost of a controller
per vcluster. Owner accepted secrets living in HCP state instead. Logged in
`docs/homelab-infra/decisions.md`.

**Defect found, not yet fixed — email is destroyed rather than delayed when the API key lapses:**
`HttpEmailSender.IsTransient` is `429 || >= 500`, so a **401 from an expired key classifies as
permanent**, and `EmailOutboxWorker` finishes permanent failures as `EmailMessageStatus.Failed`,
which is terminal. Restoring the key does not resend them. Brevo expires keys after 90 days of
inactivity and this app is idle eleven months a year, so the lapse is expected and lands on the
first real users of the season.

The classification's premise — "every other 4xx is the provider saying the request is wrong" —
holds for 400 and 422 but **not** for 401/403, which describe the credential rather than the
message. The same bytes succeed an hour later with a valid key.

**Proposed fix:** treat 401 and 403 as transient, so the outbox backoff holds the mail while the
key is rotated. Needs a test asserting 401 is retryable and 400 is not.

**Open:**
- The 401/403 classification fix is unimplemented.
- No alerting on repeated permanent failures. `EmailOutboxWorker` already logs `LogError` on
  permanent failure specifically so it can be alerted on; nothing consumes that yet (M11).
- Pre-season checklist added to `homelab-infra/docs/runbook.md`; rotating the Brevo key is now
  step one.

## 2026-08-30 — M7 unblocked: hosting resolved, k8s deploy path built

**Changed:**
- `deploy/` created: Kustomize base (Deployment, Service) plus `dev` and `prod` overlays, a
  shared `config/` base per environment, and a **separate `migrate/` kustomization** so the
  migration Job can be applied and waited on before the Deployment rolls. All four
  kustomizations build clean.
- `.github/workflows/ci.yml` — the `image` job now pushes to **GHCR** on `main` and publishes
  the digest as a job output. It previously built with `push: false` and pushed nowhere, because
  Fly built its own image remotely; the cluster needs something to pull from.
- `.github/workflows/deploy-k8s.yml` — new. Joins the tailnet (the cluster has no public API
  endpoint), pins the image by digest, applies the migrate Job and waits, then rolls the
  Deployment, then curls `/readyz` at the real public entry point.
- The platform itself lives in a new repo, `~/source/homelab-infra`. See `docs/homelab-infra/`.

**Decisions:** One logged here — the API runs on self-hosted k3s and the MySQL allowlist stays
closed, resolving the month-old OPEN entry. Six more platform-level decisions are in
`docs/homelab-infra/decisions.md`.

**Two things the manifests had to get right that were not obvious:**
- The migrate Job needs **every** secret, not just the connection string. `--migrate` runs the
  app's full startup validation before reaching the migrate branch, so a missing `Email__ApiKey`
  fails the Job and reads as a database fault.
- Liveness must stay on `/healthz` and readiness on `/readyz`. Pointing the restart policy at
  the database check would make a Hostinger blip kill and restart pods during an outage that
  cannot be fixed from this side — the same reasoning `architecture.md` records for Fly.

**Open:**
- **Nothing is deployed and nothing is applied.** The manifests are validated by `kubectl
  kustomize` and the workflows parse; none of it has run against a cluster, because the cluster
  does not exist yet. All of Phase 0 in `homelab-infra/docs/bootstrap.md` is outstanding.
- **The Hostinger allowlist assumption is unverified** — see the decision entry. This is the one
  finding that could send this back to the DigitalOcean option.
- `deploy/overlays/*/sealed-secret.yaml` do not exist yet; both kustomizations reference them in
  a commented-out line. The app cannot start without them — it hard-throws on missing config.
- The digest placeholders in the overlays are all-zero and must be replaced by CI.
- `fly.toml` and `.github/workflows/deploy-api.yml` are now dead. Left in place rather than
  deleted, pending a first successful k3s deploy — deleting the fallback before the replacement
  works would be premature.
- Still unresolved from before: where the SPA is served (Hostinger vs the cluster behind the
  same tunnel), the scoped `secret_santa` MySQL user, and `GamesPerIpPerHour` sitting above
  `GamesPerIpPerDay`.

## 2026-07-26 — M7 (part 1): deploy artifacts built, not yet deployed

**Changed:**
- `Dockerfile` + `.dockerignore` — multi-stage, Release, `aspnet:10.0-noble-chiseled-extra`,
  UID 1654, 177 MB. Built and **run** locally: `/healthz` 200, `/readyz` 503 with no database
  (correct), OpenAPI 404 under Production.
- `fly.toml` — reuses the existing suspended `secret-santa-be` app in `dfw`. Scale to zero,
  liveness check on `/healthz` (not `/readyz`, per the existing design note).
- `.github/workflows/deploy-api.yml` — manual dispatch only, requires typing the app name.
- CI gained an **image build job**, and `docs/deploy.md` was written from nothing.

**Two bugs the container build caught that nothing else would have:**
- I excluded `.editorconfig` from the Docker context. It carries the analyzer suppressions for
  EF's generated migrations, so the warnings-as-errors build failed on scaffolder-written code
  while `dotnet build` stayed green. CI now builds the image so this cannot recur. (My first
  read — "CI only builds Debug so Release was never compiled" — was wrong; Release builds fine
  locally. The missing file was the whole cause.)
- Plain chiseled has no ICU. The draw email formats the budget as `en-US`, which under invariant
  globalization renders `¤25` instead of `$25` — a broken-looking email rather than a crash.
  Moved to `-extra`.

**Nothing has been deployed.** No secrets set, no `flyctl deploy` run.

**Blocked on an owner decision: where the API runs.** Paused 2026-07-26 with the owner
deciding between two options. Researched this session:

- Free tiers were surveyed properly. **Azure Container Apps has the best free grant**
  (180k vCPU-s / 2M requests per month, perpetual, scale-to-zero by default) and is the natural
  home for .NET. **Google Cloud Run** is comparable on compute.
- **The pattern that decides it:** serverless compute is ~free everywhere, but a *static
  outbound IP* costs ~$32/mo on both Azure (workload profiles + NAT Gateway) and GCP (Cloud
  NAT). Fly is the only one selling it à la carte, at $3.60/mo. That is why Fly keeps winning
  despite having no free tier.
- Rejected: rotating AWS accounts annually. The free tier became credit-based on 2025-07-15
  ($100–200, expiring in **6 months**), it violates the customer agreement, and rebuilding
  infrastructure twice a year would wreck email sender reputation on a domain whose entire
  job is delivering mail.
- Rejected: Oracle Always Free. Free VM with a static IP solves both problems, but Oracle
  **reclaims idle instances** and this app is idle ten months a year — the failure mode is the
  server vanishing during the dead season and being gone in December.

**The two live options:**
1. **Fly** (owner believes their org is grandfathered onto a free plan — *unverified*) plus
   opening the Hostinger allowlist to any host, with credentials unique to this app.
2. **A DigitalOcean droplet.** Lowest tier costs marginally more than Fly's egress IP alone,
   comes with a static IP, keeps the allowlist intact, and has no cold start.

**Material fact surfaced at the pause: that MySQL server also holds other apps' data.** The
allowlist is therefore protecting more than this project — see the risk note in `decisions.md`.

**Also unanswered:** how `client/dist/` reaches Hostinger (FTP, SFTP, or their git integration).
The client deploy is manual until that is known.

## 2026-07-26 — M6: the client SPA

**Changed:**
- Replaced the Vite starter with the real app. Five routes — create, created, verify, draw,
  recovery — plus a not-found. `src/api/` (typed fetch + `ApiError`), `src/lib/`
  (validation, formatting, captcha config), `src/styles/` (tokens, base, app).
- Design tokens implement `design.md`: green-and-mint kept, red demoted from form-field fill to
  accent, real `<label>`s instead of white placeholders, fluid type, no particle canvas.
- `strict` and `noUncheckedIndexedAccess` added to `tsconfig.app.json` — the scaffold had
  neither, and `preferences/stack.md` calls for strict TS.
- 52 client tests. Build clean, oxlint clean, `npm audit` clean.

**Two fixes that were not cosmetic:**
- `Cors:AllowedOrigins` was unset in Development, so the SPA could not call the API locally at
  all. Added `http://localhost:5173`.
- `public/.htaccess` rewrites unknown paths to `index.html`. Without it every participant —
  who lands on `/draw/<token>` from an email and never sees the homepage — gets an Apache 404.

**Dependencies:** `react-router-dom` removed in favour of `react-router@8` to clear a high
advisory (see decisions). `@testing-library/user-event` added — the standard companion to
Testing Library, and the only way to drive focus and typing the way a real user does.

**Follow-up the same session, both from owner review:**
- **The organizer now appears as row 1 of the roster**, read-only and tagged "You". The owner
  read the form as "you plus three others" and thought the host made the minimum four. It never
  did — the server matches the creator into the list by email — but the form invited that
  reading. The roster is now derived rather than stored. See decisions.
- **The old header art is back**, pulled out of `secret-santa-web` before it gets deleted and
  resized 1920×1080 → 1280×720 (580 kB → 80 kB) as `client/src/assets/masthead.jpg`.
- 58 client tests.

**Open:**
- **No visual confirmation.** Everything here is verified by tests and a compiler; nothing has
  been looked at in a browser. The masthead especially — the crop and scrim were chosen blind.
- Turnstile is wired but unexercised — no site key has been configured yet, so the widget path
  has never actually rendered.
- The admin token is shown as a bare code, not a link. There is no management endpoint behind
  it yet; resend and cancel are later milestones.
- Quicksand is referenced but not self-hosted; it currently falls back to the system stack. The
  font files need adding, deliberately not via a Google Fonts `@import`.
- The masthead is JPEG, not WebP — no encoder available locally. See `design.md`.

## 2026-07-26 — M5 closed: rate limiting enforced

**Changed:**
- `BurstQuota` (in-process, hourly, singleton) and `DailyQuota` (durable, `ip_throttle`), wired
  into `GameService.CreateAsync` in cheapest-first order: burst → validation → daily → captcha.
- `ResultStatus.RateLimited` → 429 through the existing `MapFailure` seam. One new status, no
  new translation point.
- 394 tests passing (228 Core, 166 Api), 0 warnings, green twice in a row.

**The bug worth remembering:** the durable limiter was first written as increment-then-`SELECT`.
That reads correctly for sequential traffic and collapses under exactly the burst it exists to
stop — 60 concurrent requests against a limit of 10 admitted **2**, because every caller read a
count the others had already inflated. Now one atomic `LAST_INSERT_ID(counter + 1)` read back on
the same connection. A concurrency test caught it; reading the code did not.

**Test-harness note:** `TestServer` never sets `RemoteIpAddress`, so every request in the suite
hashes to one throttle subject and shares a counter that accumulates across the whole run. The
caps are raised to 1,000,000 in `ApiFactory`; `RateLimitTests` seeds a counter directly and
deletes it in a `finally`, because leaving it high would 429 every later creation test.

**Open:**
- **`GamesPerIpPerHour = 10` vs `GamesPerIpPerDay = 5` — the burst guard can never fire first.**
  Left at the owner-confirmed value and documented in `LimitsOptions`. It wants to be ~3, or the
  in-process limiter should come out. Owner decision.
- The three resend/recovery caps still have no call sites, because those endpoints do not exist.
  `DailyQuota` takes a generic 32-byte subject so they can key on a hashed game or participant
  id when they land — at which point `ip_throttle.ip_hash` should be renamed `subject_hash`.
- No `Retry-After` header on the 429. `Result<T>` is transport-neutral and carrying a duration
  through it was more plumbing than the value justified today.

## 2026-07-26 — Design reference captured from the old repo

**Changed:** Added `design.md` — palette, type, layout, and measured contrast extracted from
`secret-santa-web`'s CSS. Done now rather than at M6 **because the old repo is scheduled for
deletion**; this is the only surviving record of the design.

**Direction from the owner:** keep the old identity, fix the forms. The measurement backs the
instinct with a specific number — white on the red `#F53948` input fill is 3.8:1, which fails
WCAG AA for normal text. The red reads loud *and* under-contrasts; both point at taking it off
the form fields.

**Open:** `landing-christmas-1920x1080.jpg` is the only binary asset in the old client and cannot
be regenerated. Copy it out before the repo is deleted if it is wanted.

## 2026-07-26 — M5: outbox, worker, templates, verification fanout

**Changed:**
- `EmailOutbox` (enqueue, dedupe-key idempotency), `EmailRenderer` (renders from rows at send
  time), `EmailOutboxWorker` (claim-one-at-a-time, 1/5/25/125-minute backoff, 5 attempts),
  `SuppressionCheckingEmailSender` (decorator, applied in DI so no send path can skip it).
- `EmailTemplates` — verify, draw, recovery-forward. Hand-rendered, HTML-escaped.
- `VerificationService` + `POST /api/v1/verify/{token}` — the gate that releases the fanout.
  `GameService` now enqueues the creator's verify email inside the creation transaction.
- **Renamed `ParticipantTokenDeriver` → `LinkTokenDeriver`** and added `DeriveForGame`; the
  verify token is now derived too. See the decision entry — the old rule was the wrong cut and
  was hiding the same bug that blocked M5.
- 374 tests passing, 0 warnings.

**Decisions:** Two logged — bodies rendered at send time rather than stored, and the
derive/issue line being about delivery rather than token scope.

**Answered this session:** Cloudflare DNS is configured for both sender identities; replies
forward to the owner's personal inbox for now. Brevo account exists; tokens to be added to
secrets later.

**Old-repo credentials audited and closed.** The long-standing "rotate three leaked
credentials" task was miscast — the SMTP mailbox no longer exists, the reCAPTCHA secret is
inert, and production MySQL was never exposed (it used env vars). Decision logged: delete
`secret-santa-web` once v2 ships rather than rewrite history. **The one live item is a
password-reuse check, and it is not gated on that deletion.**

**Open:**
- **Rate-limit enforcement is still unbuilt.** The caps sit in `LimitsOptions` and nothing
  reads them. This is the largest remaining gap in M5 and the one with a security consequence.
- Per-participant resend, `/recovery/forward`, and marketing opt-in are not built. The
  `recovery_forward` template exists but `EmailRenderer` has no case for it, so enqueueing one
  today would fail as a render error.
- Draw emails are queued in one loop inside the request. Fine at 100 participants; revisit if
  the cap ever rises.
- CAN-SPAM postal address still unresolved — blocks the marketing stream at M10, not M5.
- ~~**M7 risk, surfaced 2026-07-26:** Fly machines have no stable outbound IP.~~
  **Corrected 2026-07-26 during M7** — that was out of date. Fly now sells **app-scoped static
  egress IPs** (`fly ips allocate-egress`, $3.60/mo per IPv4, billing from 2026-01-01), which do
  cover the runtime machines.
  **The real problem is narrower and still real:** egress IPs do **not** cover `release_command`
  machines, so `--migrate` egresses from an address the allowlist will not know. Expected
  failure mode is a deploy that aborts at the migrate step while the app itself would have been
  fine. Options written up in the repo's `docs/deploy.md`. Still do not "fix" it by opening the
  allowlist.

## 2026-07-26 — M5 begun: participant token delivery unblocked, Turnstile wired

**Changed:**
- `Core/Security/ParticipantTokenDeriver.cs` — HMAC-derives view and unsubscribe tokens from
  `(gamePublicId, position)`, resolving the blocker that made participant email impossible.
  `GameService` now derives instead of discarding; storage is unchanged (still hash-only),
  which is why all 59 prior Api tests passed untouched.
- `TurnstileCaptchaVerifier` — fails closed on every non-success path. Replaces the blanket
  "throw in Production" placeholder with a real registration; the stub now only appears outside
  Production and only when no secret is configured.
- `LimitsOptions` gained the abuse caps as owner-confirmed defaults: 5 games/day/IP durable,
  10/hr in-process, resend 3/day/participant and 20/day/game, recovery forward 3/day/game.
  **Nothing enforces these yet** — they are configuration, not behavior.
- Fixed a stale README (still described `Domain`/`Infrastructure` and minimal APIs) and added a
  configuration table covering the two required secrets and the new key.
- 298 tests passing, 0 warnings.

- `Api/Email/` — `IEmailSender` with **both** `BrevoEmailSender` and `SendGridEmailSender`
  behind it, sharing an `HttpEmailSender` base that owns retry classification. Owner wants the
  choice open: Brevo for free-tier headroom now, SendGrid as the likely paid path later since
  it carries Twilio access. `LoggingEmailSender` covers local dev, refused in Production.
- 344 tests passing.

**Decisions:** Three logged — HMAC-derived participant tokens, Turnstile failing closed, and
two email providers behind one interface.

**Answered this session:** `secret-santa.net` is still owned, so the real sender identities are
now the defaults. No Brevo account exists yet but one can be created.

**Open:**
- Rate-limit **enforcement**, the email outbox and worker, verification fanout, per-participant
  resend, and `/recovery/forward` are all still unbuilt. The senders have no caller yet.
- DNS not yet configured: SPF, DKIM and DMARC for both `secret-santa.net` and the marketing
  subdomain. Nothing will deliver reliably until that is done.

## 2026-07-26 — Structural refactor: Core/Data/Api, services, controllers, OpenAPI

**Changed:**
- Renamed `Domain`→`Core` and `Infrastructure`→`Data`; moved entities into `Data` so they sit
  with the `DbContext` and migrations. `Core` now has **zero package references**.
- Added `Core/Results/Result.cs`; extracted `GameService`, `DrawService`, `RecoveryService` out
  of the endpoint handlers. Services return `Result<T>` and touch no ASP.NET types.
- Replaced minimal APIs with attribute-routed MVC controllers. `ApiControllerBase.MapFailure`
  is the single `Result`→HTTP translation point; every action is now ~3 lines.
- Moved `IpHasher` to `Core`; extracted the email-shape rule into `Core/Security/EmailAddress.cs`.
- Wired built-in OpenAPI with `[ProducesResponseType]` on every action.
- Added `LayeringTests` (reflection-based: fails if a service references `Microsoft.AspNetCore.*`)
  and `OpenApiTests`. 266 tests passing; all 260 pre-existing tests passed unmodified through
  the new stack, which is the evidence the refactor preserved behavior.

**Decisions:** Two logged — the Core/Data/Api layout (pushing back on the originally proposed
`Data`+`Config`), and `Result<T>` over HTTP types from services.

**Open:**
- NuGet audit blocked `Microsoft.AspNetCore.OpenApi` because it pins `Microsoft.OpenApi` 2.0.0,
  which carries a high-severity advisory (GHSA-v5pm-xwqc-g5wc). Worked around with an explicit
  `Microsoft.OpenApi` 2.11.0 reference. **Remove that pin once the ASP.NET package ships a
  patched transitive dependency.**
- The participant-token-delivery question from M4 is still unanswered and still blocks M5.

## 2026-07-25 — M4: draw lookup, recovery reveal, CSV export

**Changed:**
- `GET /api/v1/draw/{viewToken}` — one participant's own receiver, no addresses, no one else's
  pairing. Stamps `draw_viewed_at` once.
- `GET /api/v1/recovery/{recoveryToken}` and `/export.csv` — the organizer's escape hatch.
  Both write an `admin_events` row.
- CSV export guards against spreadsheet formula injection; participant names are free text and
  the file exists to be opened in Excel.
- `WithTokenInUrlProtection()` endpoint filter adds `Referrer-Policy: no-referrer`,
  `X-Robots-Tag: noindex, nofollow` and `Cache-Control: no-store` to token-bearing routes.
- Replaced `ServerVersion.AutoDetect` with a configured version — AutoDetect opens a database
  connection during DI setup, so a briefly unreachable MySQL would stop the app starting.
- 260 tests passing.

**Decisions:** Logged an **open** question blocking M5 — participant token plaintext is
discarded at creation, so nothing can put a working link in a participant email. See
`decisions.md`.

**Open:**
- Api.Tests takes ~14s cold, ~2s warm. Each test class alone is ~1s; the combining cost was not
  identified. Investigated and set aside as acceptable rather than solved.
- Test parallelization is disabled for determinism (shared container, count-based assertions),
  not for speed — it made no measurable difference to runtime.

## 2026-07-25 — Repo created; milestones M0–M3 built

**Changed:**
- Created `~/source/secret-santa-v2` from nothing: solution, 3 .NET projects + 2 test projects,
  Vite React TS client, CI workflow. `git init` done, **nothing committed yet**.
- M1: Sattolo derangement in `SecretSanta.Domain/Assignments/`, replacing the old app's
  infinite-looping shuffle. 8 test cases including a bounded-work test asserting the RNG is
  called exactly `n-1` times.
- M2: 10-table normalized schema + `InitialCreate` migration, replacing the old single `games`
  table with two JSON blobs. 8 Testcontainers tests asserting the constraints reject bad data.
- M3: `POST /api/v1/games` — one server-authoritative transaction replacing the old app's
  `/submitform` + `/confirmation` pair. 10 endpoint tests.
- 232 tests passing. Zero build warnings.

**Decisions:** Six recorded in `decisions.md`. The load-bearing ones: separate admin and
recovery tokens (owner's correction to the original design), EF Core 9 + Pomelo on a net10.0
target, Sattolo over Fisher-Yates-with-rejection, and Testcontainers now with Aspire deferred.

**Open:**
- **Nothing is committed.** Working tree is entirely untracked; `git init` ran but no commit was
  made, per spine's "never commit unless asked."
- **Rotate the old repo's leaked credentials.** ~~Flagged at planning.~~ **Superseded
  2026-07-26** — audited and largely a false alarm. See `decisions.md`; the repo gets deleted
  and the only live concern is password reuse.
- Next milestone is M4 (draw lookup, recovery reveal, CSV export). Parity line is M7.
- Deferred to their milestones: real Turnstile verification and `ip_throttle` enforcement (M5 —
  the API currently registers a permissive captcha stub and refuses to start in Production),
  the email outbox and Brevo sender (M5), and the SPA (M6).
- Unanswered questions from planning, none blocking yet: the CAN-SPAM postal address (M10, the
  one place "no new spend" genuinely conflicts with the revenue feature), whether
  `secret-santa.net` is still owned (M5), and current Fly.io billing status (M7).
