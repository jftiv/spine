# Working conventions

How work gets done, regardless of stack. Agents read this; it overrides their generic
advice on conflict.

## Changes

- **Smallest change that fully solves the problem.** Not the smallest change that makes
  the symptom go away, and not a rewrite of the surrounding area.
- Match the surrounding code — its naming, its structure — even where you would have
  written it differently. A file with two styles is worse than a file with one style you
  dislike. Comment density is the exception: follow **Comments** below even when the
  file around you is heavier.
- No unrequested refactors mixed into a functional change. Note the opportunity; do it
  separately if asked.
- Do not add a compatibility shim, feature flag, or abstraction layer for a future that
  has not been asked for.

## Comments

**Default to no comment.** Explanation belongs in the repo's docs; comments are for the
few things a reader of *this line* would get wrong without being told.

A comment earns its place only when the code is:

- **Out of pattern** — it looks wrong or roundabout and is not: a workaround, a required
  ordering, a deliberately swallowed error, a call that must not be "simplified".
- **Dangerous to change** — the cost of a wrong edit is high and invisible from the code:
  security, data loss, an immutable field, a value another system depends on.

When one is warranted:

- One or two lines. If it needs a paragraph, the paragraph goes in docs and the comment
  becomes a pointer: `# see docs/deploy.md#migrations`.
- Explain *why*, not *what*. Delete a comment that restates the line below it.
- Doc comments on public API (XML docs, JSDoc) state the contract in a sentence. Design
  rationale does not go there either.
- No changelog comments — that is what git is for. No "removed X" or "this used to be Y".

**A change's comments should never outweigh its code.** If they do, that is a review
finding in its own right.

## Docs

Rationale, rejected alternatives, how pieces fit together, and operational gotchas go in
the target repo's own `docs/`, where anyone reading the code will look. What spans
repos goes in spine's `docs/`. `playbooks/doc-sync/PLAYBOOK.md` has the full split.

Write docs for two readers at once, a person skimming and an agent searching:

- One topic per heading, with headings specific enough to link to and grep for.
- Lead each section with the rule or fact, then the reason. Name files, config keys and
  commands exactly as they appear in the code, so a search finds them.
- Plain statements over narrative. No "as mentioned above". Each section should stand on
  its own.

## Errors

Fail loudly and specifically at the boundary. Do not swallow an error to make output
clean. Do not add a `try`/`catch` whose only effect is to hide a failure you did not
diagnose.

## Tests

A behavior change ships with a test. A bug fix ships with a test that fails before the
fix. If something is genuinely not worth testing, say so explicitly rather than staying
quiet about it.

## Reporting

- Say what you actually did, including what did not work. If tests fail, show the output.
  If a step was skipped, name it.
- Flag assumptions at the point they were made, not at the end.
- No completion claims for work that was not verified. "Should work" is not a status.
- Keep summaries proportional — a one-file change does not need a report.

## Git

- Never commit or push unless asked.
- Never commit to the default branch — branch first.
- Never `git add -A` blindly; stage what the change actually touched.
- Never force-push, amend a pushed commit, or rewrite shared history without being asked.
- Commit messages: imperative subject under ~70 chars, body explains why.

## Scope

If the right fix is larger than what was asked, say so and get a decision. If part of a
task is blocked, finish everything else and state clearly what was left out and why.
