# docs

spine's docs cover what **spans** repositories. Documentation for a single repo lives in
that repo's own `docs/`, next to its code. The exception is `homelab-infra`, which is the
owner's own platform and treated as part of spine: its docs live in `homelab-infra/` here.

```
landscape.md        every repo, what it is for, and how they depend on each other
decisions.md        decisions whose reasoning involves more than one repo, append-only
<topic>.md          cross-repo stories: a migration or plan that touches several repos
sessions/<repo>.md  session log for one repo, newest first
homelab-infra/      the platform's docs (see above)
PENDING.md          sessions that ended without documenting (written by a hook)
```

**spine is public.** Host addresses, MACs, ports and anything secret appear here only as
placeholders like `<lan-ip>`. The real values live in the private repos they belong to.

All of it is written and maintained by sessions, per `playbooks/doc-sync/PLAYBOOK.md`.
The starting shape for a repo's own docs is `playbooks/doc-sync/repo-template/`.
