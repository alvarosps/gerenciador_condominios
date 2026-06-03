#!/usr/bin/env bash
set -euo pipefail

# PreToolUse(Edit|Write) hook: block edits to generated / vendored / build-output files and to
# ALREADY-COMMITTED migrations. Reads the tool input JSON on stdin and parses the path with node
# (always present in this Node-frontend repo; jq is not installed and python may be absent from the
# Git-Bash PATH on Windows — the prior python-based version failed open and silently disabled this guard).
FILE=$(cat | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{const j=JSON.parse(s);process.stdout.write(String(j.tool_input?.file_path||j.tool_input?.path||""))}catch{process.stdout.write("")}})' 2>/dev/null || true)
[[ -z "$FILE" ]] && exit 0
# Normalize Windows backslashes so the forward-slash globs below match.
FILE="${FILE//\\//}"

case "$FILE" in
  *node_modules/*|*/dist/*|*/build/*|*/.next/*|*/__pycache__/*)
    echo "BLOCKED: cannot edit generated/build-output file: $FILE" >&2
    exit 2 ;;
  *package-lock.json|*yarn.lock|*pnpm-lock.yaml|*poetry.lock|*uv.lock|*.lock)
    echo "BLOCKED: cannot edit lockfiles: $FILE" >&2
    exit 2 ;;
  */migrations/0*.py)
    # Block only migrations already committed (applied/shared). A freshly created
    # makemigrations/--empty file is still untracked, so editing it (e.g. to add RunPython
    # to a data migration) is allowed.
    if ( cd "$(dirname "$FILE")" 2>/dev/null && git ls-files --error-unmatch -- "$(basename "$FILE")" >/dev/null 2>&1 ); then
      echo "BLOCKED: cannot edit a committed migration. Create a new one: 'python manage.py makemigrations'. ($FILE)" >&2
      exit 2
    fi
    ;;
esac
exit 0
