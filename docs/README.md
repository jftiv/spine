# docs

spine's docs cover what **spans** repositories. Documentation for a single repo lives in
that repo's own `docs/`, next to its code.

```
landscape.md        every repo, what it is for, and how they depend on each other
decisions.md        decisions whose reasoning involves more than one repo, append-only
<topic>.md          cross-repo stories: a migration or plan that touches several repos
sessions/<repo>.md  session log for one repo, newest first
PENDING.md          sessions that ended without documenting (written by a hook)
```

All of it is written and maintained by sessions, per `playbooks/doc-sync/PLAYBOOK.md`.
The starting shape for a repo's own docs is `playbooks/doc-sync/repo-template/`.
