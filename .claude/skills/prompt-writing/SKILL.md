---
name: prompt-writing
description: Use when writing new implementation plans/prompts for features. Creates TDD-driven, multi-session prompt files following context engineering best practices. Always use /brainstorming first to define what to build, then this skill to write the execution plan.
argument-hint: "[feature-description]"
---

# Prompt Writing — Implementation Plans

Design doc: !`ls docs/plans/*.md | tail -3`
Existing prompts: !`ls prompts/*.md | grep -v SESSION | grep -v ROADMAP`
Session state: !`head -30 prompts/SESSION_STATE.md`

## When to Use

After `/brainstorming` has produced an approved design, use this skill to turn it into executable prompt files that Claude can follow session by session.

---

## Context Engineering Principles

### 1. Minimal Relevant Context (150-300 words per section)

Each prompt loads ONLY what's needed for its session:
- Reference files with `@path/to/file` — never paste content
- Point to specific line ranges for exemplars: `core/serializers.py:8-11`
- Keep the prompt under 400 lines — if longer, split into more sessions

### 2. Exemplar > Description

Instead of describing conventions, point to a concrete exemplar:
```
✗ "Create a serializer with nested read and ID write fields"
✓ "Follow the pattern of ApartmentSerializer in core/serializers.py:20-89"
```

### 3. Lost-in-the-Middle Prevention

Place the most critical information at the TOP and BOTTOM of each prompt:
- **Top**: Context loading (what to read), scope (files to create/modify)
- **Middle**: Specification details (can be longer)
- **Bottom**: Constraints, acceptance criteria, handoff instructions

### 4. TDD-First Structure

Every prompt follows Red → Green → Refactor → Verify:
1. **Write tests first** — with specific scenarios from the spec
2. **Run tests** — they must fail (proves tests are real)
3. **Implement** — minimum to pass tests
4. **Verify** — full suite passes

### 5. Closed Scope — No Ambiguity

Each prompt has:
- **Explicit file list** — what to create, what to modify
- **Explicit exclusion list** — what NOT to do
- **Binary acceptance criteria** — pass/fail, no "partially done"

---

## Prompt File Structure

```markdown
# Sessão NN — [Título Descritivo]

## Contexto
- Ler design doc: @docs/plans/YYYY-MM-DD-<topic>-design.md (seções X, Y)
- Ler estado: @prompts/SESSION_STATE.md
- Ler exemplares:
  - `core/serializers.py:20-89` — padrão nested read + ID write
  - `core/views.py:65-127` — padrão ViewSet com filtros

## Escopo

### Arquivos a criar
- `path/to/new_file.py`
- `tests/unit/test_new_file.py`

### Arquivos a modificar
- `core/urls.py` — registrar novas rotas
- `core/signals.py` — adicionar invalidação de cache

## Especificação

### [Feature 1]
[Interface/assinatura com tipos]
[Comportamento esperado]
[Edge cases]

### [Feature 2]
...

## TDD

### Testes a escrever (`tests/unit/test_<module>.py`)

```python
class TestFeature1:
    def test_scenario_a(self):
        """Descrição do cenário"""
    def test_scenario_b(self):
        """Descrição do edge case"""
    # ... todos os cenários
```

### Ciclo
1. Criar arquivo de teste com todos os cenários acima
2. `python -m pytest tests/unit/test_<module>.py -v` → devem FALHAR
3. Implementar código em `path/to/new_file.py`
4. `python -m pytest tests/unit/test_<module>.py -v` → devem PASSAR
5. `python -m pytest` → suite completa sem regressão
6. `ruff check && ruff format --check` → zero erros

## Constraints
- NÃO implementar [X] — isso é escopo da sessão NN+1
- NÃO modificar [Y] — já está correto
- NÃO adicionar # noqa ou # type: ignore

## Critérios de Aceite
- [ ] [Critério 1 — binário]
- [ ] [Critério 2 — binário]
- [ ] Todos os testes passam (0 falhas)
- [ ] `ruff check` sem erros
- [ ] `ruff format --check` sem erros
- [ ] SESSION_STATE.md atualizado

## Handoff
1. Rodar `python -m pytest` (100% passando)
2. Rodar `ruff check && ruff format --check` (0 erros)
3. Atualizar `prompts/SESSION_STATE.md`
4. Commitar: `feat(scope): complete session NN — [description]`
```

---

## Session Splitting Strategy

### When to Split

Split into multiple sessions when:
- More than 5 files to create
- More than 3 features with independent logic
- Backend + frontend in the same scope (split by layer)
- Total implementation would exceed ~800 lines of new code

### How to Split

Group by **dependency order** — each session's output is the next session's input:

```
Session N:   Models + Migration + Model tests
Session N+1: Serializers + Serializer tests
Session N+2: ViewSets + API tests
Session N+3: Frontend schemas + hooks + hook tests
Session N+4: Frontend pages + component tests
```

### Sizing Guidelines

| Session size | Lines of new code | Files | Duration |
|-------------|-------------------|-------|----------|
| Small | ~200 | 2-3 | 1 prompt |
| Medium | ~400 | 4-6 | 1 prompt |
| Large | ~600 | 6-8 | 1 prompt (max) |
| Too large | 800+ | 8+ | SPLIT IT |

### Parallelization Opportunities

Mark in the ROADMAP which sessions can run in parallel:

```
Wave 1: Session 03 + 04 (both are backend ViewSets, different models)
Wave 2: Session 05 (depends on 03+04)
Wave 3: Session 09 + 10 (frontend schemas + navigation, independent)
```

---

## Exemplar Index Maintenance

When writing prompts, update the exemplar index in `00-prompt-standard.md` if you discover new good patterns in the codebase. The index maps:

```
| Pattern | File | Lines | Use |
|---------|------|-------|-----|
| New pattern | path/to/file.py | 10-30 | When to use |
```

This index is the "vocabulary" — prompts reference it instead of explaining conventions.

---

## Quality Checklist for Written Prompts

Before finalizing a prompt, verify:

- [ ] Context section references files, never pastes content
- [ ] Exemplars use specific line ranges, not just file names
- [ ] TDD section lists ALL test scenarios (not "add tests as needed")
- [ ] Constraints section explicitly says what NOT to do
- [ ] Acceptance criteria are binary (pass/fail)
- [ ] No session creates more than 8 files
- [ ] Frontend and backend are separate sessions (unless trivially small)
- [ ] Session ordering respects dependencies
- [ ] ROADMAP.md is updated with new sessions
- [ ] SESSION_STATE.md template row added for each new session
