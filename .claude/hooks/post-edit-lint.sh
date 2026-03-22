#!/usr/bin/env bash
# PostToolUse hook: auto-lint after file edits
# Triggers on: Edit, Write tools
set -euo pipefail

INPUT=$(cat)
FILE=$(python -c "import sys,json; d=json.loads(sys.argv[1]).get('tool_input',{}); print(d.get('file_path','') or d.get('path',''))" "$INPUT" 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

# Only lint files in our project, skip vendored
case "$FILE" in
  *node_modules/*|*dist/*|*.next/*|*__pycache__/*|*.lock) exit 0 ;;
esac

case "$FILE" in
  *.py)
    ruff format --quiet "$FILE" 2>/dev/null || true
    ruff check --fix --quiet "$FILE" 2>/dev/null || true
    ;;
  *.ts|*.tsx|*.js|*.jsx)
    FRONTEND_DIR=$(dirname "$FILE")
    while [[ "$FRONTEND_DIR" != "/" && ! -f "$FRONTEND_DIR/package.json" ]]; do
      FRONTEND_DIR=$(dirname "$FRONTEND_DIR")
    done
    if [[ -f "$FRONTEND_DIR/package.json" ]]; then
      (cd "$FRONTEND_DIR" && npx eslint --fix "$FILE" 2>/dev/null || true)
    fi
    ;;
esac

exit 0
