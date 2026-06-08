# Sessão 51 — Backend: correções de raiz (disponibilidade de apto, captura de dependentes, guard de locador)

> **Feature**: Fluxo "Novo inquilino + contrato" (web) — `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
> **Sessões da feature**: **51** → 52 → (53 ‖) → 54 → 55. Esta é a **primeira** (correções de raiz que destravam o endpoint transacional da S52 e a geração de PDF da S55). **Não** cria o endpoint de onboarding (S52), nem frontend (S53–55).
> **Branch sugerida**: `feat/tenant-lease-onboarding` (a partir de `master`).

Esta sessão corrige 3 gaps verificados (design §5: G1, G2, G3) na camada existente — beneficiam também os endpoints atuais (`LeaseViewSet`, geração de contrato), sem mudar comportamento de quem já funciona:

1. **G3** — `LeaseSerializer.validate()` passa a rejeitar apartamento já alugado com `ValidationError({"apartment": ...})` (hoje só a `UniqueConstraint` do banco protege → `IntegrityError` 500).
2. **G1/G4** — `TenantSerializer.create()` passa a **capturar** os `Dependent` criados (em `tenant._created_dependents`) e a **propagar** `created_by`/`updated_by` a eles (hoje ficam nulos). Isso torna o residente-novo (S52) resolúvel sem depender de ordem implícita.
3. **G2** — `ContractService.prepare_contract_context` passa a **falhar** (erro PT) quando não há locador ativo, em vez de renderizar contrato vazio; o action `generate_contract` retorna **400**.

---

## Contexto

Ler antes de codar:
- **Design doc** (ler §4.1, §4.2, §5 tabela G1/G2/G3/G4): `@docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (só leitura): `@prompts/SESSION_STATE.md`
- **Regras**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| `LeaseSerializer.validate()` (atual) | `core/serializers.py:402-448` | Aqui se **adiciona** o check de disponibilidade; já valida `number_of_tenants` e `resident_dependent`. NÃO remover o que existe. |
| `LeaseSerializer.create()` + derivação de rental_value | `core/serializers.py:450-479` (deriva 458-464; `full_clean()`+`save()` 468-470) | Confirma que `full_clean()` roda no save; **não** valida disponibilidade hoje. |
| `Lease.UniqueConstraint` (apto ativo) | `core/models.py:733-736` (`unique_active_lease_per_apartment`, `condition=Q(is_deleted=False)`) | A regra de banco que vira `IntegrityError`; o check do serializer deve espelhar a MESMA condição (`is_deleted=False`). |
| `Lease.clean()` | `core/models.py:753` | Valida datas/contagem; **não** mexer aqui (disponibilidade é regra de serializer, não de `clean()` de model — `.claude/rules/architecture.md`). |
| Verificação de apto ocupado (precedente) | `core/services/lease_service.py` (`transfer_lease` checa `Lease.objects.filter(apartment_id=...).exists()`) | Padrão existente de "apto já tem contrato" — espelhar a query no serializer (excluindo o próprio na edição). |
| `TenantSerializer.create()` (dependents loop) | `core/serializers.py:298-308` | Onde capturar os `Dependent` criados + passar `created_by`/`updated_by`. |
| `TenantSerializer.Meta.fields` / `update()` | `core/serializers.py:252-268` / `~313-316` | Confirmar que `created_by`/`updated_by` NÃO estão em `fields` (vêm via `save(**kwargs)`). |
| Auditoria via `serializer.save(created_by=user)` | `core/viewsets/rule_views.py:72` | Precedente do projeto: kwargs do `save()` chegam ao `create()` via `validated_data`. |
| `ContractService.prepare_contract_context` (landlord) | `core/services/contract_service.py:191` (`landlord = Landlord.get_active()`) | Onde adicionar o guard de `None`. |
| `Landlord.get_active()` | `core/models.py:916-918` (`filter(is_active=True).first()` → pode ser `None`) | A fonte do `None`. |
| `generate_contract` action | `core/views.py:376-393` (eager → `{pdf_path}` 200; async → `{task_id}` 202) | Garantir que o erro de "sem locador" vire **400** (não 500) no caminho eager. |
| Testes de contrato (com fixture landlord) | `tests/unit/test_contract_service.py:150-192` | Adicionar caso **sem** locador. |

---

## Escopo

### Arquivos a modificar
- `core/serializers.py` — (a) `LeaseSerializer.validate()`: check de disponibilidade do apto; (b) `TenantSerializer.create()`: capturar `tenant._created_dependents` + propagar `created_by`/`updated_by` aos `Dependent`.
- `core/services/contract_service.py` — guard de locador ativo em `prepare_contract_context` (levanta `ValidationError` PT).
- `core/views.py` — `generate_contract` captura o erro de configuração e responde **400** (PT) no caminho eager.

### Arquivos a criar (testes)
- `tests/unit/test_lease_serializer_availability.py`
- `tests/unit/test_tenant_serializer_dependent_capture.py`
- (adicionar casos em) `tests/unit/test_contract_service.py` — sem locador → erro/400.

### NÃO fazer (outras sessões / fora de escopo)
- **NÃO** criar `TenantOnboardingService`, `TenantLeaseOnboardingSerializer`, view ou rota de onboarding — é a **S52**.
- **NÃO** tocar `Lease.clean()` / `core/models.py` (disponibilidade é regra de serializer; constraint do banco permanece).
- **NÃO** mexer em frontend.
- **NÃO** adicionar `# noqa`/`# type: ignore`; sem `from __future__`/`TYPE_CHECKING`; sem re-export.

---

## Especificação

### 1. Disponibilidade do apartamento (`LeaseSerializer.validate`) — G3
Dentro de `validate(self, attrs)` (após as validações atuais), com `apartment = attrs.get("apartment")` (resolvido via `source` do `apartment_id`):
- Montar `qs = Lease.objects.filter(apartment=apartment, is_deleted=False)` (mesma condição da `UniqueConstraint`, `core/models.py:733-736`).
- Em **edição** (`self.instance` setado), excluir o próprio: `qs = qs.exclude(pk=self.instance.pk)`.
- Se `apartment is not None and qs.exists()` → `raise serializers.ValidationError({"apartment": ["Este apartamento já possui um contrato ativo."]})` (mensagem PT).
- Em criação, `apartment` é obrigatório; se ausente, o erro de campo obrigatório já é levantado antes — **não** duplicar.

> Resultado: o endpoint atual e o de onboarding (S52) recebem **400 namespeado** em `apartment` em vez de `IntegrityError` 500. A S52 ainda adiciona `select_for_update` + `except IntegrityError` para a corrida; aqui é a validação determinística.

### 2. Captura de dependentes + auditoria (`TenantSerializer.create`) — G1/G4
No loop atual (`core/serializers.py:298-308`):
- Capturar cada `Dependent` criado numa lista local e, ao final, anexá-la à instância: `tenant._created_dependents = created` (lista na ORDEM do array de entrada).
- Ao criar cada dependente, **propagar auditoria**: `Dependent.objects.create(tenant=tenant, created_by=validated_data.get("created_by"), updated_by=validated_data.get("updated_by"), **dep_data)`.
  - `validated_data` contém `created_by`/`updated_by` quando o chamador usa `serializer.save(created_by=user, updated_by=user)` (precedente `rule_views.py:72`). Quando ausente (chamada sem auditoria), `.get()` retorna `None` (comportamento atual preservado).
- `tenant._created_dependents` é atributo de instância (não campo do model); usado pela **S52** para resolver `resident_dependent` novo pelo índice **sem** depender de ordering do model.

> **DRY/limpeza**: `update()` (`~313-316`) deve igualmente propagar `created_by`/`updated_by` aos dependentes recém-criados no smart-merge (mesma fonte). Não alterar a semântica de delete/update existente.

### 3. Guard de locador ativo (`ContractService.prepare_contract_context`) — G2
Em `prepare_contract_context` (`core/services/contract_service.py:191`), logo após `landlord = Landlord.get_active()`:
- Se `landlord is None` → `raise serializers.ValidationError("Nenhum locador ativo configurado. Cadastre o locador antes de gerar o contrato.")` (PT).
- Importar `from rest_framework import serializers` no topo (sem `try/except`).

E em `generate_contract` (`core/views.py:376-393`), no caminho **eager**, garantir que `serializers.ValidationError` vire **400** (o handler padrão do DRF já faz isso se a exceção propagar do action; se o action captura exceções da task, re-levantar `ValidationError` para o handler). Mensagem PT preservada no corpo (`{"detail": "..."}` ou `{"non_field_errors": [...]}`).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): banco real (`--reuse-db`); `transaction.atomic()` ao asserir `IntegrityError`; **nada** de mock interno. Geração de PDF: o teste do guard de locador deve cobrir **só** `prepare_contract_context` (não invocar Chrome/Playwright — testar a função que monta o contexto, fronteira de PDF fora).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_lease_serializer_availability.py`
- [ ] Criar lease para um apartamento; novo `LeaseSerializer(data=...)` para o **mesmo** apartamento → `is_valid()` False com erro em `apartment` (mensagem PT), **sem** `IntegrityError`.
- [ ] Apartamento **livre** → `is_valid()` True.
- [ ] **Edição** do próprio contrato (mesma apartment, `instance=lease`) → válido (não acusa a si mesmo).
- [ ] Apartamento cujo único contrato está **soft-deleted** → válido (a condição é `is_deleted=False`).

#### `tests/unit/test_tenant_serializer_dependent_capture.py`
- [ ] `TenantSerializer(data={...,"dependents":[d1,d2]}).save(created_by=user, updated_by=user)` → `tenant._created_dependents` tem 2 itens na ordem `[d1, d2]`, todos com `created_by==user` e `updated_by==user`.
- [ ] Sem dependentes → `tenant._created_dependents == []`.
- [ ] `save()` **sem** `created_by` (compat) → dependentes criados com `created_by is None` (sem quebrar).

#### `tests/unit/test_contract_service.py` (adicionar)
- [ ] `prepare_contract_context(lease)` **com** locador ativo → contexto montado (caso atual segue verde).
- [ ] **Sem** locador ativo (deletar/não criar `Landlord`) → `prepare_contract_context` levanta `ValidationError` PT.

> Rodar (devem **falhar**):
> ```bash
> python -m pytest tests/unit/test_lease_serializer_availability.py tests/unit/test_tenant_serializer_dependent_capture.py tests/unit/test_contract_service.py -q
> ```

### 2. GREEN — implementar conforme a Especificação (1, 2, 3).

### 3. REFACTOR — DRY
- Mensagem PT do apto ocupado como constante nomeada se reaproveitada (S52 pode reusar via import).
- Propagação de auditoria a dependentes via um único helper interno se `create()` e `update()` repetirem a expressão.

### 4. VERIFY — gate (escopo desta sessão; rodar só nos arquivos tocados — memória `feedback_testing_scope`)
```bash
python -m pytest tests/unit/test_lease_serializer_availability.py tests/unit/test_tenant_serializer_dependent_capture.py tests/unit/test_contract_service.py -q
# regressão dirigida (serializers/contrato existentes):
python -m pytest tests/unit/test_serializers.py tests/integration/test_leases_api.py -q   # ajustar nomes reais se diferirem
ruff check core/serializers.py core/services/contract_service.py core/views.py tests/unit/
ruff format --check core/serializers.py core/services/contract_service.py core/views.py tests/unit/
mypy core/
pyright core/serializers.py core/services/contract_service.py core/views.py
```

---

## Constraints
- **Disponibilidade = regra de serializer**, não de `Lease.clean()` (não tocar `core/models.py`). Espelhar `condition=Q(is_deleted=False)` da `UniqueConstraint`.
- **Auditoria via `save(**kwargs)`**: não adicionar `created_by`/`updated_by` a `Meta.fields`. Propagar aos dependentes com `validated_data.get(...)` (compat com chamadas sem auditoria).
- **Guard de locador**: `ValidationError` PT; `generate_contract` → 400 (não 500). Não mockar Chrome/Playwright nos testes (testar só `prepare_contract_context`).
- Sem `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export. Zero erros e zero warnings (ruff/mypy/pyright/pytest).
- Mensagens ao usuário em **Português**; logs/identificadores em **Inglês**.

## Critérios de Aceite (binários)
- [ ] `LeaseSerializer.validate` rejeita apto com contrato ativo (`{"apartment": [...]}` PT), permite apto livre, ignora o próprio na edição e ignora contratos soft-deleted.
- [ ] `TenantSerializer.create` expõe `tenant._created_dependents` (ordem do input) e propaga `created_by`/`updated_by` aos `Dependent`; `update` idem para novos.
- [ ] `prepare_contract_context` levanta `ValidationError` PT sem locador ativo; `generate_contract` responde **400** nesse caso (eager).
- [ ] Todos os testes novos/adicionados passam; regressão dirigida verde.
- [ ] `ruff`/`ruff format`/`mypy core/`/`pyright` limpos — zero erros/warnings; sem suppressions.
- [ ] `core/models.py` **não** alterado; nenhum artefato de onboarding criado.

## Handoff
1. Rodar o gate acima (verde).
2. Atualizar `prompts/SESSION_STATE.md` (seção da feature — criar se não existir): linha da S51 **concluída**, arquivos criados/modificados, e os **contratos cross-session** abaixo (verbatim para a S52).
3. Rodar `/audit` contra estes Critérios de Aceite.
4. Commit (criar branch `feat/tenant-lease-onboarding` a partir de `master` se necessário):
   ```
   feat(core): lease apartment-availability validation + tenant dependent capture/audit + landlord guard (onboarding root fixes)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima: **S52 — endpoint transacional de onboarding** (consome estas correções).

---

### Contratos cross-session definidos por esta sessão (consumir verbatim na S52)
- `LeaseSerializer.validate` rejeita apto ocupado → `ValidationError({"apartment": ["Este apartamento já possui um contrato ativo."]})`. A S52 ainda envolve a criação em `select_for_update` + `except IntegrityError` (corrida).
- `TenantSerializer.create`/`update` setam `tenant._created_dependents` (lista de `Dependent` na ordem do array enviado) e propagam `created_by`/`updated_by`. A S52 usa `tenant._created_dependents[index]` para resolver `resident_dependent` **novo** sem depender de `Meta.ordering`.
- `ContractService.prepare_contract_context` levanta `serializers.ValidationError` PT sem locador ativo; `generate_contract` → 400. A S55 (passo de PDF) trata esse 400.
