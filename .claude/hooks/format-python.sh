#!/usr/bin/env bash
# PostToolUse hook. After a Python file is written or edited, format with
# black and lint with flake8. If the tools are not installed yet (pre-code
# phase), no-op silently. Once requirements.txt lands in Phase 1, this
# hook becomes active automatically.
#
# flake8 findings are printed to stdout - Claude Code surfaces stdout from
# PostToolUse hooks back to the model, so lint errors become visible in
# the next turn rather than getting silently dropped.

set -u

input=$(cat)

resolve_python() {
  # Prefer python and py on Windows. python3 on Windows often resolves to the
  # Microsoft Store stub at WindowsApps\python3.exe, which is a placeholder
  # that writes "Python was not found" to stderr and exits non-zero. We
  # validate each candidate by running a trivial import before accepting it.
  for candidate in python py python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
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

# Only Python files.
case "$path" in
  *.py) ;;
  *) exit 0 ;;
esac

# Skip if file no longer exists (e.g. was deleted in a follow-up edit).
if [ ! -f "$path" ]; then
  exit 0
fi

# black is a formatter. Silent on success, non-zero on parse failure.
if command -v black >/dev/null 2>&1; then
  black --quiet "$path" 2>&1 || true
fi

# flake8 findings go to stdout so Claude sees them next turn.
if command -v flake8 >/dev/null 2>&1; then
  output=$(flake8 "$path" 2>&1 || true)
  if [ -n "$output" ]; then
    echo "flake8 findings for $path:"
    echo "$output"
  fi
fi

exit 0
