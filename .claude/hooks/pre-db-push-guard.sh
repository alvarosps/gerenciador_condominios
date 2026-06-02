#!/usr/bin/env bash
set -euo pipefail

# PreToolUse(Bash) CRITICAL DATA-SAFETY GUARD.
# IMPORTANT: the user's global ~/.claude runs defaultMode: bypassPermissions, which makes the
# settings.json permissions layer (allow/ask/DENY) INERT. PreToolUse hooks, however, run
# regardless of permission mode — so THIS hook is the PRIMARY (and effectively only) enforcement
# for destructive DB operations on real condo/financial data. Catches forms permission globs miss:
# `cd x && manage.py flush`, env prefixes, compound commands, raw SQL via psql. Parses stdin JSON
# via node (jq is not installed on this machine).
CMD=$(cat | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{const j=JSON.parse(s);process.stdout.write(String(j.tool_input?.command||""))}catch{process.stdout.write("")}})' 2>/dev/null || true)
[[ -z "$CMD" ]] && exit 0

block() {
  echo "BLOCKED: destructive DB operation on a repo with real condo/financial data." >&2
  echo "Back up first ('python scripts/backup_db.py'); run it deliberately outside Claude if truly intended." >&2
  echo "(Global rule: pg_dump backup BEFORE any destructive DB op — never flush/reset/drop/rollback on real data.)" >&2
  exit 2
}

# (1) Destructive or interactive manage.py subcommands (covers `cd x && ...`, env prefixes, compound).
#     dbshell opens an interactive raw-SQL session whose statements are invisible to this hook — block outright;
#     use `manage.py shell` (ORM) instead.
if printf '%s' "$CMD" | grep -qiE 'manage\.py[[:space:]]+(flush|sqlflush|sqlclear|reset_db|dbshell)([[:space:]]|$)'; then block; fi

# (2) Reverse / unapply migrations: `migrate <app> zero` drops every table of an app — as destructive as flush.
if printf '%s' "$CMD" | grep -qiE 'manage\.py[[:space:]]+migrate\b[^|;&]*\bzero\b'; then block; fi

# (3) Raw destructive SQL through the psql client:
#     (a) file-fed / redirected SQL (psql -f / psql < ) is uninspectable — require a backup;
#     (b) an inline destructive DDL/DML verb on the psql command line.
if printf '%s' "$CMD" | grep -qiE '\bpsql\b' && printf '%s' "$CMD" | grep -qiE '(-f[[:space:]=]|<)'; then block; fi
if printf '%s' "$CMD" | grep -qiE '\bpsql\b' \
   && printf '%s' "$CMD" | grep -qiE '\b(DROP[[:space:]]+(TABLE|DATABASE|SCHEMA|INDEX)|ALTER[[:space:]]+TABLE[^;]*DROP|TRUNCATE|DELETE[[:space:]]+FROM)\b'; then block; fi

exit 0
