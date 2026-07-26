# Operating instructions

This is **spine** — a control repo. Sessions started here almost never change code *here*.
They change code in a **target repository** somewhere else on disk.

## Session start

1. Identify the target repo. The user names it ("work in `~/source/acme-api`") or you ask.
   If the request is genuinely about spine itself (adding an agent, editing a playbook),
   there is no target repo — say so and proceed.
2. Read `docs/<repo>/` if it exists. `docs/<repo>/overview.md` is the fastest way to get
   oriented; `decisions.md` tells you what has already been settled and why.
   If it does not exist, this is a first session for that repo — you will create it at
   the end.
3. Read `preferences/stack.md` and `preferences/conventions.md`. These are the user's
   defaults and they override an agent's generic advice.
4. Work in the target repo's own directory. Do not copy target code into spine.

## Delegation

`agents/` defines specialist roles. Use them the way you'd use a colleague: hand off work
that is squarely in one lane and where you want depth, not for trivia you can answer
yourself. A one-line CSS fix does not need the frontend agent.

| Role | Lane |
|---|---|
| `frontend` | TypeScript, React, Vite, component and state design |
| `backend` | Go and C# services, APIs, jobs |
| `database` | Schema, migrations, query performance (Postgres / MySQL) |
| `testing` | Unit tests and Playwright visual regression |
| `telemetry` | Logs, metrics, traces, SLOs |
| `security` | Authn/z, secrets, dependency and input-handling review |
| `devops` | CI, build, containers, deploy |

## Documentation duty

At the end of any session that changed code in a target repo, update `docs/<repo>/`.
The `SessionEnd` hook will remind you; do it whether or not it fires. See
`playbooks/doc-sync/PLAYBOOK.md` for exactly what to write.

Rule of thumb: **document decisions and shape, not diffs.** Git already has the diffs.
`docs/` exists so the *next* session does not have to re-derive why the code is the way
it is.

## Editing spine itself

- Agents live in `agents/*.md`. Playbooks live in `playbooks/<name>/PLAYBOOK.md`.
- Both are harness-neutral: no "use the Task tool", no Claude-specific tool names.
- After editing either, run `./adapters/claude/sync.sh` so `.claude/` picks it up. The
  session must restart before the change takes effect — say so rather than implying the
  edit is already live.
- `.claude/agents/` and `.claude/skills/` are generated and gitignored. Do not edit them
  directly; the next sync deletes whatever is there. If they are missing entirely (fresh
  clone), run `sync.sh`.
