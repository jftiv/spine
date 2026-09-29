# spine

The control repo for AI-driven development. Open Claude Code here, always. Point it at a
target repository when you want code changes.

Nothing in `spine` builds product code. It holds the *definitions* — agents, playbooks,
preferences — and the documentation that ties the target repos together. Each repo's own
documentation lives in that repo.

## Layout

```
agents/            Harness-neutral agent definitions (one file per role)
playbooks/         Harness-neutral procedures. Adapters turn these into skills.
adapters/          Per-harness translation. adapters/claude/ is the live one.
  claude/sync.sh     agents/ + playbooks/  ->  .claude/agents/ + .claude/skills/
  claude/hooks/      Hook scripts wired up in .claude/settings.json
preferences/       Stack defaults, conventions, and review standards agents read
docs/              Cross-repo docs and per-repo session logs. Repo docs live in each repo.
```

## Setup

`.claude/agents/` and `.claude/skills/` are **generated and not committed** — they are a
build output, and the source of truth is `agents/` and `playbooks/`. A fresh clone has
neither, so Claude Code will start with no agents and no skills until you build them:

```bash
git clone <spine> ~/source/spine
cd ~/source/spine
./adapters/claude/sync.sh     # -> .claude/agents/, .claude/skills/
```

Requires `bash`, `git`, and `python3` (the hooks). Verify:

```bash
ls .claude/agents .claude/skills
```

You should see one file per agent and one directory per playbook. Then start a session:

```bash
claude
```

`/agents` and `/skills` inside the session will list what got picked up. If an agent is
missing there but present on disk, its frontmatter is malformed — re-run `sync.sh`, which
validates and reports the offending file.

## Daily use

**Re-run `./adapters/claude/sync.sh` after editing anything in `agents/` or
`playbooks/`**, and restart the session so Claude Code re-reads them. This is the one
step that is easy to forget; if a change to an agent seems to have had no effect, this is
why.

In-session: *"Work in `~/source/acme-api`. Add rate limiting to the public
endpoints."* Claude reads `acme-api/docs/` and spine's cross-repo docs for context, delegates to the
relevant agents, edits the target repo, and on session end the doc-sync hook has it update
the repo's docs and append to `docs/sessions/acme-api.md`.

## Design rules

1. **Agents and playbooks never mention Claude Code.** They describe *what* to do. The
   adapter layer owns *how* a given harness invokes it. Switching harnesses means writing
   one new adapter, not rewriting content.
2. **`.claude/agents/` and `.claude/skills/` are generated and gitignored.** Edit
   `agents/` and `playbooks/`; run `sync.sh`. Never hand-edit the generated trees — the
   next sync deletes them. `.claude/settings.json` is *not* generated; it is hand-written
   and committed.
3. **Docs are the memory, and they live where their subject lives.** If a session learned
   something durable about one repo, it goes in that repo's `docs/`. If it involves several
   repos, it goes in spine's `docs/`. Never only in a chat log.
