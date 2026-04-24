#!/usr/bin/env bash
# PreToolUse hook. Refuses writes to secret-bearing files.
# Wired to Write and Edit tools via .claude/settings.json.
# Reads the tool-call JSON from stdin, pulls file_path, decides.
# Exit 2 is the Claude Code blocking signal - the write does not happen
# and stderr is surfaced to Claude as a tool-call error.

set -u

input=$(cat)

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  fi
}

extract_path() {
  local py
  py=$(resolve_python)
  if [ -z "$py" ]; then
    return 0
  fi
  printf '%s' "$input" | "$py" -c "import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))
except Exception:
    pass"
}

path=$(extract_path)
if [ -z "$path" ]; then
  exit 0
fi

base=$(basename "$path")

# Template files are always safe - they ship example structure, not secrets.
case "$base" in
  .env.example|.env.sample|.env.template)
    exit 0
    ;;
esac

# .env and any .env.<suffix> variant (.env.local, .env.production, etc).
case "$base" in
  .env|.env.*)
    echo "Blocked by .claude/hooks/block-sensitive-writes.sh: refusing to write $path" >&2
    echo "Reason: CLAUDE.md hard rule - never commit secrets or .env files." >&2
    echo "If this is a safe template, rename to .env.example." >&2
    exit 2
    ;;
esac

# Production config files.
case "$path" in
  *production*config*|*.prod.json|*.prod.yaml|*.prod.yml|*.production.json|*.production.yaml|*.production.yml)
    echo "Blocked by .claude/hooks/block-sensitive-writes.sh: refusing to write $path" >&2
    echo "Reason: CLAUDE.md hard rule - never modify production config files directly." >&2
    exit 2
    ;;
esac

exit 0
