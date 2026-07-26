#!/usr/bin/env bash
# Generate the Claude Code harness tree from spine's neutral definitions.
#
#   agents/<name>.md              ->  .claude/agents/<name>.md        (copied verbatim)
#   playbooks/<name>/PLAYBOOK.md  ->  .claude/skills/<name>/SKILL.md  (renamed)
#   playbooks/<name>/<other>      ->  .claude/skills/<name>/<other>   (copied)
#
# The generated trees are rebuilt from scratch every run. Never hand-edit them.

set -euo pipefail

SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SPINE"

AGENTS_OUT=".claude/agents"
SKILLS_OUT=".claude/skills"

rm -rf "$AGENTS_OUT" "$SKILLS_OUT"
mkdir -p "$AGENTS_OUT" "$SKILLS_OUT"

fail() { printf 'sync: %s\n' "$1" >&2; exit 1; }

# --- agents ------------------------------------------------------------------
agent_count=0
shopt -s nullglob
for src in agents/*.md; do
  name="$(basename "$src" .md)"
  head -n1 "$src" | grep -qx -- '---' || fail "$src: missing YAML frontmatter"
  grep -qE "^name: *${name}$" "$src" || fail "$src: frontmatter 'name' must be '${name}'"
  grep -qE '^description: *\S' "$src" || fail "$src: frontmatter needs a 'description'"
  cp "$src" "$AGENTS_OUT/$name.md"
  agent_count=$((agent_count + 1))
done

# --- playbooks -> skills -----------------------------------------------------
skill_count=0
for dir in playbooks/*/; do
  name="$(basename "$dir")"
  book="$dir/PLAYBOOK.md"
  [ -f "$book" ] || fail "$dir: no PLAYBOOK.md"
  head -n1 "$book" | grep -qx -- '---' || fail "$book: missing YAML frontmatter"
  grep -qE "^name: *${name}$" "$book" || fail "$book: frontmatter 'name' must be '${name}'"
  grep -qE '^description: *\S' "$book" || fail "$book: frontmatter needs a 'description'"

  mkdir -p "$SKILLS_OUT/$name"
  cp "$book" "$SKILLS_OUT/$name/SKILL.md"
  # any supporting files travel with the playbook
  find "$dir" -mindepth 1 -maxdepth 1 ! -name PLAYBOOK.md -exec cp -R {} "$SKILLS_OUT/$name/" \;
  skill_count=$((skill_count + 1))
done
shopt -u nullglob

# --- hooks -------------------------------------------------------------------
chmod +x adapters/claude/hooks/*.py 2>/dev/null || true

printf 'sync: %d agents -> %s\n' "$agent_count" "$AGENTS_OUT"
printf 'sync: %d skills -> %s\n' "$skill_count" "$SKILLS_OUT"
