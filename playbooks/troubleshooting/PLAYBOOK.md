---
name: troubleshooting
description: Systematic debugging procedure for a failure whose cause is not yet known — a bug, a broken build, a failing test, a production incident, or behavior that contradicts the code. Use when the instinct is to start guessing at fixes.
---

# Troubleshooting

A procedure for failures where you do not yet know the cause. Its purpose is to stop the
single most expensive debugging habit: **changing code before understanding the failure.**

## When to use

- A bug reproduces but the cause is unclear
- A test or build fails for reasons the error message does not explain
- Behavior contradicts what the code appears to say
- A previous fix attempt did not work

Skip it when the error message already names the cause and the fix is obvious. Do not
skip it because the fix *feels* obvious — a wrong obvious fix costs more than five
minutes of reading.

## The procedure

### 1. State the failure precisely

Write it down before touching anything:

- **Expected:** what should happen
- **Actual:** what does happen, verbatim — full error, full stack trace, exact output
- **Trigger:** the smallest set of steps that produces it
- **Scope:** always or intermittently? one environment or all? since when?

If you cannot fill these in, you are not ready to debug — you are ready to *observe*.
Go get the missing information.

### 2. Reproduce it

A failure you cannot reproduce on demand is a failure you cannot confirm you fixed.
Get to a one-command reproduction. Shrink it: remove steps, shrink the input, isolate
the layer. Every element you remove that keeps the failure alive narrows the search.

If it only reproduces intermittently, treat that as data — it points at timing, ordering,
shared state, caching, or an external dependency.

### 3. Establish the last known good state

`git log` / `git bisect` on the reproduction. "It worked on Tuesday" plus a bisect is
often the entire investigation. Also ask what changed *around* the code: dependency
versions, config, data, infrastructure, upstream APIs, clock/timezone, the environment.

### 4. Read the actual error

Read the whole stack trace, top to bottom, not just the last line. Find the first frame
in code you own. Then **read that code** — the real current version on disk, not your
memory of it. A surprising share of bugs are visible on inspection once you look at the
right twenty lines.

### 5. Form one falsifiable hypothesis

Say it explicitly: *"X is null because Y returns early when Z, and the caller does not
check."* A hypothesis you cannot disprove with a specific observation is not a
hypothesis — it is a hunch. Refine it until it makes a concrete prediction.

### 6. Test the hypothesis without fixing anything

Add a log line, a breakpoint, an assertion, a test. Observe. **Confirmed or refuted?**

If refuted, that is progress — you have eliminated a branch. Return to step 5 with what
you learned. Do not modify the hypothesis to survive the evidence.

Bisect the *space*, not just the history: is the bad value already wrong when it enters
this function, or does this function make it wrong? Halve the distance between "known
correct" and "known wrong" until the gap is one operation.

### 7. Understand *why* before fixing

You have found where it breaks. Now answer: why was the code written this way? Is the
bug the code, the assumption behind it, or the contract with the caller? Fixing the
symptom at the wrong layer is how a bug comes back in a different shape.

### 8. Fix, prove, and check the blast radius

- Write a test that **fails before the fix and passes after**. Verify it fails first —
  an untested test proves nothing.
- Make the smallest fix that addresses the cause, not the symptom.
- Search for the same pattern elsewhere in the codebase. Bugs of a kind rarely appear
  once.
- Remove the debugging instrumentation you added — unless a log line there is genuinely
  worth keeping, in which case keep it deliberately.

### 9. Record it

If the cause was non-obvious, it belongs in the target repo's `docs/troubleshooting.md`
(spine's `docs/` if the failure crossed repos): the
symptom, the cause, the fix, and the signal that would identify it faster next time.
Future sessions search that file.

## Anti-patterns

| Habit | Why it costs you |
|---|---|
| Changing several things at once | You learn nothing from the result, pass or fail |
| "Try this and see" without a hypothesis | Random walk; may mask the bug rather than fix it |
| Trusting the code you remember | The bug is usually in the gap between memory and disk |
| Blaming the framework, compiler, or library first | It is almost always your code. Almost. |
| Adding a retry / sleep / try-catch to make it stop | Converts a visible bug into an invisible one |
| Declaring victory on one passing run | For intermittent failures, run it enough times to mean something |

## When you are stuck

After roughly three refuted hypotheses, change approach rather than grinding:

- Re-read the failure statement from step 1 — is the *expectation* actually correct?
- Question an assumption you have not tested. List them; the bug is hiding in one.
- Build the minimal reproduction in isolation, outside the project.
- Read the dependency's source. Not the docs — the source.
- Explain the problem out loud, in full, from the beginning.
- Say plainly that you are stuck, what you have ruled out, and what you would try next.
  A clear dead end reported early is worth more than an hour of silent thrashing.
