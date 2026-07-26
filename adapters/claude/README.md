# Claude Code adapter

Translates spine's neutral definitions into what Claude Code expects.

## Mapping

| spine | Claude Code |
|---|---|
| `agents/<name>.md` | `.claude/agents/<name>.md` — subagent, invoked via the Task tool |
| `playbooks/<name>/PLAYBOOK.md` | `.claude/skills/<name>/SKILL.md` — skill, invoked via `/<name>` or matched by description |
| `adapters/claude/hooks/*.py` | wired up in `.claude/settings.json` |
| `preferences/*.md`, `docs/` | read by `CLAUDE.md` instructions, no translation needed |

The formats happen to be close today — agent frontmatter (`name`, `description`,
`model`) is the same shape in both, so the agent step is a validated copy. That is the
adapter's job either way: if a future harness wants JSON, or a different frontmatter
key, or a single concatenated prompt, it changes here and nowhere else.

## Running it

```bash
./adapters/claude/sync.sh
```

Rebuilds `.claude/agents/` and `.claude/skills/` from scratch. Validates that every
agent and playbook has frontmatter whose `name` matches its filename and a non-empty
`description` — Claude Code silently ignores files that fail either, which is a
miserable thing to debug.

## Hooks

**`doc_sync_reminder.py`** — `Stop`. Once per session, if the transcript shows edits to
files outside spine and nothing under `docs/` has been written, it blocks the stop and
tells the model to run the `doc-sync` skill. It respects `stop_hook_active` and a
per-session marker in `.claude/.state/`, so it cannot loop.

**`session_end_pending.py`** — `SessionEnd`. Same detection, but `SessionEnd` cannot
send anything back to the model, so it appends a line to `docs/PENDING.md` instead. That
file is the catch-all for sessions that ended without documenting.

Both exit 0 on any internal error. A hook that breaks a session is worse than a hook
that misses one.

## Writing another adapter

Add `adapters/<harness>/` with its own `sync.sh`. Read from `agents/` and `playbooks/`;
write wherever that harness looks. Do not edit `agents/` or `playbooks/` to suit a
harness — if content needs reshaping, reshape it in the adapter.
