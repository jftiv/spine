# Operating instructions

This is **spine** — a control repo. Sessions started here almost never change code *here*.
They change code in a **target repository** somewhere else on disk.

## Session start

1. Identify the target repo. The user names it ("work in `~/source/acme-api`") or you ask.
   If the request is genuinely about spine itself (adding an agent, editing a playbook),
   there is no target repo — say so and proceed.
2. Read the docs, in this order:
   - The target repo's own `docs/README.md` and whatever it points to. `decisions.md`
     there tells you what has already been settled and why.
   - spine's `docs/landscape.md` for how this repo fits with the others, and
     `docs/decisions.md` for decisions that span repos.
   - The recent entries in spine's `docs/sessions/<repo>.md`, to see where the last
     session left off.

   If the repo has no `docs/`, this is its first documented session. You will create
   it at the end.
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

At the end of any session that changed code in a target repo, update the docs. The
`SessionEnd` hook will remind you; do it whether or not it fires. See
`playbooks/doc-sync/PLAYBOOK.md` for exactly what to write.

There are two tiers:

- **The target repo's `docs/`**: everything about that repo. It ships with the code and
  is written for people and agents alike.
- **spine's `docs/`**: what spans repos (how they connect, cross-repo decisions and
  plans), plus a session log per repo in `docs/sessions/<repo>.md`.

Rule of thumb: **document decisions and shape, not diffs.** Git already has the diffs.
Docs exist so the *next* reader does not have to re-derive why the code is the way it
is. Code comments are not a substitute: see `preferences/conventions.md` → Comments.

## Editing spine itself

- **spine is public.** It doubles as a portfolio of this workflow. Nothing committed here may
  contain secrets or real host addresses; see `playbooks/doc-sync/PLAYBOOK.md` → Scope limits.
- Agents live in `agents/*.md`. Playbooks live in `playbooks/<name>/PLAYBOOK.md`.
- Both are harness-neutral: no "use the Task tool", no Claude-specific tool names.
- After editing either, run `./adapters/claude/sync.sh` so `.claude/` picks it up. The
  session must restart before the change takes effect — say so rather than implying the
  edit is already live.
- `.claude/agents/` and `.claude/skills/` are generated and gitignored. Do not edit them
  directly; the next sync deletes whatever is there. If they are missing entirely (fresh
  clone), run `sync.sh`.
