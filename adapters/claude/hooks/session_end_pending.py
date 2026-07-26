#!/usr/bin/env python3
"""SessionEnd hook: if a session changed code outside spine but never wrote docs,
leave a note in docs/PENDING.md so a later session can catch up.

SessionEnd cannot talk back to the model, so this is a durable breadcrumb rather than a
prompt. Any internal error exits 0.
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SPINE = Path(__file__).resolve().parents[3]
PENDING = SPINE / "docs" / "PENDING.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_sync_reminder import edited_paths, touched_target_repo, spine_docs_dirty  # noqa: E402


def repo_guesses(paths):
    """Best-effort: the git repo root of each edited path outside spine."""
    roots = set()
    for p in paths:
        parent = Path(p).parent
        try:
            out = subprocess.run(
                ["git", "-C", str(parent), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        root = out.stdout.strip()
        if root and not root.startswith(str(SPINE)):
            roots.add(Path(root).name)
    return sorted(roots)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    transcript = payload.get("transcript_path")
    if not transcript:
        return

    paths = edited_paths(transcript)
    if not touched_target_repo(paths) or spine_docs_dirty():
        return

    repos = repo_guesses(paths) or ["unknown"]
    session_id = payload.get("session_id", "unknown")

    PENDING.parent.mkdir(parents=True, exist_ok=True)
    if not PENDING.exists():
        PENDING.write_text(
            "# Pending documentation\n\n"
            "Sessions that changed a target repo but did not update `docs/`. "
            "Clear an entry by running the `doc-sync` skill for that repo and deleting "
            "the line.\n\n",
            encoding="utf-8",
        )
    with PENDING.open("a", encoding="utf-8") as fh:
        fh.write(f"- {date.today().isoformat()} — `{', '.join(repos)}` (session {session_id[:8]})\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        pass
    sys.exit(0)
