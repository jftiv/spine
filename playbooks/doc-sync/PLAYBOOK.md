---
name: doc-sync
description: Update documentation after an implementation session — the target repo's own docs/ and spine's cross-repo docs and session log. Use when a session that changed code in a target repo is wrapping up, when the doc-sync hook fires, or when docs have drifted from reality.
---

# doc-sync

Refresh the docs so the next session, and the next person, starts informed instead of
re-deriving everything.

## Principle

**Document decisions and shape, not diffs.** Git has the diffs. Docs answer what a diff
cannot: why is it built this way, what was rejected, where are the sharp edges, what
breaks if you touch this.

If a fact is already obvious from reading the code, leave it out. Docs that restate the
code rot immediately and teach the reader to distrust the rest of the file.

## Where things go

There are two tiers. Write each fact once, in the tier where it belongs.

| Tier | Location | Holds |
|---|---|---|
| **Repo** | `<target repo>/docs/` | Everything about that one repo: overview, architecture, its own decisions, conventions, troubleshooting, deploy and schema notes, and the rationale kept out of code comments. |
| **Spine** | `spine/docs/` | Anything that spans repos or concepts: how the repos connect, decisions whose reasoning involves more than one repo, cross-repo plans and migrations. Also the per-repo session log. |

**Tie-break:** if explaining it requires knowing about another repo, the reasoning goes
in spine. The repo's docs still state the local fact ("Postgres is provided by the
platform, in-cluster"), so a person reading only that repo is not misled. They just
don't carry the cross-repo argument.

### Repo tier layout

```
docs/README.md           entry point: what this is, stack, layout, how to run, index of the rest
docs/architecture.md     components, data flow, boundaries, sharp edges
docs/decisions.md        this repo's decisions, append-only
docs/conventions.md      patterns specific to this repo
docs/troubleshooting.md  non-obvious failures, by symptom
docs/<topic>.md          deploy.md, schema.md, … when a subject outgrows a section
```

Starting shapes are in `repo-template/` next to this playbook. Create only the files
there is something true to put in. An empty `troubleshooting.md` is noise.

### Spine tier layout

```
docs/landscape.md        every repo, what it is for, and how they depend on each other
docs/decisions.md        cross-repo decisions, append-only
docs/<topic>.md          cross-repo stories: a migration or plan that spans repos
docs/sessions/<repo>.md  session log for one repo
docs/PENDING.md          sessions that ended without documenting (written by a hook)
```

## Procedure

1. **Identify the repo.** `<repo>` is the target repository's directory name.

2. **Determine what actually changed.** Use the target repo's `git status` and
   `git diff` for the session's work, plus what you know from the session itself.
   Decisions made in conversation never appear in a diff.

3. **Update the repo tier** for each area the session touched:

   | File | Update when |
   |---|---|
   | `README.md` | Purpose, stack, layout, or how-to-run changed |
   | `architecture.md` | A component, boundary, or data flow changed |
   | `decisions.md` | A choice was made with a real alternative. **Append, never rewrite.** |
   | `conventions.md` | A repo-specific pattern was established or changed |
   | `troubleshooting.md` | A non-obvious failure was diagnosed |
   | `<topic>.md` | Rationale that was cut from a comment, or an operational procedure |

   If the repo has no `docs/` yet, create it from `repo-template/`. For sections you
   have not verified, write `_Not yet documented._` and move on. An honest gap beats a
   confident guess.

   These files ship with the code, so they change on the working branch like any other
   file and go through the same review. Follow the repo's git rules and do not commit
   unless asked.

4. **Update the spine tier** only if the session crossed a repo boundary: a new
   dependency between repos, a decision that involved another repo, or a change to a
   cross-repo plan. Update `landscape.md` whenever a repo's role or its connections
   change.

5. **Append a session entry** to `docs/sessions/<repo>.md` in spine, newest first. Do
   this every time:

   ```markdown
   ## YYYY-MM-DD — <short title>

   **Changed:** <what shipped, 1–3 bullets>
   **Decisions:** <choices worth remembering, with a link to where each is recorded, or "none">
   **Open:** <known gaps, TODOs, things deliberately deferred>
   ```

6. **Correct what is now wrong,** in both tiers. Drift is the failure mode. If the
   session invalidated an existing statement, fix or delete it. Do not append a
   contradiction and leave both standing.

7. **Report** which doc files you wrote, in each tier, in one or two lines. Do not paste
   their contents back.

## Writing for two readers

Every doc is read by a person skimming and by an agent searching. Write for both:

- One topic per heading, with headings specific enough to link to and grep for.
- Lead with the rule or fact, then the reason.
- Name files, config keys, commands and types exactly as they appear in the code, so a
  search finds them.
- Each section stands on its own. No "as mentioned above".
- Link across tiers only from spine to a repo, never from a repo to spine. A person
  reading the repo may not have spine.

## Writing a decision entry

Only for choices with a real alternative. Format:

```markdown
### <Decision> — YYYY-MM-DD
**Context:** what forced a choice
**Chose:** what was picked
**Because:** the reason, including the constraint that mattered
**Rejected:** the alternative and why not
```

Decisions are append-only history. When one is superseded, mark the old entry
`_Superseded by <new decision> on YYYY-MM-DD_` rather than deleting it. Knowing that
something was reversed is itself useful.

## Scope limits

- Do not copy source code, secrets, credentials, or customer data into either tier.
- Do not document a repo you did not work in this session.
- Keep each file readable in one sitting. If a file is growing past a couple of pages,
  split it by subsystem or topic.
