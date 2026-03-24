---
name: debug
description: Systematic debugging workflow for investigating and fixing bugs
argument-hint: "[bug-description]"
---

# Debug Workflow

Current branch: !`git branch --show-current`
Recent changes: !`git log --oneline -5`

## 1. Reproduce
- What action triggers the bug?
- What's the error message or unexpected behavior?
- Is it backend (API error, 500, wrong data) or frontend (UI, rendering, state)?

## 2. Locate
- **Backend error**: Check Django logs, read the traceback, find the file:line
- **Frontend error**: Check browser console, read the error, trace the component
- **API error**: Test endpoint with curl/httpie, check serializer validation
- **Database error**: Check migration state, inspect model constraints

## 3. Understand
- Read the relevant code thoroughly
- Trace the data flow: who calls this? with what arguments?
- Check recent git changes: `git log --oneline -10 -- <file>`
- Look for similar patterns in the codebase that work correctly

## 4. Hypothesize
- Form a specific hypothesis: "X happens because Y"
- Verify with targeted logging or a test case that reproduces the bug

## 5. Fix
- Make the minimal change that fixes the root cause
- Don't fix symptoms — fix the cause
- Don't refactor surrounding code — stay focused

## 6. Verify
- Write a regression test that would catch this bug
- Run: `ruff check && python -m pytest` or `cd frontend && npm run lint && npm run type-check`
- Commit: `fix(scope): description of what was fixed`
