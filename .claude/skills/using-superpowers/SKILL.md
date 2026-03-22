---
name: using-superpowers
description: Use when starting any session — establishes how to find and use skills before any action, including clarifying questions.
---

# Using Skills

## The Rule

**Check for relevant skills BEFORE ANY response** — including clarifying questions.

If there is even a 1% chance a skill applies, read it first.

---

## Flow

```
User message arrives
        ↓
Does a skill apply? (even 1% chance)
    YES → read the skill → announce "Using [skill] to [purpose]"
          → if skill has a checklist, work through it item by item
          → follow the skill exactly
    NO  → respond directly
```

### Available Skills

```
# Process skills (use FIRST)
/brainstorming     — Collaborative design before implementation
/debug             — Systematic bug investigation and fix

# Planning skills (after brainstorming, before implementation)
/prompt-writing    — Write TDD implementation plans split into sessions

# Domain skills (use for domain-specific logic)
/financial         — Financial module: cash flow, expenses, installments, simulations
/admin             — Property admin: buildings, apartments, tenants, leases, contracts

# Execution skills (for implementation)
/prompt-session NN — Execute numbered session (01-15) with TDD + audit
/new-feature       — End-to-end feature implementation (backend + frontend)
/refactor          — Safe refactoring with tests as safety net

# Verification skills (MANDATORY at session end)
/audit             — Verify 100% completeness against plan, fix gaps
```

---

## Skill Priority Order

When multiple skills could apply:

1. **Process skills first** (brainstorming, debug): determine _how_ to approach
2. **Planning skills second** (prompt-writing): create the execution plan
3. **Domain skills third** (financial, admin): provide business rules
4. **Execution skills fourth** (prompt-session, new-feature, refactor): guide implementation
5. **Verification skills LAST** (audit): verify completeness — MANDATORY

Examples:

- "Add expense tracking" → `/brainstorming` → `/prompt-writing` → `/prompt-session`
- "Fix the late fee calculation" → `/debug` → `/admin`
- "Implement cash flow projection" → `/financial` → `/new-feature`
- "Run session 03" → `/prompt-session 03` → `/financial` (loaded by session) → `/audit`
- "Plan a new reporting feature" → `/brainstorming` → `/prompt-writing`
- "Extract service from viewset" → `/refactor` → `/audit`
- "Review these changes" → `@reviewer` agent

### The Complete Workflow

```
Idea → /brainstorming → /prompt-writing → /prompt-session NN → /audit
```

For existing prompts (01-15), skip brainstorming and prompt-writing:
```
/prompt-session 03 → (loads /financial or /admin) → TDD → /audit
```

---

## Parallel Work — Agent Teams & Worktrees

Agent teams are enabled in this project (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).

### When to use Agent Teams
- 2+ independent areas need parallel exploration (e.g., "review security + performance + tests")
- Cross-layer coordination (backend + frontend + tests each owned by a teammate)
- Debugging with competing hypotheses
- Research across multiple modules simultaneously

### When to use Subagents with Worktrees
- The `implementer` and `tester` agents use `isolation: worktree` — they get an isolated copy of the repo
- Use worktrees when multiple implementations could conflict (editing the same files)
- Each worktree agent works on its own branch, changes are merged after review

### When to use plain Subagents (no worktree)
- Quick, focused tasks where only the result matters (read-only research, linting)
- The `reviewer` agent runs without worktree — it's read-only with `permissionMode: plan`

### Available Agents
```
@implementer  — Implements features (worktree-isolated, Sonnet)
@reviewer     — Reviews code (read-only, Opus, persistent memory)
@tester       — Writes tests (worktree-isolated, Sonnet, persistent memory)
```

---

## Red Flags

These thoughts mean STOP — you're rationalizing skipping a skill:

| Thought                             | Reality                                            |
| ----------------------------------- | -------------------------------------------------- |
| "This is just a simple question"    | Questions are tasks. Check for skills.             |
| "I need more context first"         | Skill check comes BEFORE clarifying questions.     |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first.       |
| "I can check git/files quickly"     | Files lack conversation context. Check for skills. |
| "Let me gather information first"   | Skills tell you HOW to gather information.         |
| "This doesn't need a formal skill"  | If a skill exists, use it.                         |
| "I remember this skill"             | Skills evolve. Read the current version.           |
| "This doesn't count as a task"      | Action = task. Check for skills.                   |
| "The skill is overkill for this"    | Simple things become complex. Use it.              |
| "I'll just do this one thing first" | Check BEFORE doing anything.                       |
| "I already know what to do"         | The skill might contradict you. Read it.           |

---

## Skill Types

**Rigid** (debug, new-feature, refactor): Follow exactly. The workflow exists because of known failure modes.

**Flexible** (brainstorming): Adapt principles to context.

The skill itself tells you which type it is. When unsure, treat it as rigid.

---

## Project-Specific Reminders

- **`/brainstorming` before implementation** — any feature that skips design produces misaligned code
- **`/debug` before fixing bugs** — hypothesize first, don't guess-and-check
- **Verify lint/type-check before claiming done** — `ruff check && cd frontend && npm run lint && npm run type-check`
- **Use worktree isolation for parallel implementations** — prevents file conflicts between agents
- **Use agent teams for cross-layer work** — backend + frontend + tests can each have a teammate
- **Mock policy** — mock ONLY external boundaries, never internal code
- **No `# noqa` or `eslint-disable`** — always fix the actual code
