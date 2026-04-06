#!/usr/bin/env bash
# PreToolUse hook: enforce conventional commits format
# Triggers on: Bash tool when command contains "git commit"
set -euo pipefail

INPUT=$(cat)
CMD=$(python -c "import sys,json; print(json.loads(sys.argv[1]).get('tool_input',{}).get('command',''))" "$INPUT" 2>/dev/null)

# Only check git commit commands
echo "$CMD" | grep -q 'git commit' || exit 0

# Extract commit message from -m flag (handles both single and double quotes)
MSG=$(echo "$CMD" | sed -n 's/.*-m ["\x27]\([^"\x27]*\).*/\1/p' | head -1)
[[ -z "$MSG" ]] && exit 0

# Skip merge commits and Co-Authored-By lines
echo "$MSG" | grep -qiE '^Merge |^Co-Authored' && exit 0

# Validate conventional commit format
if ! echo "$MSG" | grep -qE '^(feat|fix|chore|docs|style|refactor|test|build|ci|perf|revert)(\(.+\))?: .+'; then
  echo "BLOCKED: Commit message must follow Conventional Commits format" >&2
  echo "" >&2
  echo "Format: type(scope): description" >&2
  echo "Types: feat | fix | chore | docs | style | refactor | test | build | ci | perf | revert" >&2
  echo "" >&2
  echo "Examples:" >&2
  echo "  feat(lease): add late fee notification" >&2
  echo "  fix(contract): correct PDF margin calculation" >&2
  echo "  chore: update dependencies" >&2
  exit 2
fi

exit 0
