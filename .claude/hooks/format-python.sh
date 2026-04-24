#!/usr/bin/env bash
# PostToolUse hook. After a Python file is written or edited, format with
# black and lint with flake8. Prefers the project venv (.venv) over system
# python so tools installed via requirements-dev.txt are found without the
# user having to activate the venv. If neither has the tools, no-op silently.
#
# flake8 findings are printed to stdout - Claude Code surfaces stdout from
# PostToolUse hooks back to the model, so lint errors become visible in
# the next turn rather than getting silently dropped.

set -u

input=$(cat)

# Extract the first "file_path":"..." value. Assumes no embedded escaped
# quotes in the path - true for every OS path Claude Code produces.
path=$(printf '%s' "$input" \
  | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' \
  | head -1 \
  | sed -E 's/^"file_path"[[:space:]]*:[[:space:]]*"//; s/"$//')

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

# Find a python interpreter that has the requested module installed.
# Prefer the project venv so requirements-dev.txt tools are found.
find_python_with() {
  local module="$1"
  for py in ".venv/Scripts/python.exe" ".venv/bin/python"; do
    if [ -x "$py" ] && "$py" -c "import $module" >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
  done
  for py in python py python3; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c "import $module" >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
  done
}

BLACK_PY=$(find_python_with black)
if [ -n "$BLACK_PY" ]; then
  "$BLACK_PY" -m black --quiet "$path" 2>&1 || true
fi

FLAKE8_PY=$(find_python_with flake8)
if [ -n "$FLAKE8_PY" ]; then
  output=$("$FLAKE8_PY" -m flake8 "$path" 2>&1 || true)
  if [ -n "$output" ]; then
    echo "flake8 findings for $path:"
    echo "$output"
  fi
fi

exit 0
