#!/usr/bin/env bash
# PreToolUse hook: block edits to generated/vendored files
# Triggers on: Edit, Write tools
set -euo pipefail

FILE=$(python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path','') or json.load(sys.stdin).get('tool_input',{}).get('path',''))" 2>/dev/null <<< "$(cat)")
[[ -z "$FILE" ]] && exit 0

case "$FILE" in
  *node_modules/*)
    echo "BLOCKED: Cannot edit node_modules files: $FILE" >&2
    exit 2 ;;
  *dist/*|*build/*|*.next/*)
    echo "BLOCKED: Cannot edit build output: $FILE" >&2
    exit 2 ;;
  *__pycache__/*)
    echo "BLOCKED: Cannot edit Python cache: $FILE" >&2
    exit 2 ;;
  *package-lock.json|*yarn.lock|*poetry.lock)
    echo "BLOCKED: Cannot edit lockfiles: $FILE" >&2
    exit 2 ;;
  */migrations/0*.py)
    echo "BLOCKED: Cannot edit existing migrations. Create a new migration instead: $FILE" >&2
    exit 2 ;;
esac

exit 0
