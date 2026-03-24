---
name: brainstorming
description: Use before any creative work — creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements, and design before implementation.
disable-model-invocation: true
---

# Brainstorming — Ideas Into Designs

Turn ideas into fully formed, architecture-compliant designs through collaborative dialogue.

## The Process

### 1. Understand the Idea

Start by reading current project context:

- Recent changes: `git log --oneline -10`
- Architecture overview: `CLAUDE.md`, `.claude/rules/architecture.md`
- Relevant existing code in the affected area

Then ask questions **one at a time** to refine the idea:

- Prefer multiple-choice when possible — easier to answer than open-ended
- Only one question per message; break complex topics into a sequence
- Focus on: purpose, constraints, success criteria, affected layers

### 2. Explore Approaches

Propose **2–3 different approaches** with trade-offs. Lead with your recommendation and explain why. Don't skip this — even if one approach is clearly better, naming the alternatives prevents blind spots.

### 3. Architecture Gate

Before presenting any design, verify it complies with the project's non-negotiable constraints:

| Constraint            | Rule                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| Dependency direction  | Views → Services → Models (never backwards)                                             |
| Business logic        | All business logic in `core/services/` — never in views or serializers                  |
| Serializer pattern    | Dual pattern: nested read (`BuildingSerializer(read_only=True)`), `_id` write           |
| Soft delete           | All models use `AuditMixin` + `SoftDeleteMixin` — default querysets exclude deleted     |
| Cache invalidation    | New models need signal handlers in `core/signals.py`                                    |
| Frontend state        | Server state via TanStack Query, client state via Zustand (auth only), forms via RHF+Zod|
| CRUD pages            | Use `useCrudPage` hook — never build CRUD state management from scratch                 |
| Mock policy           | Tests mock ONLY external boundaries — never internal code or libraries                  |
| No inline suppression | Never use `# noqa`, `# type: ignore`, `eslint-disable` — fix the actual code           |
| Lint compliance       | All code must pass `ruff check`, `mypy`, `npm run lint`, `npm run type-check`           |

If a proposed design violates any of these, flag it explicitly before proceeding.

### 4. Present the Design

Once you understand what you're building, present the design in sections of 200–300 words. After each section, ask whether it looks right before continuing.

Cover:

- **Architecture**: which layers are touched (models, serializers, services, views, frontend hooks, pages)
- **Components**: new classes/functions, where they live
- **Data flow**: inputs → processing → outputs
- **API design**: endpoints, request/response format, filters
- **Error handling**: failure modes and user-facing messages (Portuguese)
- **Testing strategy**: integration tests (view→service→model), unit tests for complex logic only

### 5. Document the Design

Write the validated design to a prompt file:

```
prompts/<NN>-<topic>.md
```

Following the existing prompt format (see `prompts/00-prompt-standard.md` as reference).

### 6. Ready for Implementation?

Ask: "Ready to implement?" If yes, use `/new-feature` to execute.

---

## Key Principles

- **One question at a time** — don't overwhelm
- **Multiple-choice preferred** — easier to answer
- **YAGNI ruthlessly** — remove every feature that isn't needed right now
- **Always 2–3 approaches** — explore before settling
- **Incremental validation** — present in sections, validate each
- **Architecture gate before design** — a design that violates dependency direction or soft delete is not a design, it's technical debt
- **Research modern best practices** — before proposing any design, search for current patterns. Use Python 3.11+ idioms, current library versions, and modern Django/React patterns
- **No workarounds in design** — if a design requires a workaround to fit the architecture, the design is wrong. Redesign until it fits properly
- **Refactoring is part of the design** — if implementing the best-practice solution requires restructuring existing code, include that restructuring in the design plan. Never design around existing tech debt — design to eliminate it
