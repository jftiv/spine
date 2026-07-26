---
name: doc-sync
description: Update spine's documentation for a target repository after an implementation session. Use when a session that changed code in a target repo is wrapping up, when the doc-sync hook fires, or when docs for a repo have drifted from reality.
---

# doc-sync

Refresh `docs/<repo>/` in spine so the next session starts informed instead of
re-deriving everything.

## Principle

**Document decisions and shape, not diffs.** Git has the diffs. These files exist to
answer the questions a diff cannot: why is it built this way, what was rejected, where
are the sharp edges, what breaks if you touch this.

If a fact is already obvious from reading the code, leave it out. Docs that restate the
code rot immediately and teach the reader to distrust the rest of the file.

## Procedure

1. **Identify the repo.** `<repo>` is the target repository's directory name. Docs live
   at `docs/<repo>/` in spine — never inside the target repo unless the user asks.

2. **Determine what actually changed.** Use the target repo's `git status` and
   `git diff` for the session's work, plus what you know from the session itself
   (decisions made in conversation never appear in a diff).

3. **If `docs/<repo>/` does not exist**, create it from `docs/_template/` and fill in
   what you know. Do not invent content for sections you have not verified — write
   `_Not yet documented._` and move on. An honest gap beats a confident guess.

4. **Update each file that the session's work touched:**

   | File | Update when |
   |---|---|
   | `overview.md` | Purpose, stack, layout, or how-to-run changed |
   | `architecture.md` | A component, boundary, or data flow changed |
   | `decisions.md` | A choice was made with a real alternative — **append, never rewrite** |
   | `conventions.md` | A repo-specific pattern was established or changed |
   | `troubleshooting.md` | A non-obvious failure was diagnosed |
   | `sessions.md` | Always — one entry per session |

5. **Append a session entry** to `sessions.md`, newest first:

   ```markdown
   ## YYYY-MM-DD — <short title>

   **Changed:** <what shipped, 1–3 bullets>
   **Decisions:** <choices worth remembering, or "none">
   **Open:** <known gaps, TODOs, things deliberately deferred>
   ```

6. **Correct what is now wrong.** Drift is the failure mode. If the session invalidated
   an existing statement, fix or delete it — do not append a contradiction and leave both
   standing.

7. **Report** which doc files you wrote, in one or two lines. Do not paste their contents
   back.

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
`_Superseded by <new decision> on YYYY-MM-DD_` rather than deleting it — knowing that
something was reversed is itself useful.

## Scope limits

- Do not copy source code, secrets, credentials, or customer data into `docs/`.
- Do not document a repo you did not work in this session.
- Keep each file readable in one sitting. If `architecture.md` is growing past a couple
  of pages, split by subsystem.
