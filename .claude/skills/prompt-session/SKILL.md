---
name: prompt-session
description: Use when executing a numbered implementation session (prompts/01-*.md through prompts/15-*.md). Loads the prompt, checks prerequisites, guides execution with TDD, and runs audit at the end.
argument-hint: "[session-number, e.g. 03]"
---

# Prompt Session Execution

Session state: !`cat prompts/SESSION_STATE.md | head -30`
Current branch: !`git branch --show-current`

## Session Lifecycle

```
1. LOAD     → Read the prompt, check prerequisites
2. PLAN     → Review scope, identify files, load exemplars
3. TEST     → Write failing tests (Red)
4. BUILD    → Implement until tests pass (Green)
5. REFINE   → Clean up without changing behavior (Refactor)
6. VERIFY   → Run full suite (ruff + mypy + pytest + eslint + tsc)
7. AUDIT    → Run /audit to verify 100% completeness against plan
8. HANDOFF  → Update SESSION_STATE.md, commit
```

---

## 1. LOAD — Read and Validate

Given session number `$ARGUMENTS`:

```
Read: prompts/$ARGUMENTS-*.md           → The session prompt
Read: prompts/SESSION_STATE.md          → Current state
Read: prompts/00-prompt-standard.md     → Exemplar reference
```

**Prerequisites check:**
- All previous sessions must be "concluída" in SESSION_STATE.md
- If a prerequisite is "pendente", STOP and inform the user

**Context loading:**
- Read the design doc: `docs/plans/2026-03-21-financial-module-design.md` (only sections relevant to this session)
- Read exemplar files referenced in the prompt (specific line ranges)
- Load domain skill: `/financial` or `/admin` depending on scope

## 2. PLAN — Review Scope

From the prompt, extract and confirm:
- **Files to create**: list them
- **Files to modify**: list them
- **What NOT to do**: constraints
- **Acceptance criteria**: binary checklist

Present this plan to the user. Ask: "Ready to start?"

## 3. TEST — Red Phase (TDD)

Following the prompt's `## TDD` section:

1. Create the test file(s) specified
2. Write ALL test scenarios listed in the prompt
3. Run tests — they MUST fail (Red)
4. If tests pass without implementation, the tests are wrong — fix them

```bash
# Backend
python -m pytest <test_file> -v --no-header

# Frontend
cd frontend && npm run test:unit -- --reporter=verbose <test_file>
```

**Test quality rules:**
- Mock ONLY external boundaries (Chrome, HTTP, filesystem)
- Use factory-boy/model-bakery for test data
- Test behavior, not implementation
- Each test scenario from the prompt = one test function

## 4. BUILD — Green Phase

Implement the minimum code to make all tests pass:

1. Follow the exemplar patterns from `00-prompt-standard.md`
2. Follow the domain skill rules (`/financial` or `/admin`)
3. After each file, run the relevant tests
4. Continue until ALL tests pass (Green)

```bash
python -m pytest <test_file> -v
```

## 5. REFINE — Refactor Phase

With all tests green:
1. Clean up code (extract helpers, improve naming)
2. Run tests after each change — must stay green
3. Do NOT add features beyond the prompt scope

## 6. VERIFY — Full Suite

Run the complete verification:

```bash
# Backend
ruff check
ruff format --check
python -m pytest tests/ -v --tb=short -x

# Frontend (if this session touches frontend)
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

ALL must pass with zero errors. No `# noqa`, no `eslint-disable`.

## 7. AUDIT — Completeness Check

Run `/audit` skill. This is mandatory — no session ends without it.

The audit will:
- Compare every acceptance criterion against the implementation
- Find gaps
- Fix gaps
- Re-verify

## 8. HANDOFF — State Update

After audit passes:

1. Update `prompts/SESSION_STATE.md`:
   - Mark session as "concluída"
   - List files created/modified
   - Note any architectural decisions
   - Note any corrections to the design doc

2. Commit:
```bash
git add <specific files>
git commit -m "feat(financial): complete session $ARGUMENTS — [description]

Audit: all acceptance criteria verified"
```

3. Inform the user what was completed and what the next session is.

---

## Error Recovery

| Situation | Action |
|-----------|--------|
| Tests won't pass | Debug the implementation, not the tests (unless tests are wrong per spec) |
| Lint/type errors | Fix them — never use inline suppression |
| Prompt spec is ambiguous | Check the design doc for clarification. If still ambiguous, ask the user |
| Prompt spec conflicts with existing code | The design doc is the source of truth. If the code diverges, fix the code |
| Previous session left issues | Note in SESSION_STATE.md but don't fix outside current session scope |

## Parallel Execution

For sessions that span backend + frontend (e.g., session 09):
- Use `@implementer` agent (worktree-isolated) for backend
- Use another `@implementer` for frontend
- Each works in its own worktree, changes merged after both pass
