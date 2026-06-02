#!/usr/bin/env node
// PreToolUse(Bash) hook: enforce Conventional Commits on `git commit -m "..."`.
// Robust extraction (vs the prior sed): tokenizes the command honoring quotes,
// validates the FIRST -m/--message value (git's subject line), and tolerates
// internal quotes/apostrophes. Heredoc/command-substitution messages are skipped
// (cannot be parsed reliably here — a commit-msg git hook would cover those).
'use strict';

let raw = '';
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  let cmd = '';
  try { cmd = String(JSON.parse(raw).tool_input?.command || ''); } catch { /* not JSON */ }
  if (!cmd) process.exit(0);

  // Must be a `git ... commit`. Tolerate arbitrary git global options before `commit`
  // (e.g. `git -c user.name=x commit`, `git --no-pager commit`, `git -C <dir> commit`, `git -p commit`).
  if (!/(^|\s)git(\s+(-c\s+\S+|-C\s+\S+|--\S+|-[A-Za-z]\S*))*\s+commit(\s|$)/.test(cmd)) process.exit(0);

  // Tokenize honoring single/double quotes (quotes are removed; adjacent text joins).
  const toks = [];
  let cur = '', q = null, hadQuote = false;
  for (const c of cmd) {
    if (q) { if (c === q) q = null; else cur += c; continue; }
    if (c === '"' || c === "'") { q = c; hadQuote = true; continue; }
    if (/\s/.test(c)) { if (cur || hadQuote) { toks.push(cur); cur = ''; hadQuote = false; } continue; }
    cur += c;
  }
  if (cur || hadQuote) toks.push(cur);

  // First -m / --message value (subject line).
  let msg = null;
  for (let i = 0; i < toks.length; i++) {
    const t = toks[i];
    if (t === '-m' || t === '--message') { msg = toks[i + 1] ?? ''; break; }
    let m = t.match(/^(?:--message|-m)=(.*)$/s); if (m) { msg = m[1]; break; }
    m = t.match(/^-m(.+)$/s); if (m) { msg = m[1]; break; } // -m"msg" / -mmsg form
  }
  if (msg == null || msg === '') process.exit(0);
  if (/\$\(|<</.test(msg)) process.exit(0); // command substitution / heredoc — skip

  const ok = /^(feat|fix|chore|docs|style|refactor|test|build|ci|perf|revert)(\([^)]+\))?!?: .+/.test(msg);
  if (ok) process.exit(0);

  process.stderr.write('BLOCKED: commit must follow Conventional Commits.\n');
  process.stderr.write('Format: type(scope): description\n');
  process.stderr.write('Types: feat|fix|chore|docs|style|refactor|test|build|ci|perf|revert\n');
  process.exit(2);
});
