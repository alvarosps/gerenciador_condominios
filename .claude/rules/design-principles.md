# Design Principles — MANDATORY

These principles are non-negotiable. Every line of code, every refactoring, every feature must follow them. No exceptions, no shortcuts, no laziness.

## Core Principles

- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion — apply to classes, modules, services, and components
- **DRY**: Extract shared logic immediately when duplication is detected — never copy-paste
- **KISS**: Prefer the simplest correct solution — complexity must be justified
- **YAGNI**: Build only what is needed now — no speculative features, no "just in case" code
- **Clean Code**: Meaningful names, small focused functions, clear intent, no dead code

## Strict Rules

- CRITICAL: **No workarounds** — if something is broken or wrong, fix it properly at the root cause
- CRITICAL: **No quick wins** — every change must be done correctly, even if it takes longer
- CRITICAL: **No laziness** — if a refactoring is needed, do it fully, including all side effects
- CRITICAL: **No backwards compatibility** — legacy code is not maintained; when refactoring, update ALL callers, consumers, and side effects to match the new code
- CRITICAL: **No re-exports** — every module exports only what it defines; consumers import from the source
- CRITICAL: **No TODO/FIXME/HACK comments** — fix the issue now or don't touch it
- CRITICAL: **No partial refactoring** — when changing an interface, signature, or pattern, update every single usage across the entire codebase

## Refactoring Rules

When refactoring:
1. Change the source (function, class, module, interface)
2. Find ALL usages across the entire codebase (grep, IDE search)
3. Update every single usage — no exceptions
4. Remove old code completely — no deprecated wrappers, no shims, no aliases
5. Run linting, type checking, and tests to verify nothing is broken
6. If tests break, fix the tests to match the new correct behavior — don't revert the refactoring

## Architecture Quality

- Every class/module has a single, clear responsibility
- Dependencies flow in one direction — never circular
- Business logic lives in services, never in views/controllers or serializers
- Shared logic is extracted into well-named utilities or base classes
- Configuration and magic numbers are named constants
- Functions do one thing and do it well — if a function needs a comment explaining what a section does, that section should be its own function
