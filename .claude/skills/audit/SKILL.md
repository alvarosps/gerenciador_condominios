---
name: audit
description: Use at the end of every implementation session to verify completeness against the original plan. Compares what was implemented vs what was specified, finds gaps, and fixes them before closing the session. Never skip this.
---

# Session Audit — Verificação de Completude

Current branch: !`git branch --show-current`
Recent commits: !`git log --oneline -10`

## The Rule

**Every implementation session MUST end with an audit.** No session is complete until the audit passes. No exceptions.

---

## Audit Process

### 1. Identify the Plan

Determine which plan/prompt was being executed:

- Check `prompts/SESSION_STATE.md` for current session
- Read the original prompt file (e.g., `prompts/03-backend-viewsets-simple.md`)
- Read the design doc if referenced: `docs/plans/2026-03-21-financial-module-design.md`

### 2. Extract Acceptance Criteria

From the original plan, extract EVERY:
- [ ] File that should have been **created**
- [ ] File that should have been **modified**
- [ ] Feature/function that should have been **implemented**
- [ ] Test scenario that should have been **covered**
- [ ] Acceptance criterion listed (the `## Critérios de Aceite` section)

### 3. Verify Each Item — One by One

For EACH item from the plan, verify it was actually done:

```
For each file to create:
  → Does it exist? Read it.
  → Does it contain what the plan specified?
  → Is it complete or partial?

For each file to modify:
  → Was it modified? Check git diff.
  → Were ALL specified changes made?

For each feature/function:
  → Does it exist in the code?
  → Does it implement the FULL specification, not a subset?
  → Does it handle all edge cases mentioned in the plan?

For each test scenario:
  → Does a test exist for it?
  → Does the test actually verify the behavior (not just assert True)?
  → Does the test pass?
```

### 4. Run Full Verification

```bash
# Backend
ruff check
ruff format --check
python -m pytest tests/ -v --tb=short

# Frontend (if touched)
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

ALL must pass with zero errors.

### 5. Gap Analysis

List every gap found:

```markdown
## Gaps Found

| # | What was specified | What was implemented | Gap |
|---|-------------------|---------------------|-----|
| 1 | PersonViewSet with 5 filters | PersonViewSet with 3 filters | Missing: is_owner, is_employee filters |
| 2 | Test: singleton returns same instance | No test for this | Missing test |
| 3 | ... | ... | ... |
```

### 6. Fix ALL Gaps

For EACH gap:
1. Implement what's missing — following the original specification exactly
2. Run tests after each fix
3. Mark the gap as resolved

**DO NOT:**
- Skip a gap because "it's minor"
- Implement a workaround instead of the specified solution
- Add `# TODO` comments instead of implementing
- Simplify the specification to match what was built
- Close the session with any gap remaining

### 7. Final Verification

After all gaps are fixed:
1. Re-run the full verification suite (step 4)
2. Re-check every acceptance criterion from the plan
3. Only proceed if ALL criteria pass

### 8. Update State

```bash
# Update SESSION_STATE.md with:
# - Session marked as "concluída"
# - Files created/modified listed
# - Any architectural decisions noted
# - Known issues (pre-existing only, not new gaps)
```

### 9. Commit

```bash
git add <specific files>
git commit -m "feat(scope): complete session NN — [description]

Audit: all acceptance criteria verified
- [N] files created
- [N] files modified
- [N] tests passing
- Zero gaps remaining"
```

---

## Anti-Patterns — What Audit Must Catch

| Anti-Pattern | How to detect | Fix |
|-------------|--------------|-----|
| **Partial implementation** | Function exists but doesn't handle all cases from spec | Complete it |
| **Missing validation** | Serializer validate() doesn't check all rules from spec | Add missing checks |
| **Placeholder tests** | Test exists but asserts `True` or just checks existence | Write real assertions |
| **Missing edge case** | Plan says "handle prepaid leases" but code doesn't check `prepaid_until` | Implement the check |
| **Wrong error message** | Plan says Portuguese, code uses English | Fix language |
| **Missing filter** | ViewSet should have 9 filters, only has 6 | Add the 3 missing |
| **Skipped acceptance criterion** | Criterion not checked because "it's obvious" | Verify explicitly |
| **Workaround** | Plan says "use ORM aggregation", code uses raw Python loop | Rewrite with ORM |

---

## Audit Mindset

Think like a QA engineer reviewing a contractor's work against the SOW (Statement of Work):
- Every line item must be delivered
- "Close enough" is not delivered
- If the plan says X, the code must do X — not Y that's "similar"
- If something is genuinely wrong in the plan, flag it and fix BOTH the plan and the code
