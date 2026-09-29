#!/usr/bin/env python3
"""Stop hook: remind the session to update spine's docs once it has changed code
in a target repository.

Fires at most once per session, and only when both are true:
  * the session edited files outside spine (i.e. it was an implementation session)
  * nothing under spine's docs/ has been written

Reads the standard Stop-hook JSON payload on stdin. Emits a `block` decision with
instructions, or exits silently. Any internal error exits 0 — a broken hook must never
wedge a session.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SPINE = Path(__file__).resolve().parents[3]
STATE = SPINE / ".claude" / ".state"

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

REASON = """\
This session changed code outside spine, but spine's docs/ has not been updated.

If the implementation work is complete, follow the `doc-sync` skill now: update the
target repo's own docs/, update spine's cross-repo docs if the work crossed a repo
boundary, and append a session entry to spine's docs/sessions/<repo>.md.

If you are still mid-task, say so briefly and carry on — this reminder fires only once
per session."""


def edited_paths(transcript_path):
    """File paths passed to edit-shaped tools, from the session transcript."""
    paths = []
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (entry.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and block.get("name") in EDIT_TOOLS:
                        fp = (block.get("input") or {}).get("file_path")
                        if fp:
                            paths.append(fp)
    except OSError:
        pass
    return paths


def touched_target_repo(paths):
    spine = str(SPINE)
    for p in paths:
        try:
            resolved = str(Path(p).resolve())
        except OSError:
            resolved = p
        if not resolved.startswith(spine + os.sep):
            return True
    return False


def spine_docs_dirty():
    """True if this session appears to have written docs. PENDING.md is excluded —
    it is written by the SessionEnd hook, and counting it would permanently silence
    this check."""
    try:
        out = subprocess.run(
            ["git", "-C", str(SPINE), "status", "--porcelain", "--",
             "docs", ":(exclude)docs/PENDING.md"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return True  # can't tell -> assume handled, stay quiet
    if out.returncode != 0:
        return True
    return bool(out.stdout.strip())


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    if payload.get("stop_hook_active"):
        return  # already blocked once this turn; never loop

    session_id = payload.get("session_id") or "unknown"
    marker = STATE / f"docsync-{session_id}"
    if marker.exists():
        return

    transcript = payload.get("transcript_path")
    if not transcript:
        return

    paths = edited_paths(transcript)
    if not touched_target_repo(paths):
        return
    if spine_docs_dirty():
        return

    STATE.mkdir(parents=True, exist_ok=True)
    marker.touch()
    json.dump({"decision": "block", "reason": REASON}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a hook must never break the session
        pass
    sys.exit(0)
