# Working conventions

How work gets done, regardless of stack. Agents read this; it overrides their generic
advice on conflict.

## Changes

- **Smallest change that fully solves the problem.** Not the smallest change that makes
  the symptom go away, and not a rewrite of the surrounding area.
- Match the surrounding code — its naming, its structure, its comment density — even
  where you would have written it differently. A file with two styles is worse than a
  file with one style you dislike.
- No unrequested refactors mixed into a functional change. Note the opportunity; do it
  separately if asked.
- Do not add a compatibility shim, feature flag, or abstraction layer for a future that
  has not been asked for.

## Comments

Explain *why*, not *what*. Delete a comment that restates the line below it. No
changelog comments in code — that is what git is for. No "removed X" or "this used to
be Y" markers.

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
